# -*- coding: utf-8 -*-
"""
用户偏好管理：从文本提取偏好、判断是否需要更新偏好
"""

from __future__ import annotations

from agent.user_preference_state import UserPreferenceState


def should_update_preferences(user_input: str) -> bool:
    """
    粗略判断当前这一轮用户输入是否在「描述/修改旅行偏好」。
    只有在返回 True 时，才会接受本轮对偏好字段的更新。
    """
    text = user_input.strip()
    if not text:
        return False

    # 关键触发词：用户显式提到偏好、喜欢、预算、节奏等
    keywords = [
        "偏好",
        "喜好",
        "喜欢",
        "不喜欢",
        "合适的节奏",
        "节奏",
        "预算",
        "消费水平",
    ]

    # 具体偏好选项相关词
    option_words = [
        # 兴趣
        "历史文化",
        "自然风光",
        "美食体验",
        "购物娱乐",
        "亲子游玩",
        "艺术文艺",
        # 出行方式
        "步行",
        "公交",
        "地铁",
        "自驾",
        "混合",
        # 行程节奏
        "悠闲",
        "适中",
        "紧凑",
        # 预算
        "经济",
        "舒适",
        "豪华",
    ]

    # 只要命中任意关键词/选项词，就认为是在谈偏好
    if any(k in text for k in keywords):
        return True
    if any(w in text for w in option_words):
        return True

    return False


def update_preferences_from_text(
    user_input: str, preferences: UserPreferenceState
) -> None:
    """
    基于本轮用户输入的自然语言，粗略提取并更新旅行偏好字段。

    说明：
    - 只在 should_update_preferences 返回 True 时被调用
    - 采用关键词/选项词映射，不依赖模型/工具返回的 state，保证偏好可持久化
    """
    text = user_input.strip()
    if not text:
        return

    updated = False

    # 1）兴趣偏好：允许多选，采用"包含即加入"的方式
    interests_map = {
        "历史文化": "历史文化",
        "自然风光": "自然风光",
        "美食体验": "美食体验",
        "美食": "美食体验",
        "购物娱乐": "购物娱乐",
        "购物": "购物娱乐",
        "亲子游玩": "亲子游玩",
        "亲子": "亲子游玩",
        "艺术文艺": "艺术文艺",
        "文艺": "艺术文艺",
    }
    current_interests = set(preferences.get("travel_interests", []) or [])

    # 如果语句中包含"改成/改为"，视为覆盖兴趣偏好
    is_replace = ("改成" in text) or ("改为" in text)
    new_interests: set[str] = set()

    for kw, label in interests_map.items():
        if kw in text:
            new_interests.add(label)

    if new_interests:
        if is_replace:
            current_interests = new_interests
        else:
            current_interests.update(new_interests)

        preferences["travel_interests"] = list(current_interests)
        updated = True

    # 2）出行方式偏好（互斥）
    transport = preferences.get("transport_preference", "未设置") or "未设置"
    if "步行" in text:
        transport = "步行"
    elif ("公交" in text) or ("地铁" in text):
        transport = "公交"
    elif ("自驾" in text) or ("开车" in text) or ("驾车" in text):
        transport = "自驾"
    elif "混合" in text:
        transport = "混合"
    if transport != preferences.get("transport_preference", "未设置"):
        preferences["transport_preference"] = transport
        updated = True

    # 3）旅行节奏偏好（互斥）
    pace = preferences.get("travel_pace", "未设置") or "未设置"
    if "悠闲" in text:
        pace = "悠闲"
    elif "适中" in text:
        pace = "适中"
    elif "紧凑" in text:
        pace = "紧凑"
    if pace != preferences.get("travel_pace", "未设置"):
        preferences["travel_pace"] = pace
        updated = True

    # 4）预算水平（互斥）
    budget = preferences.get("budget_level", "未设置") or "未设置"
    if "经济" in text:
        budget = "经济"
    elif "舒适" in text:
        budget = "舒适"
    elif "豪华" in text:
        budget = "豪华"
    if budget != preferences.get("budget_level", "未设置"):
        preferences["budget_level"] = budget
        updated = True

    # 只要有任意一项被更新，就认为"已收集过偏好"
    if updated:
        preferences["preferences_collected"] = True

