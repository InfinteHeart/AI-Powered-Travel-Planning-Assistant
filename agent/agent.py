# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

# 确保可以从项目根目录导入 prompts / tools 包
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools import (
    query_train_tickets,
    get_train_route_stations,
    gaode_weather,
    gaode_geocode,
    gaode_around_search,
    gaode_direction_transit,
    gaode_direction_walking,
    gaode_direction_driving,
    get_personalized_recommendations,
    update_user_preferences,
    search_reviews,
    search_hotels,
)
from workflow import create_recommendation_workflow_tool
from agent.context_types import TravelContext, ResponseFormat
from agent.middleware import travel_system_prompt
from agent.session_manager import SessionManager
from agent.preference_manager import (
    should_update_preferences,
    update_preferences_from_text,
)
from agent.text_utils import (
    remove_duplicate_content,
    sanitize_preference_answer,
)
from agent.user_preference_state import UserPreferenceState

load_dotenv()


class TravelPlanningAgent:
    """旅行规划智能体：支持多轮对话、工具调用、动态系统提示词与摘要中间件。"""

    def __init__(self) -> None:
        """初始化底层模型、Agent 与中间件。"""
        self.model = init_chat_model(
            "deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0.1,
            max_tokens=1200,
        )

        # LangGraph 内存型 checkpoint，用于按 thread_id 维护会话状态
        self.checkpointer = InMemorySaver()

        # 摘要中间件：靠 LangChain 自带的 SummarizationMiddleware 管理长上下文
        self.summarization_middleware = SummarizationMiddleware(
            model=self.model,
            trigger=("tokens", 4000),
            keep=("messages", 20),
            summary_prompt=(
                "你是一个旅行规划助手，请用简洁的中文总结当前对话，"
                "保留关键信息（出发地、目的地、日期、车次/交通选择、天气、行程安排、用户偏好等），"
                "供后续多轮对话使用。"
            ),
        )

        # 会话管理器
        self.session_manager = SessionManager()

        # 创建统一 Agent，挂载：
        # - tools：12306 + 高德 + 个性化推荐 + 网络搜索 + 结构化推荐工作流
        # - middleware：SummarizationMiddleware + dynamic_prompt
        # 注意：需要先创建 agent 才能获取 runtime，所以分两步初始化
        self.agent = None
        self._init_agent()

    def _init_agent(self) -> None:
        """初始化 Agent（需要在 __init__ 之后调用，以便创建工作流工具）"""
        # 创建一个临时的 runtime 对象用于工作流工具
        # 注意：这里使用一个占位符，实际运行时会被替换
        class TempRuntime:
            def __init__(self):
                self.state = {}
        
        temp_runtime = TempRuntime()
        
        # 创建工作流工具
        structured_recommendation_tool = create_recommendation_workflow_tool(temp_runtime)
        
        self.agent = create_agent(
            model=self.model,
            tools=[
                # 交通（12306）
                query_train_tickets,
                get_train_route_stations,
                # 目的地信息（高德）
                gaode_weather,
                gaode_geocode,
                gaode_around_search,
                gaode_direction_transit,
                gaode_direction_walking,
                gaode_direction_driving,
                # 个性化推荐
                get_personalized_recommendations,
                update_user_preferences,
                # 网络搜索（评价搜索）
                search_reviews,
                # 🆕 酒店推荐
                search_hotels,
                # 🆕 结构化推荐工作流（包含完整的路线规划）
                structured_recommendation_tool,
            ],
            response_format=ToolStrategy(ResponseFormat),
            checkpointer=self.checkpointer,
            middleware=[self.summarization_middleware, travel_system_prompt],
            state_schema=TravelContext,
        )

    def create_new_session(self) -> str:
        """创建新的对话会话，并返回 session_id（即 thread_id）。"""
        return self.session_manager.create_new_session()

    def get_response(self, user_input: str, session_id: Optional[str] = None) -> str:
        """
        获取对用户输入的响应。

        - 使用 SummarizationMiddleware 自动管理长对话摘要；
        - 使用 dynamic_prompt(travel_system_prompt) 动态选择系统提示词；
        - 支持基于用户偏好的个性化推荐； 
        - 仍然通过 structured_response.answer 返回纯文本。
        """
        if session_id is None:
            session_id = self.create_new_session()
        
        # 确保会话存在
        self.session_manager.ensure_session_exists(session_id)

        config = {"configurable": {"thread_id": session_id}}

        try:
            messages: List[Dict[str, str]] = [{"role": "user", "content": user_input}]

            # 获取当前会话的用户偏好
            preferences = self.session_manager.get_session_preferences(session_id)
            
            # 增加交互计数
            preferences["interaction_count"] = preferences.get("interaction_count", 0) + 1

            # 是否可以基于本轮输入更新偏好
            allow_pref_update = should_update_preferences(user_input)

            # 如果本轮在明显描述偏好，则先基于用户输入更新一次会话偏好，确保本轮就能用上
            if allow_pref_update:
                update_preferences_from_text(user_input, preferences)
                # 更新会话管理器中的偏好
                self.session_manager.update_session_preferences(session_id, preferences)

            # 构建包含用户偏好的上下文（用于传给 Agent / tools）
            # 这一步是传给state，相当于初始化，而不是用来更新，真正的更新是调用了工具，如果没有这一步初始化，则工具无法更新state
            context: TravelContext = {
                "user_role": "user",
                # 本轮是否允许更新偏好（传递给工具使用，仅作参考）
                "allow_pref_update": allow_pref_update,
                # 传入用户偏好状态
                "travel_interests": preferences.get("travel_interests", []),
                "transport_preference": preferences.get("transport_preference", "未设置"),
                "travel_pace": preferences.get("travel_pace", "未设置"),
                "budget_level": preferences.get("budget_level", "未设置"),
                "accommodation_preference": preferences.get("accommodation_preference", []),
                "food_preference": preferences.get("food_preference", []),
                "special_needs": preferences.get("special_needs", []),
                "weather_sensitive": preferences.get("weather_sensitive", True),
                "preferences_collected": preferences.get("preferences_collected", False),
                "interaction_count": preferences["interaction_count"],
            }

            # 在message中如果有更新偏好的消息，则调用update_user_preferences工具来更新用户偏好(在state中更新)
            resp = self.agent.invoke(
                {"messages": messages},
                config=config,
                state=context,
            )

            # 将 Agent 执行后的 state 同步回 session_manager
            # 因为工具可能更新了 state 中的偏好信息，需要持久化到 session
            final_state = resp.get("state", {})
            if final_state:
                # 更新 session 中的偏好信息
                preferences["travel_interests"] = final_state.get("travel_interests", preferences.get("travel_interests", []))
                preferences["transport_preference"] = final_state.get("transport_preference", preferences.get("transport_preference", "未设置"))
                preferences["travel_pace"] = final_state.get("travel_pace", preferences.get("travel_pace", "未设置"))
                preferences["budget_level"] = final_state.get("budget_level", preferences.get("budget_level", "未设置"))
                preferences["accommodation_preference"] = final_state.get("accommodation_preference", preferences.get("accommodation_preference", []))
                preferences["food_preference"] = final_state.get("food_preference", preferences.get("food_preference", []))
                preferences["special_needs"] = final_state.get("special_needs", preferences.get("special_needs", []))
                preferences["weather_sensitive"] = final_state.get("weather_sensitive", preferences.get("weather_sensitive", True))
                preferences["preferences_collected"] = final_state.get("preferences_collected", preferences.get("preferences_collected", False))
                
                # 同步回 session_manager
                self.session_manager.update_session_preferences(session_id, preferences)

            answer = resp["structured_response"].answer
            answer = remove_duplicate_content(answer)
            # 在用户尚未设置偏好且本轮并非在描述偏好时，强制清理"已更新偏好"之类的不当表述
            if not preferences.get("preferences_collected", False) and not allow_pref_update:
                answer = sanitize_preference_answer(answer)
            
            return answer
        except Exception as e:
            return f"抱歉，处理您的请求时出现了错误：{str(e)}\n请尝试重新表述您的问题。"
    
    def get_session_preferences(self, session_id: str) -> UserPreferenceState:
        """获取指定会话的用户偏好。"""
        return self.session_manager.get_session_preferences(session_id)
    
    def update_session_preferences(
        self, 
        session_id: str, 
        preferences: UserPreferenceState
    ) -> None:
        """更新指定会话的用户偏好。"""
        self.session_manager.update_session_preferences(session_id, preferences)
