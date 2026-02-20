# -*- coding: utf-8 -*-
"""
酒店搜索工具：基于 Aigohotel MCP 服务（通过 ModelScope）
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional, List

from langchain.tools import tool
from client.aigohotel_client import aigohotel_search_hotels


def _infer_place_type(place: str) -> str:
    """
    根据地点名称推断地点类型。
    
    Args:
        place: 地点名称
        
    Returns:
        地点类型：城市、机场、景点、火车站、地铁站、酒店、区/县
    """
    place_lower = place.lower()
    
    # 机场关键词
    if any(kw in place for kw in ["机场", "国际机场", "航空港"]):
        return "机场"
    
    # 火车站关键词
    if any(kw in place for kw in ["火车站", "高铁站", "动车站", "客运站"]):
        return "火车站"
    
    # 地铁站关键词
    if any(kw in place for kw in ["地铁站", "轻轨站", "轨道交通"]):
        return "地铁站"
    
    # 酒店关键词
    if any(kw in place for kw in ["酒店", "宾馆", "饭店", "旅馆", "民宿"]):
        return "酒店"
    
    # 景点关键词（常见景点名称）
    if any(kw in place for kw in ["公园", "博物馆", "纪念馆", "景区", "风景区", "乐园", "广场", "塔", "寺", "庙", "山", "湖", "海"]):
        return "景点"
    
    # 区/县关键词
    if any(kw in place for kw in ["区", "县", "市", "镇", "街道"]):
        return "区/县"
    
    # 默认为城市
    return "城市"


def _budget_to_star_ratings(budget_level: str) -> Optional[List[float]]:
    """
    根据预算水平推断酒店星级范围。
    
    Args:
        budget_level: 预算水平（经济、舒适、豪华）
        
    Returns:
        星级范围列表，如 [0.0, 2.0] 或 None（不限制）
    """
    if budget_level == "经济":
        return [0.0, 3.0]  # 经济型：0-3星
    elif budget_level == "舒适":
        return [3.0, 4.5]  # 舒适型：3-4.5星
    elif budget_level == "豪华":
        return [4.5, 5.0]  # 豪华型：4.5-5星
    else:
        return None  # 未设置或不限制


@tool
def search_hotels(
    place: str,
    place_type: Optional[str] = None,
    origin_query: Optional[str] = None,
    check_in: Optional[str] = None,
    stay_nights: Optional[int] = None,
    star_ratings: Optional[List[float]] = None,
    adult_count: Optional[int] = None,
    distance_in_meter: Optional[int] = None,
    size: Optional[int] = 10,
    with_hotel_amenities: bool = False,
    with_room_amenities: bool = False,
    budget_level: Optional[str] = None,
) -> str:
    """
    搜索酒店：根据地点、时间和偏好条件搜索酒店，返回符合条件的酒店列表。
    
    会根据用户偏好自动调整搜索参数（如预算对应的星级范围）。
    
    Args:
        place (str): 地点名称（支持城市，景点，酒店，交通枢纽，地标等），例如：北京、上海外滩、北京首都国际机场
        place_type (str, optional): 地点的类型（城市、机场、景点、火车站、地铁站、酒店、区/县）。如果不提供，会根据地点名称自动推断
        origin_query (str, optional): 用户的提问语句，用于个性化分析。如果不提供，会使用默认值
        check_in (str, optional): 入住日期，格式：yyyy-MM-dd，如 2025-10-01。未填写时默认日期为次日
        stay_nights (int, optional): 入住天数，未填写时默认 1 天
        star_ratings (List[float], optional): 酒店星级(0.0-5.0, 梯度为 0.5)，例如：[4.5, 5.0] 表示 4.5–5 星
        adult_count (int, optional): 每间房入住的成人数量，默认两人
        distance_in_meter (int, optional): 直线距离，单位（米），当地点是一个 POI 位置时生效，生效时默认设定值为 5000
        size (int, optional): 返回酒店结果数量，默认 10 个酒店，最大不超过 20 个
        with_hotel_amenities (bool, optional): 是否包含酒店设施
        with_room_amenities (bool, optional): 是否包含房间设施
        budget_level (str, optional): 预算水平（经济、舒适、豪华），用于自动设置星级范围
        
    Returns:
        格式化的酒店推荐文本（纯中文）
    """
    try:
        # 设置默认预算水平
        if not budget_level:
            budget_level = "未设置"
        
        # 如果没有指定 place_type，自动推断
        if not place_type:
            place_type = _infer_place_type(place)
        
        # 如果没有指定 origin_query，使用默认值
        if not origin_query:
            origin_query = f"在{place}附近搜索酒店"
        
        # 根据用户预算自动设置星级范围（如果用户没有明确指定）
        if not star_ratings and budget_level != "未设置":
            star_ratings = _budget_to_star_ratings(budget_level)
        
        # 如果没有指定入住日期，默认使用次日
        if not check_in:
            tomorrow = datetime.now() + timedelta(days=1)
            check_in = tomorrow.strftime("%Y-%m-%d")
        
        # 如果没有指定入住天数，默认 1 天
        if stay_nights is None:
            stay_nights = 1
        
        # 调用 MCP 服务
        result_json = aigohotel_search_hotels(
            place=place,
            place_type=place_type,
            origin_query=origin_query,
            check_in=check_in,
            stay_nights=stay_nights,
            star_ratings=star_ratings,
            adult_count=adult_count,
            distance_in_meter=distance_in_meter,
            size=size,
            with_hotel_amenities=with_hotel_amenities,
            with_room_amenities=with_room_amenities,
        )
        
        # 解析结果
        try:
            data = json.loads(result_json)
            
            # 检查是否有错误
            if "error" in data:
                return f"酒店搜索失败：{data.get('error', '未知错误')}"
            
            # ModelScope 返回的格式：{"message": "...", "hotelInformationList": [...]}
            hotels = []
            if "hotelInformationList" in data:
                hotels = data["hotelInformationList"]
            elif isinstance(data, list):
                hotels = data
            elif isinstance(data, dict):
                # 尝试其他可能的字段名
                if "hotels" in data:
                    hotels = data["hotels"]
                elif "data" in data:
                    hotels = data["data"]
                elif "result" in data:
                    result = data["result"]
                    if isinstance(result, list):
                        hotels = result
                    elif isinstance(result, dict) and "hotels" in result:
                        hotels = result["hotels"]
            
            if not hotels:
                return f"在{place}附近未找到符合条件的酒店。"
            
            # 格式化输出
            output = f"## 🏨 为您推荐以下酒店（共 {len(hotels)} 家）\n\n"
            output += f"📍 搜索地点：{place}（{place_type}）\n"
            output += f"📅 入住日期：{check_in}，入住 {stay_nights} 晚\n"
            if star_ratings:
                output += f"⭐ 星级范围：{star_ratings[0]}-{star_ratings[1]} 星\n"
            output += "\n"
            
            for idx, hotel in enumerate(hotels, 1):
                name = hotel.get("name", "未知酒店")
                address = hotel.get("address", "地址未知")
                star_rating = hotel.get("starRating", 0)
                
                # 价格信息可能在 price 对象中
                price_info = hotel.get("price", {})
                price = 0
                currency = "CNY"
                if isinstance(price_info, dict):
                    price = price_info.get("lowestPrice", 0)
                    currency = price_info.get("currency", "CNY")
                else:
                    price = hotel.get("price", 0)
                    currency = hotel.get("currency", "CNY")
                
                description = hotel.get("description", "")
                booking_url = hotel.get("bookingUrl", "")
                image_url = hotel.get("imageUrl", "")
                score = hotel.get("score", "")
                
                output += f"### {idx}. {name}\n"
                
                if star_rating > 0:
                    output += f"⭐ 星级：{star_rating} 星\n"
                
                if price > 0:
                    output += f"💰 价格：{currency} {price:.2f}/晚\n"
                
                output += f"📍 地址：{address}\n"
                
                if description:
                    # 移除 HTML 标签并截断过长的描述
                    import re
                    desc_clean = re.sub(r'<[^>]+>', '', description)
                    desc_short = desc_clean[:100] + "..." if len(desc_clean) > 100 else desc_clean
                    output += f"📝 简介：{desc_short}\n"
                
                if score:
                    output += f"🎯 个性化评分：{score}\n"
                
                # 酒店设施
                hotel_amenities = hotel.get("hotelAmenities", [])
                if hotel_amenities:
                    amenities_str = "、".join(hotel_amenities[:5])  # 最多显示5个
                    if len(hotel_amenities) > 5:
                        amenities_str += f"等（共{len(hotel_amenities)}项）"
                    output += f"🏢 酒店设施：{amenities_str}\n"
                
                # 房间设施
                room_amenities = hotel.get("hotelRoomAmenities", [])
                if room_amenities:
                    room_amenities_str = "、".join(room_amenities[:5])  # 最多显示5个
                    if len(room_amenities) > 5:
                        room_amenities_str += f"等（共{len(room_amenities)}项）"
                    output += f"🛏️ 房间设施：{room_amenities_str}\n"
                
                if booking_url:
                    output += f"🔗 预订链接：{booking_url}\n"
                
                output += "\n"
            
            # 添加偏好提示
            if budget_level != "未设置":
                output += f"\n💡 已根据您的预算偏好（{budget_level}）为您筛选酒店\n"
            
            return output
            
        except json.JSONDecodeError:
            # 如果无法解析为JSON，直接返回原始结果
            return result_json
        except Exception as e:
            return f"解析酒店搜索结果时出错：{str(e)}\n原始结果：{result_json[:500]}"
            
    except Exception as e:
        return f"酒店搜索失败：{str(e)}"

