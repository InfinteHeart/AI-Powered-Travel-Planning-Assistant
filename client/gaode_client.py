# -*- coding: utf-8 -*-
"""
高德地图 Web 服务 API 统一客户端封装。

设计目标：
- 统一处理：API Key、超时、请求参数、错误返回、JSON字符串输出
- 便于你后续快速新增“周边搜索/路径规划/地理编码”等 tool（只需改 endpoint 和 params）

注意：
- 本模块对外推荐只暴露 `gaode_get_json_str` 这一个函数（足够通用）
- tool 的返回建议是 JSON 字符串；Agent 最终回答必须是纯文本（在 prompt 里约束）
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
load_dotenv()
import requests


def _json_dumps(obj: Any) -> str:
    """确保中文不转义，返回 JSON 字符串。"""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def gaode_get_json_str(
    endpoint: str,
    params: Dict[str, Any],
    *,
    timeout: int = 10,
    api_key_env: str = "GAODE_API_KEY",
    base_url: str = "https://restapi.amap.com",
) -> str:
    """
    调用高德 Web 服务 API（GET），返回 JSON 字符串（不转义中文）。

    Args:
        endpoint: API 路径，如 "/v3/weather/weatherInfo"
        params: 请求参数（不包含 key 会自动补）
        timeout: 超时时间（秒）
        api_key_env: 环境变量名，默认 "GAODE_API_KEY"
        base_url: 高德 API 域名
    """
    key = os.getenv(api_key_env)
    if not key:
        return _json_dumps({"error": f"未找到环境变量 {api_key_env}，请先配置高德 API Key"})

    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")
    full_params = dict(params)
    full_params["key"] = key

    try:
        resp = requests.get(url, params=full_params, timeout=timeout)
        # 高德多数接口无论成功失败都返回 JSON；这里尽量解析
        try:
            data: Any = resp.json()
        except Exception:
            data = {"error": "响应不是JSON", "status_code": resp.status_code, "text": resp.text}

        # 把HTTP层错误也显式化，方便模型判断
        if resp.status_code != 200:
            return _json_dumps({"error": "HTTP请求失败", "status_code": resp.status_code, "data": data})

        return _json_dumps(data)
    except Exception as e:
        return _json_dumps({"error": "请求异常", "message": str(e), "endpoint": endpoint, "params": params})


