# -*- coding: utf-8 -*-
"""
路线规划客户端
专门为工作流提供路线规划功能，不依赖 ToolRuntime
"""

from __future__ import annotations

import json
from client.gaode_client import gaode_get_json_str


def plan_walking_route(origin: str, destination: str, origin_name: str = "起点", dest_name: str = "终点") -> dict:
    """
    规划步行路线
    
    Args:
        origin: 起点经纬度 "lng,lat"
        destination: 终点经纬度 "lng,lat"
        origin_name: 起点名称
        dest_name: 终点名称
    
    Returns:
        包含路线信息的字典
    """
    try:
        result = gaode_get_json_str(
            "/v3/direction/walking",
            {"origin": origin, "destination": destination},
            timeout=10
        )
        
        data = json.loads(result)
        
        # 检查错误
        if "error" in data:
            return {
                "success": False,
                "error": data.get("error", "未知错误"),
                "origin_name": origin_name,
                "dest_name": dest_name
            }
        
        # 检查状态
        if data.get("status") != "1":
            return {
                "success": False,
                "error": data.get("info", "API返回状态异常"),
                "origin_name": origin_name,
                "dest_name": dest_name
            }
        
        # 解析路线数据
        if data.get("route"):
            route = data["route"]
            paths = route.get("paths", [])
            
            if paths:
                path = paths[0]
                return {
                    "success": True,
                    "origin_name": origin_name,
                    "dest_name": dest_name,
                    "distance": int(float(path.get("distance", 0))),
                    "duration": int(float(path.get("duration", 0))),
                    "steps": path.get("steps", [])
                }
        
        return {
            "success": False,
            "error": "无路线数据",
            "origin_name": origin_name,
            "dest_name": dest_name
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "origin_name": origin_name,
            "dest_name": dest_name
        }


def plan_transit_route(origin: str, destination: str, city: str, origin_name: str = "起点", dest_name: str = "终点") -> dict:
    """
    规划公交/地铁路线
    
    Args:
        origin: 起点经纬度 "lng,lat"
        destination: 终点经纬度 "lng,lat"
        city: 城市名称
        origin_name: 起点名称
        dest_name: 终点名称
    
    Returns:
        包含路线信息的字典
    """
    try:
        result = gaode_get_json_str(
            "/v3/direction/transit/integrated",
            {
                "origin": origin,
                "destination": destination,
                "city": city,
                "cityd": city
            },
            timeout=15
        )
        
        data = json.loads(result)
        
        # 检查错误
        if "error" in data:
            return {
                "success": False,
                "error": data.get("error", "未知错误"),
                "origin_name": origin_name,
                "dest_name": dest_name
            }
        
        # 检查状态
        if data.get("status") != "1":
            return {
                "success": False,
                "error": data.get("info", "API返回状态异常"),
                "origin_name": origin_name,
                "dest_name": dest_name
            }
        
        # 解析路线数据
        if data.get("route"):
            route = data["route"]
            transits = route.get("transits", [])
            
            if transits:
                return {
                    "success": True,
                    "origin_name": origin_name,
                    "dest_name": dest_name,
                    "transits": transits[:2]  # 返回前2个方案
                }
        
        return {
            "success": False,
            "error": "无公交路线",
            "origin_name": origin_name,
            "dest_name": dest_name
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "origin_name": origin_name,
            "dest_name": dest_name
        }


def plan_driving_route(origin: str, destination: str, origin_name: str = "起点", dest_name: str = "终点") -> dict:
    """
    规划驾车路线
    
    Args:
        origin: 起点经纬度 "lng,lat"
        destination: 终点经纬度 "lng,lat"
        origin_name: 起点名称
        dest_name: 终点名称
    
    Returns:
        包含路线信息的字典
    """
    try:
        result = gaode_get_json_str(
            "/v3/direction/driving",
            {"origin": origin, "destination": destination},
            timeout=10
        )
        
        data = json.loads(result)
        
        # 检查错误
        if "error" in data:
            return {
                "success": False,
                "error": data.get("error", "未知错误"),
                "origin_name": origin_name,
                "dest_name": dest_name
            }
        
        # 检查状态
        if data.get("status") != "1":
            return {
                "success": False,
                "error": data.get("info", "API返回状态异常"),
                "origin_name": origin_name,
                "dest_name": dest_name
            }
        
        # 解析路线数据
        if data.get("route"):
            route = data["route"]
            paths = route.get("paths", [])
            
            if paths:
                path = paths[0]
                return {
                    "success": True,
                    "origin_name": origin_name,
                    "dest_name": dest_name,
                    "distance": int(float(path.get("distance", 0))),
                    "duration": int(float(path.get("duration", 0))),
                    "tolls": int(float(path.get("tolls", 0))),
                    "traffic_lights": int(float(path.get("traffic_lights", 0))),
                    "steps": path.get("steps", [])
                }
        
        return {
            "success": False,
            "error": "无驾车路线",
            "origin_name": origin_name,
            "dest_name": dest_name
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "origin_name": origin_name,
            "dest_name": dest_name
        }

