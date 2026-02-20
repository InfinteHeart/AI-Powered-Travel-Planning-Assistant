# -*- coding: utf-8 -*-
"""
文本处理工具函数
"""

from __future__ import annotations

import sys
from typing import List


def ensure_utf8_stdout() -> None:
    """尽量避免 Windows 控制台中文乱码（PowerShell/CMD 常见为 cp936/gbk）。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass


def remove_duplicate_content(text: str) -> str:
    """简单的重复内容检测和清理。"""
    if not text:
        return text

    # 0）检测前缀性的大段重复（例如整段回答重复两遍但中间有轻微差异）
    normalized = text.strip()
    if len(normalized) > 200:
        # 取前缀窗口，在后半段查找是否再次出现；若出现则截断到第二次出现之前
        prefix_len = min(len(normalized) // 2, 500)
        window = normalized[:prefix_len]
        idx = normalized.find(window, prefix_len)
        if idx != -1:
            return normalized[:idx].strip()

    # 1）优先处理整段文本被完整重复两遍的情况（A + A）
    if len(normalized) > 200:
        half = len(normalized) // 2
        first_half = normalized[:half].strip()
        second_half = normalized[half:].strip()
        if first_half and first_half == second_half:
            return first_half

    # 2）逐行去重
    lines = text.split("\n")
    seen = set()
    cleaned_lines: List[str] = []

    for line in lines:
        line_stripped = line.strip()
        if line_stripped and line_stripped not in seen:
            cleaned_lines.append(line)
            seen.add(line_stripped)

    # 3）段落级去重（两行空行视作一个段落分隔）
    paragraphs = text.split("\n\n")
    if len(paragraphs) > 1:
        unique_paras: List[str] = []
        seen_paras = set()
        for p in paragraphs:
            p_stripped = p.strip()
            if p_stripped and p_stripped not in seen_paras:
                unique_paras.append(p)
                seen_paras.add(p_stripped)

        if len(unique_paras) < len(paragraphs):
            return "\n\n".join(unique_paras)

    return "\n".join(cleaned_lines)


def sanitize_preference_answer(text: str) -> str:
    """
    在用户尚未设置偏好、且本轮输入也不是在描述偏好的情况下，
    清理模型回答中"擅自声明已为用户更新偏好"的句子，避免误导用户。
    """
    if not text:
        return text

    # 以句号/问号/感叹号和换行做一个粗略的句子切分
    sentences: List[str] = []
    buffer = ""
    for ch in text:
        buffer += ch
        if ch in ["。", "！", "？", "\n", "! ", "? "]:
            sentences.append(buffer)
            buffer = ""
    if buffer:
        sentences.append(buffer)

    danger_keywords = [
        "已为您更新", "已经为您更新", "已更新您的偏好", "已经更新您的偏好",
        "帮您更新了偏好", "为您设置了旅行偏好", "我先帮您假设一个偏好",
    ]

    cleaned: List[str] = []
    for sent in sentences:
        s_strip = sent.strip()
        # 只在同时包含「偏好」和若干"更新/设置/假设"表述时才认为是危险句子
        if "偏好" in s_strip and any(k in s_strip for k in danger_keywords):
            # 这一句直接丢弃，不向用户展示
            continue
        cleaned.append(sent)

    # 如果全部被删光，给出一个安全的 fallback 提示
    if not cleaned:
        return "当前尚未为您设置旅行偏好。如需个性化推荐，您可以输入“偏好”或直接告诉我您的旅行喜好、出行方式、节奏和预算。"

    return "".join(cleaned)

