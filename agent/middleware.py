# -*- coding: utf-8 -*-
"""
Agent 中间件：动态系统提示词选择
"""

from __future__ import annotations

from typing import Dict, Any

from langchain.agents.middleware import dynamic_prompt, ModelRequest

from prompts import (
    BASE_TRAVEL_SYSTEM_PROMPT,
    TRAFFIC_SYSTEM_PROMPT,
    DESTINATION_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT,
)


@dynamic_prompt
def travel_system_prompt(request: ModelRequest) -> str:
    """
    动态系统提示词中间件：
    - 根据当前消息内容 + 上下文 TravelContext 中的 travel_mode_hint，
      在"三套旅游提示词"之间切换。
    """
    # 1) 从上下文中读取显式 hint（如果有的话）
    context: Dict[str, Any] = dict(getattr(request.runtime, "context", {}) or {})
    mode_hint: str = str(context.get("travel_mode_hint", "") or "").lower()

    if mode_hint == "traffic":
        return TRAFFIC_SYSTEM_PROMPT
    if mode_hint in ("destination", "dest", "poi"):
        return DESTINATION_SYSTEM_PROMPT
    if mode_hint == "review":
        return REVIEW_SYSTEM_PROMPT

    # 2) 没有显式 hint 时，根据最后一条用户消息做简单意图识别
    messages = request.messages or []
    last_text = ""
    if messages:
        last = messages[-1]
        if isinstance(last, dict):
            last_text = str(last.get("content", "") or "")
        else:
            # 兼容 BaseMessage 等类型
            last_text = str(getattr(last, "content", "") or "")

    text = last_text

    # 评价类关键词（优先级最高，因为评价查询需要网络搜索）
    review_keywords = [
        "怎么样", "好不好", "值得", "推荐", "评价", "口碑", "好吃", "好玩",
        "哪家好", "哪个好", "体验", "感觉", "味道", "服务", "环境",
    ]
    
    traffic_keywords = ["火车", "高铁", "动车", "车次", "余票", "经停", "12306", "列车"]
    dest_keywords = ["天气", "景点", "美食", "周边", "路线", "公交", "步行", "驾车", "地铁", "地理编码", "坐标"]

    # 优先判断是否是评价类查询
    if any(k in text for k in review_keywords):
        return REVIEW_SYSTEM_PROMPT
    if any(k in text for k in traffic_keywords):
        return TRAFFIC_SYSTEM_PROMPT
    if any(k in text for k in dest_keywords):
        return DESTINATION_SYSTEM_PROMPT

    # 默认使用基础旅行助手提示词
    return BASE_TRAVEL_SYSTEM_PROMPT

