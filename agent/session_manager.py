# -*- coding: utf-8 -*-
"""
会话管理：创建会话、管理会话偏好
"""

from __future__ import annotations

from typing import Dict

from agent.user_preference_state import (
    UserPreferenceState,
    get_default_preferences,
)


class SessionManager:
    """会话管理器：负责创建和管理会话及其偏好状态。"""

    def __init__(self) -> None:
        self.thread_id_counter = 0
        self.session_preferences: Dict[str, UserPreferenceState] = {}

    def create_new_session(self) -> str:
        """创建新的对话会话，并返回 session_id（即 thread_id）。"""
        self.thread_id_counter += 1
        session_id = f"session_{self.thread_id_counter}"
        
        # 为新会话初始化默认偏好
        self.session_preferences[session_id] = get_default_preferences()
        
        return session_id

    def get_session_preferences(self, session_id: str) -> UserPreferenceState:
        """获取指定会话的用户偏好。"""
        if session_id not in self.session_preferences:
            self.session_preferences[session_id] = get_default_preferences()
        return self.session_preferences[session_id]
    
    def update_session_preferences(
        self, 
        session_id: str, 
        preferences: UserPreferenceState
    ) -> None:
        """更新指定会话的用户偏好。"""
        self.session_preferences[session_id] = preferences

    def ensure_session_exists(self, session_id: str) -> None:
        """确保会话存在，如果不存在则创建。"""
        if session_id not in self.session_preferences:
            self.session_preferences[session_id] = get_default_preferences()

