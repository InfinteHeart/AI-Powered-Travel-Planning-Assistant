from __future__ import annotations

import json

from langchain.tools import tool, ToolRuntime
from client.gaode_client import gaode_get_json_str


@tool
def gaode_weather(city: str, adcode: str | None = None, extensions: str = "all") -> str:
    """调用高德天气 API，返回 JSON 字符串（不转义中文）。

    Args:
        city (str): 城市名称，例如：北京、上海（当 adcode 为空时使用该参数）
        adcode (str|None): 城市 adcode，例如：110000（北京），优先级高于 city
        extensions (str): base 或 all（all 为预报，base 为实况）
    """
    result = gaode_get_json_str(
        "/v3/weather/weatherInfo",
        {
            "city": adcode if adcode else city,
            "extensions": extensions,
        },
        timeout=10,
    )

    try:
        data = json.loads(result)
        if data.get("status") == "1":
            if extensions == "base":
                lives = data.get("lives", [])
                if lives:
                    weather_info = lives[0]
                    return f"""
{city}实时天气：
天气：{weather_info.get('weather', '未知')}
温度：{weather_info.get('temperature', '未知')}°C
湿度：{weather_info.get('humidity', '未知')}%
风向：{weather_info.get('winddirection', '未知')}风
风力：{weather_info.get('windpower', '未知')}级
更新时间：{weather_info.get('reporttime', '未知')}
"""
            else:
                forecasts = data.get("forecasts", [])
                if forecasts:
                    forecast = forecasts[0]
                    city_name = forecast.get("city", city)
                    casts = forecast.get("casts", [])

                    forecast_text = f"{city_name}天气预报：\n"
                    for cast in casts[:4]:
                        date_str = cast.get("date", "未知")
                        day_weather = cast.get("dayweather", "未知")
                        night_weather = cast.get("nightweather", "未知")
                        day_temp = cast.get("daytemp", "未知")
                        night_temp = cast.get("nighttemp", "未知")
                        forecast_text += (
                            f"{date_str}：白天{day_weather} {day_temp}°C，夜间{night_weather} {night_temp}°C\n"
                        )

                    return forecast_text
    except Exception:
        pass

    return result


@tool
def gaode_geocode(address: str, city: str | None = None) -> str:
    """地理编码：把"地址/POI名称"转换为经纬度，返回 JSON 字符串。

    Args:
        address (str): 结构化地址或 POI 名称，例如：上海虹桥站、外滩、迪士尼
        city (str|None): 可选，城市名用于缩小范围，例如：上海
    """
    params: dict[str, str] = {"address": address}
    if city:
        params["city"] = city
    return gaode_get_json_str("/v3/geocode/geo", params, timeout=10)


@tool
def gaode_around_search(runtime: ToolRuntime, city: str, keywords: str | None = None) -> str:
    """周边/兴趣点搜索（基于高德 place/text 接口），返回 JSON 字符串。
    
    会根据用户偏好自动调整搜索关键词和结果展示。

    Args:
        runtime (ToolRuntime): 运行时上下文，用于获取用户偏好
        city (str): 城市中文名、citycode 或 adcode，例如：北京 / 010 / 110000
        keywords (str|None): 关键词，例如：美食、咖啡、景点、博物馆；为空时建议在对话中提示用户补充
    """
    try:
        # 获取用户偏好
        state = runtime.state
        travel_interests = state.get("travel_interests", [])
        budget_level = state.get("budget_level", "未设置")
        
        # 如果没有提供关键词，根据用户兴趣偏好生成
        if not keywords and travel_interests:
            interest_keywords_map = {
                "历史文化": "博物馆,古迹,文化街区",
                "自然风光": "公园,风景区,山水",
                "美食体验": "美食,餐厅,小吃",
                "购物娱乐": "商场,购物中心,娱乐",
                "亲子游玩": "游乐园,动物园,儿童乐园",
                "艺术文艺": "美术馆,艺术馆,剧院",
            }
            # 使用第一个兴趣作为关键词
            for interest in travel_interests:
                if interest in interest_keywords_map:
                    keywords = interest_keywords_map[interest].split(",")[0]
                    break
        
        params: dict[str, str] = {"city": city}
        if keywords:
            params["keywords"] = keywords
        
        result = gaode_get_json_str("/v3/place/text", params, timeout=10)
        
        # 解析结果并根据用户偏好添加推荐说明
        try:
            data = json.loads(result)
            if data.get("status") == "1" and data.get("pois"):
                pois = data["pois"][:10]  # 限制返回数量
                
                # 构建个性化推荐文本
                recommendation = f"\n根据您的偏好为您推荐 {city} 的{keywords or '相关'}地点：\n\n"
                
                for idx, poi in enumerate(pois, 1):
                    name = poi.get("name", "未知")
                    address = poi.get("address", "未知")
                    poi_type = poi.get("type", "")
                    
                    recommendation += f"{idx}. {name}\n"
                    recommendation += f"   地址：{address}\n"
                    
                    # 根据预算水平添加提示
                    if budget_level == "经济" and "免费" in poi_type:
                        recommendation += "   💡 经济实惠推荐\n"
                    elif budget_level == "豪华" and any(k in poi_type for k in ["五星", "高档", "奢华"]):
                        recommendation += "   ⭐ 高品质推荐\n"
                    
                    recommendation += "\n"
                
                # 添加偏好相关的额外建议
                if travel_interests:
                    recommendation += f"\n💡 基于您对 {', '.join(travel_interests)} 的兴趣为您筛选\n"
                
                return recommendation
        except Exception:
            pass
        
        return result
    except Exception as e:
        return f"搜索失败：{e}"


@tool
def gaode_direction_transit(runtime: ToolRuntime, origin: str, destination: str, city: str, cityd: str) -> str:
    """公交路径规划：返回 JSON 字符串。
    
    会根据用户的出行偏好提供个性化建议。

    Args:
        runtime (ToolRuntime): 运行时上下文，用于获取用户偏好
        origin (str): 起点经纬度 "lng,lat"
        destination (str): 终点经纬度 "lng,lat"
        city (str): 起点城市名或 adcode
        cityd (str): 终点城市名或 adcode
    """
    result = gaode_get_json_str(
        "/v3/direction/transit/integrated",
        {"origin": origin, "destination": destination, "city": city, "cityd": cityd},
        timeout=15,
    )
    
    # 获取用户偏好
    state = runtime.state
    transport_preference = state.get("transport_preference", "未设置")
    travel_pace = state.get("travel_pace", "未设置")
    
    # 添加偏好提示
    preference_note = ""
    if transport_preference == "公交":
        preference_note = "\n💡 根据您的偏好，为您优先推荐公交路线"
    elif travel_pace == "悠闲":
        preference_note = "\n💡 建议选择换乘较少的路线，更加轻松"
    
    return result + preference_note


@tool
def gaode_direction_walking(runtime: ToolRuntime, origin: str, destination: str) -> str:
    """步行路径规划：返回 JSON 字符串。
    
    会根据用户的旅行节奏提供个性化建议。
    
    Args:
        runtime (ToolRuntime): 运行时上下文，用于获取用户偏好
        origin (str): 起点经纬度 "lng,lat"
        destination (str): 终点经纬度 "lng,lat"
    """
    result = gaode_get_json_str(
        "/v3/direction/walking",
        {"origin": origin, "destination": destination},
        timeout=15,
    )
    
    # 获取用户偏好
    state = runtime.state
    transport_preference = state.get("transport_preference", "未设置")
    travel_pace = state.get("travel_pace", "未设置")
    
    # 添加偏好提示
    preference_note = ""
    if transport_preference == "步行":
        preference_note = "\n💡 根据您的偏好，步行是很好的选择，可以深度体验当地"
    elif travel_pace == "紧凑":
        preference_note = "\n💡 如果时间紧张，建议考虑其他交通方式"
    
    return result + preference_note


@tool
def gaode_direction_driving(runtime: ToolRuntime, origin: str, destination: str) -> str:
    """驾车路径规划：返回 JSON 字符串。
    
    会根据用户的出行偏好提供个性化建议。
    
    Args:
        runtime (ToolRuntime): 运行时上下文，用于获取用户偏好
        origin (str): 起点经纬度 "lng,lat"
        destination (str): 终点经纬度 "lng,lat"
    """
    result = gaode_get_json_str(
        "/v3/direction/driving",
        {"origin": origin, "destination": destination},
        timeout=15,
    )
    
    # 获取用户偏好
    state = runtime.state
    transport_preference = state.get("transport_preference", "未设置")
    
    # 添加偏好提示
    preference_note = ""
    if transport_preference == "自驾":
        preference_note = "\n💡 根据您的偏好，自驾游可以更自由地安排行程"
    
    return result + preference_note


