# -*- coding: utf-8 -*-
"""
把 12306-mcp（CLI-stdio）封装成可复用的 Python Tool。

特点：
- 首次调用时自动启动 `npx -y 12306-mcp` 子进程
- 通过 MCP(JSON-RPC) 发送 `initialize` / `tools/call`
- 默认返回 text 格式，适合直接给大模型阅读

注意：
- 该实现面向“本机可运行 npx”的场景（Windows/Linux/macOS 均可）
- Windows 下会使用 `cmd /c npx ...`

你在工程里应统一这样导入本模块：

    from mcp_12306_stdio_tool import (
        get_station_code_of_citys,
        get_tickets_text,
        query_city_to_city_tickets_text,
        get_train_route_stations_text,
    )
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


def _json_dumps(obj: Any) -> str:
    """内部 JSON 序列化，统一使用 utf-8 且不转义中文。"""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


class _MCPStdioClient:
    """一个极简的 MCP stdio 客户端（只实现本项目需要的能力）。"""

    def __init__(self, npx_args: Optional[list[str]] = None) -> None:
        # 线程锁，保证同一时间只有一个请求在与子进程交互
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._rpc_id = 0
        self._npx_args = npx_args or ["-y", "12306-mcp"]

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def _ensure_proc(self) -> subprocess.Popen:
        """确保 MCP 子进程已启动。"""
        if self._proc and self._proc.poll() is None:
            return self._proc

        npx_path = shutil.which("npx") or shutil.which("npx.cmd") or shutil.which("npx.exe")
        if not npx_path:
            raise RuntimeError("未找到 npx。请先安装 Node.js，并确保 npx 在 PATH 中。")

        if os.name == "nt":
            cmd = ["cmd", "/c", npx_path] + self._npx_args
        else:
            cmd = [npx_path] + self._npx_args

        # 说明：
        # - MCP stdio 常见实现是“一行一个 JSON”，这里按 readline() 读取
        # - Windows 下部分环境会出现编码不一致导致中文变成 �（replacement char）
        #   因此这里用 bytes 模式读取，再做“utf-8 优先、失败回退 gbk/cp936”的解码。
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            cwd=os.getcwd(),
        )

        # 等待一点点日志输出，避免极端情况下 initialize 太快导致输出交错
        time.sleep(0.1)
        self._initialize()
        return self._proc

    @staticmethod
    def _decode_line(raw: bytes) -> str:
        """优先按 utf-8 解码，失败则回退 gbk(cp936)。"""
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("gbk", errors="replace")

    def _read_json_line(self, proc: subprocess.Popen) -> Dict[str, Any]:
        raw = proc.stdout.readline()  # type: ignore[union-attr]
        if not raw:
            err = ""
            try:
                raw_err = (proc.stderr.read() or b"")  # type: ignore[union-attr]
                err = self._decode_line(raw_err)
            except Exception:
                pass
            raise RuntimeError(f"未读到 MCP 响应，子进程可能已退出。stderr:\n{err}")
        line = self._decode_line(raw).strip()
        return json.loads(line)

    def _rpc_call(self, method: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        proc = self._ensure_proc()
        rid = self._next_id()
        req: Dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            req["params"] = params
        data = (_json_dumps(req) + "\n").encode("utf-8")
        proc.stdin.write(data)  # type: ignore[union-attr]
        proc.stdin.flush()  # type: ignore[union-attr]
        return self._read_json_line(proc)

    def _initialize(self) -> None:
        resp = self._rpc_call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "python-stdio-tool", "version": "0.0.1"},
            },
        )
        if "error" in resp:
            raise RuntimeError(f"initialize 失败：{resp['error']}")

    @staticmethod
    def _extract_text_content(resp: Dict[str, Any]) -> str:
        """从 MCP 响应中提取 text 内容，失败则返回 JSON 字符串。"""
        if "error" in resp:
            return f"RPC错误: {resp['error']}"
        result = resp.get("result")
        if not isinstance(result, dict):
            return _json_dumps(resp)
        content = result.get("content")
        if not isinstance(content, list) or not content:
            return _json_dumps(result)
        first = content[0]
        if isinstance(first, dict) and first.get("type") == "text":
            return str(first.get("text", ""))
        return _json_dumps(content)

    def call_tool_text(self, name: str, arguments: Dict[str, Any]) -> str:
        """调用 MCP 工具，并返回文本结果。"""
        resp = self._rpc_call("tools/call", {"name": name, "arguments": arguments})
        return self._extract_text_content(resp)

    def terminate(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass


_client_singleton = _MCPStdioClient()


def get_station_code_of_citys(citys: str) -> str:
    """
    获取城市 station_code（支持 | 分隔多个城市）。
    例：citys="北京|上海"
    """
    with _client_singleton._lock:
        return _client_singleton.call_tool_text("get-station-code-of-citys", {"citys": citys})


def get_tickets_text(
    date: str,
    from_station_code: str,
    to_station_code: str,
    train_filter_flags: str = "G",
    limited_num: int = 5,
) -> str:
    """查询余票（text 格式）。"""
    args: Dict[str, Any] = {
        "date": date,
        "fromStation": from_station_code,
        "toStation": to_station_code,
        "format": "text",
    }
    if train_filter_flags:
        args["trainFilterFlags"] = train_filter_flags
    if limited_num:
        args["limitedNum"] = limited_num

    with _client_singleton._lock:
        return _client_singleton.call_tool_text("get-tickets", args)


def query_city_to_city_tickets_text(
    from_city: str,
    to_city: str,
    date: Optional[str] = None,
    days_after_today: int = 1,
    train_filter_flags: str = "G",
    limited_num: int = 5,
) -> str:
    """
    给“城市->城市”的一键查询：自动取 station_code + 计算日期 + 查票。
    - date 为空时：用 MCP 的 get-current-date 作为基准 + days_after_today
    """
    with _client_singleton._lock:
        if not date:
            cur = _client_singleton.call_tool_text("get-current-date", {}).strip()
            try:
                base = datetime.strptime(cur, "%Y-%m-%d")
            except Exception:
                base = datetime.now()
            date = (base + timedelta(days=days_after_today)).strftime("%Y-%m-%d")

        station_text = _client_singleton.call_tool_text(
            "get-station-code-of-citys",
            {"citys": f"{from_city}|{to_city}"},
        )
        try:
            station_obj = json.loads(station_text)
            from_code = station_obj.get(from_city, {}).get("station_code") or "BJP"
            to_code = station_obj.get(to_city, {}).get("station_code") or "SHH"
        except Exception:
            # 解析失败就让用户显式提供 station_code，或用常见默认值继续
            from_code, to_code = "BJP", "SHH"

        tickets = _client_singleton.call_tool_text(
            "get-tickets",
            {
                "date": date,
                "fromStation": from_code,
                "toStation": to_code,
                "trainFilterFlags": train_filter_flags,
                "limitedNum": limited_num,
                "format": "text",
            },
        )
        return f"查询日期：{date}\n{from_city}({from_code}) -> {to_city}({to_code})\n\n{tickets}"


def get_train_route_stations_text(train_code: str, depart_date: str, format: str = "text") -> str:
    """
    查询指定车次在指定日期的经停站信息。

    Args:
        train_code (str): 车次，例如 "G1033"
        depart_date (str): 发车日期，格式 "yyyy-MM-dd"
        format (str): 返回格式，"text" 或 "json"
    """
    with _client_singleton._lock:
        return _client_singleton.call_tool_text(
            "get-train-route-stations",
            {"trainCode": train_code, "departDate": depart_date, "format": format},
        )



