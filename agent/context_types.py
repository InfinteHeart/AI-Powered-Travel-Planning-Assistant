# -*- coding: utf-8 -*-
"""
Agent 类型定义
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class TravelContext(TypedDict, total=False):
    """Agent 运行时上下文，用于 dynamic_prompt / 其他中间件读取。"""

    user_role: str
    travel_mode_hint: str  # "traffic" / "destination" / "general" 等
    # 本轮是否允许更新偏好（由 _should_update_preferences 基于用户输入判断）
    allow_pref_update: bool
    
    # 用户偏好状态（继承 UserPreferenceState 的所有字段）
    travel_interests: list[str]
    transport_preference: str
    travel_pace: str
    budget_level: str
    accommodation_preference: list[str]
    food_preference: list[str]
    special_needs: list[str]
    weather_sensitive: bool
    preferences_collected: bool
    interaction_count: int


@dataclass
class ResponseFormat:
    """统一响应格式（方便后续做 UI 展示/结构化处理）。"""

    answer: str

