# -*- coding: utf-8 -*-
"""
Aigohotel MCP 客户端（通过 ModelScope）
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional, List
import os
from dotenv import load_dotenv
import requests
load_dotenv()
AIGOHOTEL_MCP_URL = os.getenv("AIGOHOTEL_MCP_URL")
# 配置日志
logger = logging.getLogger(__name__)


def _json_dumps(obj: Any) -> str:
    """确保中文不转义，返回 JSON 字符串。"""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def aigohotel_search_hotels(
    place: str,
    place_type: str,
    origin_query: str,
    check_in: Optional[str] = None,
    stay_nights: Optional[int] = None,
    star_ratings: Optional[List[float]] = None,
    adult_count: Optional[int] = None,
    distance_in_meter: Optional[int] = None,
    size: Optional[int] = None,
    with_hotel_amenities: bool = False,
    with_room_amenities: bool = False,
    country_code: Optional[str] = None,
    language: str = "zh_CN",
    query_parsing: bool = True,
    *,
    timeout: int = 30,
    mcp_url: str = AIGOHOTEL_MCP_URL,
) -> str:
    """
    通过 ModelScope MCP 端点搜索酒店，返回 JSON 字符串（不转义中文）。

    Args:
        place: 地点名称（支持城市，景点，酒店，交通枢纽，地标等）
        place_type: 地点的类型（城市、机场、景点、火车站、地铁站、酒店、区/县）
        origin_query: 用户的提问语句
        check_in: 入住日期，格式：yyyy-MM-dd
        stay_nights: 入住天数
        star_ratings: 酒店星级列表，如 [3.0, 5.0]
        adult_count: 每间房入住的成人数量
        distance_in_meter: 直线距离（米）
        size: 返回酒店结果数量，默认 10 个，最大 20 个
        with_hotel_amenities: 是否包含酒店设施
        with_room_amenities: 是否包含房间设施
        country_code: 国家三字码（例如：CHN）
        language: 语言环境（如 zh_CN、en_US）
        query_parsing: 是否分析用户个性化需求
        timeout: 超时时间（秒）
        mcp_url: ModelScope MCP 端点 URL

    Returns:
        JSON 字符串，包含酒店列表
    """
    # 构建参数
    arguments = {
        "place": place,
        "placeType": place_type,
        "originQuery": origin_query,
    }

    # 添加可选参数
    if check_in:
        arguments["checkIn"] = check_in
    if stay_nights is not None:
        arguments["stayNights"] = stay_nights
    if star_ratings is not None:
        arguments["starRatings"] = star_ratings
    if adult_count is not None:
        arguments["adultCount"] = adult_count
    if distance_in_meter is not None:
        arguments["distanceInMeter"] = distance_in_meter
    if size is not None:
        arguments["size"] = size
    if with_hotel_amenities:
        arguments["withHotelAmenities"] = True
    if with_room_amenities:
        arguments["withRoomAmenities"] = True
    if country_code:
        arguments["countryCode"] = country_code
    if language:
        arguments["language"] = language
    if not query_parsing:
        arguments["queryParsing"] = False

    # 构建 MCP 请求
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "searchHotels",
            "arguments": arguments
        }
    }

    # 设置请求头（ModelScope 不需要认证）
    headers = {
        "Content-Type": "application/json"
    }

    logger.debug(f"调用 ModelScope MCP: {mcp_url}")
    logger.debug(f"请求参数: {_json_dumps(arguments)}")

    try:
        # 发送请求
        resp = requests.post(
            mcp_url,
            json=mcp_request,
            headers=headers,
            timeout=timeout
        )

        # 检查 HTTP 状态码
        if resp.status_code != 200:
            error_msg = f"HTTP 错误 {resp.status_code}"
            logger.error(f"{error_msg}: {resp.text}")
            return _json_dumps({
                "error": error_msg,
                "status_code": resp.status_code,
                "response": resp.text[:500]
            })

        # 解析响应
        try:
            data = resp.json()
        except Exception as e:
            error_msg = f"响应不是有效的 JSON: {str(e)}"
            logger.error(f"{error_msg}, 响应: {resp.text[:500]}")
            return _json_dumps({
                "error": error_msg,
                "response": resp.text[:500]
            })

        # 检查 MCP 错误
        if "error" in data:
            err = data["error"]
            error_msg = f"MCP 错误 {err.get('code', 'unknown')}: {err.get('message', 'unknown')}"
            logger.error(error_msg)
            return _json_dumps({
                "error": error_msg,
                "mcp_error": err
            })

        # 提取结果
        result = data.get("result")
        if not result or "content" not in result:
            error_msg = "MCP 响应格式异常：缺少 result.content"
            logger.error(f"{error_msg}, 响应: {_json_dumps(data)}")
            return _json_dumps({
                "error": error_msg,
                "response": data
            })

        # 提取 text 内容
        content = result["content"]
        if not isinstance(content, list):
            error_msg = "MCP 响应格式异常：content 不是数组"
            logger.error(error_msg)
            return _json_dumps({
                "error": error_msg,
                "content": content
            })

        # 查找 text 类型的内容
        text_content = None
        for item in content:
            if item.get("type") == "text":
                text_content = item.get("text")
                break

        if text_content is None:
            error_msg = "MCP 响应中没有 text 类型的内容"
            logger.error(error_msg)
            return _json_dumps({
                "error": error_msg,
                "content": content
            })

        # 解析酒店数据
        try:
            hotels = json.loads(text_content)
            logger.info(f"成功获取 {len(hotels) if isinstance(hotels, list) else 1} 家酒店")
            return _json_dumps(hotels)
        except json.JSONDecodeError as e:
            error_msg = f"解析酒店数据失败: {str(e)}"
            logger.error(f"{error_msg}, 数据: {text_content[:500]}")
            return _json_dumps({
                "error": error_msg,
                "text": text_content[:500]
            })

    except requests.exceptions.Timeout:
        error_msg = f"请求超时（{timeout}秒）"
        logger.error(error_msg)
        return _json_dumps({
            "error": error_msg,
            "place": place
        })
    except requests.exceptions.ConnectionError as e:
        error_msg = f"连接失败: {str(e)}"
        logger.error(error_msg)
        return _json_dumps({
            "error": error_msg,
            "mcp_url": mcp_url
        })
    except Exception as e:
        error_msg = f"请求异常: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return _json_dumps({
            "error": error_msg,
            "place": place
        })
