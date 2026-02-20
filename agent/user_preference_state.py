# -*- coding: utf-8 -*-
"""
用户偏好状态定义
用于存储和管理用户的旅行偏好，实现个性化推荐
"""

from __future__ import annotations

from typing import Literal, TypedDict


class UserPreferenceState(TypedDict, total=False):
    """
    用户旅行偏好状态
    
    包含用户的各种旅行偏好信息，用于生成个性化推荐
    """
    
    # 旅行兴趣偏好
    travel_interests: list[str]  # 例如：["历史文化", "自然风光", "美食体验", "购物娱乐", "亲子游玩"]
    
    # 出行方式偏好
    transport_preference: Literal["步行", "公交", "自驾", "混合", "未设置"]  # 在目的地的出行方式
    
    # 旅行节奏偏好
    travel_pace: Literal["悠闲", "适中", "紧凑", "未设置"]  # 行程安排的紧凑程度
    
    # 预算偏好
    budget_level: Literal["经济", "舒适", "豪华", "未设置"]  # 预算水平
    
    # 住宿偏好
    accommodation_preference: list[str]  # 例如：["靠近景区", "交通便利", "安静舒适", "性价比高"]
    
    # 餐饮偏好
    food_preference: list[str]  # 例如：["本地特色", "网红餐厅", "街边小吃", "高档餐厅"]
    
    # 特殊需求
    special_needs: list[str]  # 例如：["带小孩", "带老人", "无障碍设施", "宠物友好"]
    
    # 天气敏感度
    weather_sensitive: bool  # 是否对天气敏感（影响行程安排）
    
    # 是否偏好收集完成
    preferences_collected: bool  # 标记是否已经收集过偏好
    
    # 交互计数
    interaction_count: int  # 交互次数统计


def get_default_preferences() -> UserPreferenceState:
    """
    获取默认的用户偏好状态
    
    Returns:
        UserPreferenceState: 默认偏好状态
    """
    return {
        "travel_interests": [],
        "transport_preference": "未设置",
        "travel_pace": "未设置",
        "budget_level": "未设置",
        "accommodation_preference": [],
        "food_preference": [],
        "special_needs": [],
        "weather_sensitive": True,
        "preferences_collected": False,
        "interaction_count": 0,
    }


def format_preferences_summary(preferences: UserPreferenceState) -> str:
    """
    格式化用户偏好摘要，用于展示给用户确认
    
    Args:
        preferences: 用户偏好状态
        
    Returns:
        str: 格式化的偏好摘要
    """
    lines = ["您的旅行偏好："]
    
    if preferences.get("travel_interests"):
        lines.append(f"• 兴趣偏好：{', '.join(preferences['travel_interests'])}")
    
    if preferences.get("transport_preference") and preferences["transport_preference"] != "未设置":
        lines.append(f"• 出行方式：{preferences['transport_preference']}")
    
    if preferences.get("travel_pace") and preferences["travel_pace"] != "未设置":
        lines.append(f"• 旅行节奏：{preferences['travel_pace']}")
    
    if preferences.get("budget_level") and preferences["budget_level"] != "未设置":
        lines.append(f"• 预算水平：{preferences['budget_level']}")
    
    if preferences.get("accommodation_preference"):
        lines.append(f"• 住宿偏好：{', '.join(preferences['accommodation_preference'])}")
    
    if preferences.get("food_preference"):
        lines.append(f"• 餐饮偏好：{', '.join(preferences['food_preference'])}")
    
    if preferences.get("special_needs"):
        lines.append(f"• 特殊需求：{', '.join(preferences['special_needs'])}")
    
    if preferences.get("weather_sensitive"):
        lines.append("• 对天气敏感：是")
    
    return "\n".join(lines)


def get_preference_collection_prompt() -> str:
    """
    获取偏好收集提示语
    
    Returns:
        str: 偏好收集提示
    """
    return """为了给您提供更个性化的旅行推荐，我想了解一下您的旅行偏好：

1. 您对哪些方面比较感兴趣？（可多选）
   - 历史文化（古迹、博物馆、文化街区）
   - 自然风光（山水、公园、海滨）
   - 美食体验（特色餐厅、小吃街、网红店）
   - 购物娱乐（商场、夜市、娱乐场所）
   - 亲子游玩（游乐园、动物园、科技馆）
   - 艺术文艺（美术馆、剧院、文艺街区）

2. 在目的地您更喜欢哪种出行方式？
   - 步行（慢慢逛，深度体验）
   - 公交/地铁（经济实惠，体验当地生活）
   - 自驾（自由灵活，适合郊区景点）
   - 混合（根据具体情况选择）

3. 您喜欢什么样的旅行节奏？
   - 悠闲（每天2-3个景点，留足时间休息）
   - 适中（每天3-4个景点，张弛有度）
   - 紧凑（每天4-5个景点，充分利用时间）

4. 您的预算水平大概是？
   - 经济（注重性价比）
   - 舒适（品质与价格平衡）
   - 豪华（追求高品质体验）

5. 有什么特殊需求吗？（可选）
   - 带小孩、带老人、需要无障碍设施等

您可以直接告诉我，比如："我喜欢历史文化和美食，喜欢步行，节奏悠闲一点，预算舒适就好"
或者只回答部分问题也可以，我会根据您提供的信息来优化推荐！"""

