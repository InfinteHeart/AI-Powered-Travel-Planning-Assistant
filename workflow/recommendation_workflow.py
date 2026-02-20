"""
基于 LangGraph 的个性化推荐工作流
将地点搜索、评价查询、路线规划等步骤组织成结构化的工作流
"""

from __future__ import annotations

import json
from typing import TypedDict, Annotated, Literal
from typing_extensions import NotRequired

from langgraph.graph import StateGraph, END

class RecommendationState(TypedDict):
    """推荐工作流的状态"""
    # 用户输入
    user_query: str
    city: str
    
    # 用户偏好（从 Agent state 传入）
    travel_interests: list[str]
    transport_preference: str
    travel_pace: str
    budget_level: str
    
    # 中间结果
    poi_results: NotRequired[list[dict]]  # 地点搜索结果
    review_results: NotRequired[dict[str, str]]  # 评价查询结果（地点名 -> 评价）
    route_info: NotRequired[str]  # 路线规划信息
    hotel_results: NotRequired[str]  # 酒店推荐结果
    
    # 最终输出
    final_recommendation: NotRequired[str]
    
    # 流程控制
    next_step: NotRequired[str]


class RecommendationWorkflow:
    """个性化推荐工作流"""
    
    def __init__(self, runtime):
        """
        Args:
            runtime: Agent 的 ToolRuntime，用于访问 state
        """
        self.runtime = runtime
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建工作流图"""
        workflow = StateGraph(RecommendationState)
        
        # 添加节点
        workflow.add_node("search_pois", self._search_pois_node)
        workflow.add_node("query_reviews", self._query_reviews_node)
        workflow.add_node("search_hotels", self._search_hotels_node)
        workflow.add_node("plan_route", self._plan_route_node)
        workflow.add_node("generate_recommendation", self._generate_recommendation_node)
        
        # 定义边
        workflow.set_entry_point("search_pois")
        workflow.add_edge("search_pois", "query_reviews")
        workflow.add_conditional_edges(
            "query_reviews",
            self._should_search_hotels,
            {
                "search_hotels": "search_hotels",
                "skip_hotels": "plan_route"  # 跳过酒店后直接进入路线规划
            }
        )
        # 路线规划现在是必须执行的步骤
        workflow.add_edge("search_hotels", "plan_route")
        workflow.add_edge("plan_route", "generate_recommendation")
        workflow.add_edge("generate_recommendation", END)
        
        return workflow.compile()
    
    def _search_pois_node(self, state: RecommendationState) -> RecommendationState:
        """节点1：搜索地点（基于用户偏好）"""
        print("🔍 搜索符合偏好的地点...")
        
        city = state["city"]
        interests = state.get("travel_interests", [])
        
        # 根据兴趣生成搜索关键词
        interest_keywords_map = {
            "历史文化": ["博物馆", "古迹", "文化街区"],
            "自然风光": ["公园", "风景区", "山水"],
            "美食体验": ["美食", "餐厅", "特色小吃"],
            "购物娱乐": ["商场", "购物中心", "娱乐场所"],
            "亲子游玩": ["游乐园", "动物园", "儿童乐园"],
            "艺术文艺": ["美术馆", "艺术馆", "剧院"],
        }
        
        # 收集所有相关关键词
        keywords_to_search = []
        for interest in interests:
            if interest in interest_keywords_map:
                keywords_to_search.extend(interest_keywords_map[interest])
        
        # 如果没有兴趣偏好，使用通用关键词
        if not keywords_to_search:
            keywords_to_search = ["景点", "美食"]
        
        # 搜索地点（每个关键词搜索一次，取前3个结果）
        all_pois = []
        for keyword in keywords_to_search[:3]:  # 限制搜索次数
            try:
                # 直接调用高德 API，不通过工具（避免 runtime 类型问题）
                from client.gaode_client import gaode_get_json_str
                raw_result = gaode_get_json_str(
                    "/v3/place/text",
                    {"city": city, "keywords": keyword},
                    timeout=10
                )
                data = json.loads(raw_result)
                
                if data.get("status") == "1" and data.get("pois"):
                    pois = data["pois"][:3]  # 每个关键词取前3个
                    all_pois.extend(pois)
                    # 移除详细打印，只保留主要步骤标题
                    
            except Exception as e:
                # 静默处理错误，不打印详细信息
                continue
        
        # 移除详细打印
        state["poi_results"] = all_pois
        return state
    
    def _query_reviews_node(self, state: RecommendationState) -> RecommendationState:
        """节点2：查询地点评价（仅针对具体景点/美食）"""
        print("🔍 查询地点评价...")
        
        pois = state.get("poi_results", [])
        city = state["city"]
        review_results = {}
        
        # 为每个地点查询评价（限制数量避免过多请求）
        for poi in pois[:5]:  # 最多查询5个地点的评价
            poi_name = poi.get("name", "")
            poi_type = poi.get("type", "")
            if not poi_name:
                continue
            
            try:
                # 直接调用搜索工具，只搜索具体景点/美食的评价
                # 关键优化：明确搜索"景点名+评价/怎么样"，避免搜索宽泛的攻略
                from tools.web_search_tools import tavily_search_reviews
                
                # 构建精确的搜索查询，避免搜索攻略
                search_query = f"{city} {poi_name} 怎么样 评价"
                
                review_text = tavily_search_reviews(
                    query=search_query,
                    location=city
                )
                
                # 只保留有效的评价信息（过滤掉攻略类内容）
                if review_text and len(review_text.strip()) > 0:
                    # 简单过滤：如果包含"攻略"、"行程"、"路线"等关键词，说明搜到了攻略而非评价
                    filter_keywords = ["攻略", "行程安排", "路线规划", "第一天", "第二天", "第三天", "Day1", "Day2"]
                    is_guide = any(kw in review_text for kw in filter_keywords)
                    
                    if not is_guide:
                        review_results[poi_name] = review_text
                
            except Exception as e:
                # 静默处理错误，不打印详细信息
                continue
        
        state["review_results"] = review_results
        return state
    
    def _should_search_hotels(self, state: RecommendationState) -> Literal["search_hotels", "skip_hotels"]:
        """条件边：判断是否需要搜索酒店"""
        # 如果用户明确提到酒店、住宿、住等，则搜索酒店
        user_query = state.get("user_query", "").lower()
        hotel_keywords = ["酒店", "住宿", "住", "宾馆", "饭店", "旅馆", "民宿", "订房"]
        
        # 如果用户查询中包含"行程"、"规划"、"安排"等，且没有明确排除住宿，也搜索酒店
        travel_keywords = ["行程", "规划", "安排", "旅游", "游玩", "旅行"]
        if any(kw in user_query for kw in travel_keywords):
            # 检查是否明确排除住宿
            exclude_keywords = ["不住", "不需要住宿", "一日游", "当天往返"]
            if not any(kw in user_query for kw in exclude_keywords):
                return "search_hotels"
        
        if any(kw in user_query for kw in hotel_keywords):
            return "search_hotels"
        return "skip_hotels"
    
    def _search_hotels_node(self, state: RecommendationState) -> RecommendationState:
        """节点：搜索酒店（可选）"""
        print("🔍 步骤3：搜索酒店...")
        
        city = state["city"]
        budget_level = state.get("budget_level", "未设置")
        
        try:
            # 直接调用酒店搜索客户端（不使用工具装饰器）
            from client.aigohotel_client import aigohotel_search_hotels
            from datetime import datetime, timedelta
            
            # 默认使用次日，入住1晚
            tomorrow = datetime.now() + timedelta(days=1)
            check_in = tomorrow.strftime("%Y-%m-%d")
            
            # 根据预算设置星级范围
            star_ratings = None
            if budget_level == "经济":
                star_ratings = [0.0, 3.0]
            elif budget_level == "舒适":
                star_ratings = [3.0, 4.5]
            elif budget_level == "豪华":
                star_ratings = [4.5, 5.0]
            
            # 调用酒店搜索客户端
            result_json = aigohotel_search_hotels(
                place=city,
                place_type="城市",
                origin_query=state.get("user_query", f"在{city}搜索酒店"),
                check_in=check_in,
                stay_nights=1,
                star_ratings=star_ratings,
                size=5,
            )
            
            # 解析并格式化结果
            try:
                import json
                import re
                data = json.loads(result_json)
                
                if "error" not in data and "hotelInformationList" in data:
                    hotels = data["hotelInformationList"]
                    
                    if hotels:
                        # 格式化酒店信息
                        hotel_text = f"\n## 🏨 酒店推荐（共 {len(hotels)} 家）\n\n"
                        for idx, hotel in enumerate(hotels[:5], 1):
                            name = hotel.get("name", "未知酒店")
                            address = hotel.get("address", "地址未知")
                            star_rating = hotel.get("starRating", 0)
                            
                            # 价格信息
                            price_info = hotel.get("price", {})
                            price = 0
                            currency = "CNY"
                            if isinstance(price_info, dict):
                                price = price_info.get("lowestPrice", 0)
                                currency = price_info.get("currency", "CNY")
                            
                            hotel_text += f"{idx}. **{name}**\n"
                            if star_rating > 0:
                                hotel_text += f"   ⭐ {star_rating} 星"
                            if price > 0:
                                hotel_text += f" | 💰 {currency} {price:.2f}/晚\n"
                            else:
                                hotel_text += "\n"
                            hotel_text += f"   📍 {address}\n\n"
                        
                        state["hotel_results"] = hotel_text
                    else:
                        state["hotel_results"] = f"\n在{city}未找到符合条件的酒店。\n"
                else:
                    state["hotel_results"] = ""
                    
            except Exception as e:
                state["hotel_results"] = ""
                print(f"   ⚠️ 解析酒店数据失败: {str(e)}")
                
        except Exception as e:
            state["hotel_results"] = ""
            print(f"   ⚠️ 酒店搜索失败: {str(e)}")
        
        return state
    
    def _plan_route_node(self, state: RecommendationState) -> RecommendationState:
        """节点4：规划路线 - 调用路线规划客户端获取实际路线"""
        print("🔍 步骤4：规划路线...")
        
        pois = state.get("poi_results", [])
        transport_pref = state.get("transport_preference", "未设置")
        city = state["city"]
        
        if not pois or len(pois) < 2:
            # 如果地点少于2个，无法规划路线
            route_info = f"\n## 🗺️ 路线规划建议\n\n"
            if not pois:
                route_info += "暂无地点信息，无法规划路线。\n"
            else:
                route_info += f"仅有1个地点，建议直接前往：\n\n"
                poi = pois[0]
                route_info += f"**{poi.get('name', '未知')}**\n"
                route_info += f"地址：{poi.get('address', '未知')}\n"
            state["route_info"] = route_info
            return state
        
        # 构建路线规划信息
        route_info = f"\n## 🗺️ 详细路线规划\n\n"
        
        # 选择前5个地点进行路线规划
        selected_pois = pois[:5]
        
        # 根据用户偏好选择路线规划方式
        if transport_pref == "步行":
            route_info += "### 步行路线\n\n"
            route_info = self._plan_walking_routes(route_info, selected_pois)
            
        elif transport_pref == "公交":
            route_info += "### 公交/地铁路线\n\n"
            route_info = self._plan_transit_routes(route_info, selected_pois, city)
            
        elif transport_pref == "自驾":
            route_info += "### 自驾路线\n\n"
            route_info = self._plan_driving_routes(route_info, selected_pois)
            
        else:
            # 未设置偏好，提供公交路线（最常用）
            route_info += "### 公交/地铁路线（推荐）\n\n"
            route_info = self._plan_transit_routes(route_info, selected_pois, city)
        
        state["route_info"] = route_info
        return state
    
    def _plan_walking_routes(self, route_info: str, pois: list[dict]) -> str:
        """规划步行路线"""
        from client.route_planning_client import plan_walking_route
        
        for i in range(len(pois) - 1):
            origin_poi = pois[i]
            dest_poi = pois[i + 1]
            
            origin_name = origin_poi.get("name", "未知")
            dest_name = dest_poi.get("name", "未知")
            origin_location = origin_poi.get("location", "")
            dest_location = dest_poi.get("location", "")
            
            route_info += f"#### {i+1}. {origin_name} → {dest_name}\n\n"
            
            if not origin_location or not dest_location:
                route_info += f"⚠️ 缺少位置信息，无法规划路线\n\n"
                continue
            
            # 调用路线规划客户端
            result = plan_walking_route(
                origin=origin_location,
                destination=dest_location,
                origin_name=origin_name,
                dest_name=dest_name
            )
            
            if result["success"]:
                distance = result["distance"]
                duration = result["duration"]
                steps = result.get("steps", [])
                
                route_info += f"📍 **距离**：{distance}米 | ⏱️ **步行时间**：约{duration//60}分钟\n\n"
                
                # 解析步行步骤
                if steps:
                    route_info += "**详细步骤**：\n\n"
                    for idx, step in enumerate(steps, 1):
                        instruction = step.get("instruction", "")
                        step_distance = int(float(step.get("distance", 0)))
                        route_info += f"{idx}. {instruction}（{step_distance}米）\n"
                    route_info += "\n"
            else:
                route_info += f"⚠️ 路线查询失败：{result.get('error', '未知错误')}\n\n"
        
        return route_info
    
    def _plan_transit_routes(self, route_info: str, pois: list[dict], city: str) -> str:
        """规划公交/地铁路线"""
        from client.route_planning_client import plan_transit_route
        
        for i in range(len(pois) - 1):
            origin_poi = pois[i]
            dest_poi = pois[i + 1]
            
            origin_name = origin_poi.get("name", "未知")
            dest_name = dest_poi.get("name", "未知")
            origin_location = origin_poi.get("location", "")
            dest_location = dest_poi.get("location", "")
            
            route_info += f"#### {i+1}. {origin_name} → {dest_name}\n\n"
            
            if not origin_location or not dest_location:
                route_info += f"⚠️ 缺少位置信息，无法规划路线\n\n"
                continue
            
            # 调用路线规划客户端
            result = plan_transit_route(
                origin=origin_location,
                destination=dest_location,
                city=city,
                origin_name=origin_name,
                dest_name=dest_name
            )
            
            if result["success"]:
                transits = result.get("transits", [])
                
                # 显示前2个方案
                for plan_idx, transit in enumerate(transits, 1):
                    # 安全转换：先转float再转int，处理字符串类型的数字
                    cost = int(float(transit.get("cost", 0)))
                    duration = int(float(transit.get("duration", 0)))
                    walking_distance = int(float(transit.get("walking_distance", 0)))
                    
                    route_info += f"**方案{plan_idx}**：⏱️ 约{duration//60}分钟 | 💰 {cost}元 | 🚶 步行{walking_distance}米\n\n"
                    
                    # 解析换乘步骤
                    segments = transit.get("segments", [])
                    for seg_idx, segment in enumerate(segments, 1):
                        # 步行段
                        walking = segment.get("walking")
                        if walking:
                            walk_distance = int(float(walking.get("distance", 0)))
                            if walk_distance > 0:
                                route_info += f"   {seg_idx}. 🚶 步行 {walk_distance}米\n"
                        
                        # 公交/地铁段
                        bus = segment.get("bus")
                        if bus:
                            buslines = bus.get("buslines", [])
                            for busline in buslines:
                                bus_name = busline.get("name", "")
                                departure_stop = busline.get("departure_stop", {}).get("name", "")
                                arrival_stop = busline.get("arrival_stop", {}).get("name", "")
                                via_num = int(float(busline.get("via_num", 0)))
                                bus_type = busline.get("type", "")
                                
                                # 判断是地铁还是公交
                                icon = "🚇" if "地铁" in bus_type else "🚌"
                                
                                route_info += f"   {seg_idx}. {icon} 乘坐 **{bus_name}**\n"
                                route_info += f"      上车：{departure_stop}\n"
                                route_info += f"      下车：{arrival_stop}（经过{via_num}站）\n"
                    
                    route_info += "\n"
            else:
                route_info += f"⚠️ 路线查询失败：{result.get('error', '未知错误')}\n\n"
        
        return route_info
    
    def _plan_driving_routes(self, route_info: str, pois: list[dict]) -> str:
        """规划自驾路线"""
        from client.route_planning_client import plan_driving_route
        
        for i in range(len(pois) - 1):
            origin_poi = pois[i]
            dest_poi = pois[i + 1]
            
            origin_name = origin_poi.get("name", "未知")
            dest_name = dest_poi.get("name", "未知")
            origin_location = origin_poi.get("location", "")
            dest_location = dest_poi.get("location", "")
            
            route_info += f"#### {i+1}. {origin_name} → {dest_name}\n\n"
            
            if not origin_location or not dest_location:
                route_info += f"⚠️ 缺少位置信息，无法规划路线\n\n"
                continue
            
            # 调用路线规划客户端
            result = plan_driving_route(
                origin=origin_location,
                destination=dest_location,
                origin_name=origin_name,
                dest_name=dest_name
            )
            
            if result["success"]:
                distance = result["distance"]
                duration = result["duration"]
                tolls = result.get("tolls", 0)
                traffic_lights = result.get("traffic_lights", 0)
                steps = result.get("steps", [])
                
                route_info += f"🚗 **距离**：{distance/1000:.1f}公里 | ⏱️ **驾车时间**：约{duration//60}分钟\n"
                if tolls > 0:
                    route_info += f"💰 **过路费**：约{tolls}元 | "
                route_info += f"🚦 **红绿灯**：{traffic_lights}个\n\n"
                
                # 解析驾车步骤（简化版，只显示主要道路）
                if steps and len(steps) <= 10:  # 步骤不太多时才显示
                    route_info += "**主要路线**：\n\n"
                    for idx, step in enumerate(steps, 1):
                        instruction = step.get("instruction", "")
                        step_distance = int(float(step.get("distance", 0)))
                        road = step.get("road", "")
                        if road:
                            route_info += f"{idx}. {instruction}，沿{road}行驶{step_distance}米\n"
                        else:
                            route_info += f"{idx}. {instruction}（{step_distance}米）\n"
                    route_info += "\n"
            else:
                route_info += f"⚠️ 路线查询失败：{result.get('error', '未知错误')}\n\n"
        
        return route_info
    
    def _generate_recommendation_node(self, state: RecommendationState) -> RecommendationState:
        """节点5：生成最终推荐（优先展示路线规划）"""
        print("🔍 生成个性化推荐...")
        
        pois = state.get("poi_results", [])
        reviews = state.get("review_results", {})
        route_info = state.get("route_info", "")
        hotel_results = state.get("hotel_results", "")
        
        # 构建推荐文本 - 优化结构，路线规划放在前面
        recommendation = ""
        
        # 1. 首先展示路线规划（最重要的信息）
        if route_info:
            recommendation += route_info + "\n"
        
        # 2. 展示酒店推荐（如果有）
        if hotel_results:
            recommendation += hotel_results + "\n"
        
        # 3. 展示景点详情和评价
        recommendation += f"## 🎯 景点详细信息\n\n"
        recommendation += f"根据您的偏好（{', '.join(state.get('travel_interests', []))}），"
        recommendation += f"为您精选了 {len(pois)} 个地点：\n\n"
        
        for idx, poi in enumerate(pois, 1):
            name = poi.get("name", "未知")
            address = poi.get("address", "未知")
            poi_type = poi.get("type", "")
            
            recommendation += f"### {idx}. {name}\n"
            recommendation += f"📍 地址：{address}\n"
            if poi_type:
                recommendation += f"🏷️ 类型：{poi_type}\n"
            
            # 添加评价信息（如果有）
            if name in reviews:
                review = reviews[name]
                # 提取评价摘要（取前150字，避免过长）
                review_summary = review[:150] + "..." if len(review) > 150 else review
                recommendation += f"💬 评价：{review_summary}\n"
            
            recommendation += "\n"
        
        # 4. 添加个性化建议
        budget = state.get("budget_level", "未设置")
        pace = state.get("travel_pace", "未设置")
        
        recommendation += f"## 💡 温馨提示\n\n"
        
        tips = []
        if budget == "经济":
            tips.append("建议选择免费或低价景点，控制餐饮预算")
        elif budget == "豪华":
            tips.append("可以选择高端餐厅和五星级酒店，享受优质服务")
        
        if pace == "悠闲":
            tips.append("建议每天安排2-3个景点，留出充足的休息时间")
        elif pace == "紧凑":
            tips.append("可以安排更多景点，充分利用时间")
        
        # 添加通用建议
        tips.append("建议提前查看景点开放时间，避免白跑一趟")
        tips.append("可以使用高德地图实时导航，获取最新路况信息")
        
        for tip in tips:
            recommendation += f"- {tip}\n"
        
        state["final_recommendation"] = recommendation
        print("   ✅ 推荐生成完成")
        return state
    
    def run(self, user_query: str, city: str) -> str:
        """运行工作流"""
        # 从 runtime.state 获取用户偏好
        state_data = self.runtime.state
        
        initial_state: RecommendationState = {
            "user_query": user_query,
            "city": city,
            "travel_interests": state_data.get("travel_interests", []),
            "transport_preference": state_data.get("transport_preference", "未设置"),
            "travel_pace": state_data.get("travel_pace", "未设置"),
            "budget_level": state_data.get("budget_level", "未设置"),
        }
        
        # 执行工作流
        final_state = self.graph.invoke(initial_state)
        
        return final_state.get("final_recommendation", "推荐生成失败")


def create_recommendation_workflow_tool(runtime):
    """创建推荐工作流工具（供 Agent 调用）"""
    from langchain.tools import tool
    
    @tool
    def get_structured_recommendations(city: str, query: str = "") -> str:
        """
        获取结构化的个性化推荐（使用工作流）
        
        这个工具会：
        1. 根据用户偏好搜索合适的地点
        2. 查询这些地点的真实评价
        3. 搜索酒店（如果需要）
        4. 规划路线（必须执行，包括公交/地铁/步行/自驾路线）
        5. 生成综合推荐
        
        Args:
            city: 城市名称，例如"北京"、"上海"
            query: 用户的具体需求，例如"推荐景点"、"美食推荐"
        
        Returns:
            结构化的个性化推荐文本
        """
        workflow = RecommendationWorkflow(runtime)
        return workflow.run(query or "推荐", city)
    
    return get_structured_recommendations

