"""
Agent 模块
包含旅行规划 Agent 和相关工作流

模块结构：
- agent.py: 主 Agent 类
- context_types.py: 类型定义（TravelContext, ResponseFormat）
- middleware.py: 中间件（动态系统提示词）
- session_manager.py: 会话管理
- preference_manager.py: 偏好管理
- text_utils.py: 文本处理工具
- cli.py: 命令行交互界面
- user_preference_state.py: 用户偏好状态定义
"""

from .agent import TravelPlanningAgent
from .context_types import TravelContext, ResponseFormat
from .user_preference_state import (
    UserPreferenceState,
    get_default_preferences,
    format_preferences_summary,
    get_preference_collection_prompt,
)

__all__ = [
    "TravelPlanningAgent",
    "TravelContext",
    "ResponseFormat",
    "UserPreferenceState",
    "get_default_preferences",
    "format_preferences_summary",
    "get_preference_collection_prompt",
]

