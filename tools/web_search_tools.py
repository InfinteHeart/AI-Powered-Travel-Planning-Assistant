"""
网络搜索工具
使用 Tavily API 提供网络搜索功能，获取最新的实时信息

主要用于：
- 查询景点、商场、餐厅的真实评价和口碑
- 获取当地美食、特色菜的最新评价
- 搜索旅游目的地的实时信息和用户反馈
"""

from typing import Optional, List
from langchain_core.tools import tool
import os
from dotenv import load_dotenv
load_dotenv()

Tavily_API_Key = os.getenv("TAVILY_API_KEY")

# 尝试导入新的 Tavily 包，如果失败则使用旧的
try:
    from langchain_tavily import TavilySearchResults as TavilySearch
    USING_NEW_TAVILY = True
except ImportError:
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults as TavilySearch
        USING_NEW_TAVILY = False
    except ImportError:
        TavilySearch = None
        USING_NEW_TAVILY = False


def create_tavily_search_tool(
    max_results: int = 5,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
):
    """
    创建 Tavily 搜索工具实例
    
    Args:
        max_results: 返回的最大结果数（默认5条）
        include_domains: 限制搜索的域名列表（如：["dianping.com", "mafengwo.cn"]）
        exclude_domains: 排除的域名列表
        
    Returns:
        配置好的 Tavily 搜索工具实例
    """
    if TavilySearch is None:
        raise ValueError(
            "Tavily 搜索工具未安装！请安装: pip install langchain-tavily"
        )
        
    if not Tavily_API_Key:
        raise ValueError(
            "Tavily API Key 未设置！请在环境变量或 .env 文件中设置 TAVILY_API_KEY"
        )
    
    tool_kwargs = {
        "max_results": max_results,
        "api_key": Tavily_API_Key,
    }
    
    # 根据版本添加域名过滤参数
    if USING_NEW_TAVILY:
        if include_domains is not None:
            tool_kwargs["include_domains"] = include_domains
        if exclude_domains is not None:
            tool_kwargs["exclude_domains"] = exclude_domains
    else:
        tool_kwargs["include_domains"] = include_domains if include_domains is not None else []
        tool_kwargs["exclude_domains"] = exclude_domains if exclude_domains is not None else []
    
    try:
        import warnings
        # 抑制 LangChain 弃用警告
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")
            tool = TavilySearch(**tool_kwargs)
        return tool
    except Exception as e:
        print(f"❌ 创建 Tavily 工具失败: {e}")
        raise


def tavily_search_reviews(query: str, location: str = "") -> str:
    """
    底层搜索评价函数（供工作流等内部调用）
    
    Args:
        query: 要查询的内容
        location: 可选的地点信息
        
    Returns:
        搜索结果文本
    """
    try:
        if not Tavily_API_Key:
            print(f"❌ Tavily API Key 未设置，无法执行搜索")
            return (
                "抱歉，网络搜索功能暂时不可用（未配置 Tavily API Key）。"
                "请在 .env 文件中设置 TAVILY_API_KEY。"
            )
        
        # 构建更精确的搜索查询
        search_query = f"{location} {query}" if location else query
        
        # 添加评价相关关键词，提高搜索精准度
        if not any(kw in search_query for kw in ["评价", "怎么样", "好不好", "推荐", "口碑"]):
            search_query += " 评价 推荐"
        
        # 移除详细打印，只保留工作流主要步骤标题
        
        # 创建搜索工具（优先搜索评价类网站）
        search_tool = create_tavily_search_tool(
            max_results=5,
            # 可以优先搜索这些评价网站（可选）
            # include_domains=["dianping.com", "mafengwo.cn", "ctrip.com", "xiaohongshu.com"]
        )
        
        results = search_tool.invoke({"query": search_query})
        
        if not results:
            # 静默处理，不打印错误信息
            return f"未找到关于 '{query}' 的评价信息。建议换个关键词试试。"
        
        # 格式化结果，突出评价信息
        formatted_results = [f"📊 找到 {len(results)} 条关于「{query}」的评价信息：\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "无标题")
            content = result.get("content", "")
            url = result.get("url", "")
            
            # 截断过长的内容，保留关键评价信息
            if len(content) > 300:
                content = content[:300] + "..."
            
            formatted_results.append(f"\n{i}. {title}")
            if content:
                formatted_results.append(f"   💬 {content}")
            if url:
                formatted_results.append(f"   🔗 来源: {url}")
        
        result_text = "\n".join(formatted_results)
        # 移除详细打印，只保留工作流主要步骤标题
        return result_text
        
    except Exception as e:
        error_msg = f"搜索评价时发生错误: {str(e)}"
        print(f"❌ {error_msg}")
        return f"抱歉，{error_msg}"


@tool
def search_reviews(
    query: str,
    location: str = ""
) -> str:
    """
    搜索景点、餐厅、商场、美食等的真实评价和口碑信息
    
    专门用于获取用户对旅游相关内容的真实评价，包括：
    - 景点评价（如：故宫怎么样、外滩值得去吗）
    - 餐厅评价（如：海底捞服务好吗、某某餐厅味道如何）
    - 商场评价（如：南京路步行街购物体验）
    - 美食评价（如：北京烤鸭哪家好吃、小笼包推荐）
    - 酒店评价（如：某某酒店住宿体验）
    
    Args:
        query: 要查询的内容，例如"北京故宫评价"、"上海小笼包推荐"
        location: 可选的地点信息，帮助精确搜索，例如"北京"、"上海"
        
    Returns:
        包含真实用户评价、评分、推荐理由等信息的搜索结果
        
    Example:
        >>> search_reviews("故宫博物院评价", "北京")
        >>> search_reviews("海底捞火锅怎么样", "上海")
        >>> search_reviews("小笼包哪家好吃", "上海")
    """
    return tavily_search_reviews(query, location)


@tool
def search_travel_info(query: str) -> str:
    """
    搜索旅游相关的实时信息和最新资讯
    
    用于获取旅游目的地的最新信息，包括：
    - 旅游攻略和游记
    - 最新的旅游资讯和活动
    - 交通和住宿的最新信息
    - 旅游注意事项和建议
    
    Args:
        query: 搜索查询，例如"北京旅游攻略"、"上海迪士尼最新信息"
        
    Returns:
        搜索结果摘要，包含最新的旅游信息
        
    Example:
        >>> search_travel_info("北京三日游攻略")
        >>> search_travel_info("上海迪士尼门票价格")
    """
    
    try:
        if not Tavily_API_Key:
            return "网络搜索功能暂时不可用（未配置 API Key）"
        
        print(f"🔍 搜索旅游信息: {query}")
        
        search_tool = create_tavily_search_tool(max_results=5)
        results = search_tool.invoke({"query": query})
        
        if not results:
            return f"未找到关于 '{query}' 的相关信息。"
        
        formatted_results = [f"🗺️ 找到 {len(results)} 条旅游信息：\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "无标题")
            content = result.get("content", "")
            url = result.get("url", "")
            
            if len(content) > 250:
                content = content[:250] + "..."
            
            formatted_results.append(f"\n{i}. {title}")
            if content:
                formatted_results.append(f"   📝 {content}")
            if url:
                formatted_results.append(f"   🔗 {url}")
        
        result_text = "\n".join(formatted_results)
        # 移除详细打印，只保留工作流主要步骤标题
        return result_text
        
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return f"搜索失败: {str(e)}"