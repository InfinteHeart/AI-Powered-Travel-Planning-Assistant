from __future__ import annotations

from langchain.tools import tool

from client.mcp_12306_stdio_client import (
    query_city_to_city_tickets_text,
    get_train_route_stations_text,
)


@tool
def query_train_tickets(
    from_city: str,
    to_city: str,
    days_after_today: int = 1,
    date: str | None = None,
    train_filter_flags: str = "G",
    limited_num: int = 5,
) -> str:
    """查询"城市到城市"的余票信息（默认查高铁G），返回 text 结果，适合直接展示给用户。

    Args:
        from_city (str): 出发城市，例如：北京
        to_city (str): 到达城市，例如：上海
        days_after_today (int): 当 date 为空时，以"今天+N天"作为查询日期，默认 1（明天）
        date (str|None): 指定日期（yyyy-MM-dd），传了就优先生效
        train_filter_flags (str): 车次过滤，例如：G / GD / 空字符串(不过滤)
        limited_num (int): 返回前 N 条，默认 5
    """
    return query_city_to_city_tickets_text(
        from_city=from_city,
        to_city=to_city,
        date=date,
        days_after_today=days_after_today,
        train_filter_flags=train_filter_flags,
        limited_num=limited_num,
    )


@tool
def get_train_route_stations(train_code: str, depart_date: str) -> str:
    """查询车次经停站信息（含到发时刻/停站时长等）。

    Args:
        train_code (str): 车次，例如：G1033
        depart_date (str): 发车日期（yyyy-MM-dd）
    """
    return get_train_route_stations_text(
        train_code=train_code,
        depart_date=depart_date,
        format="text",
    )


