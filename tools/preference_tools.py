# -*- coding: utf-8 -*-
"""
用户偏好相关的工具函数
用于收集、更新和使用用户偏好信息
"""

from __future__ import annotations

from langchain.tools import tool, ToolRuntime

# 这个工具的作用是根据用户的偏好设置来具体更详细的给出推荐内容
# 最终返回一个兴趣偏好、出行方式、旅行节奏、预算水平等具体推荐建议信息的一个str
@tool
def get_personalized_recommendations(runtime: ToolRuntime, destination: str) -> str:
    """基于用户偏好生成个性化旅行推荐。
    
    根据用户的兴趣偏好、出行方式、旅行节奏、预算水平等信息，
    为用户提供定制化的旅行建议。
    
    Args:
        runtime (ToolRuntime): 运行时上下文，用于获取用户偏好
        destination (str): 目的地城市名称
        
    Returns:
        str: 个性化推荐内容
    """
    try:
        state = runtime.state
        
        # 获取用户偏好
        travel_interests = state.get("travel_interests", [])
        transport_preference = state.get("transport_preference", "未设置")
        travel_pace = state.get("travel_pace", "未设置")
        budget_level = state.get("budget_level", "未设置")
        accommodation_preference = state.get("accommodation_preference", [])
        food_preference = state.get("food_preference", [])
        special_needs = state.get("special_needs", [])
        weather_sensitive = state.get("weather_sensitive", True)
        
        # 构建个性化推荐
        recommendations = [f"🎯 为您定制的 {destination} 旅行建议：\n"]
        
        # 1. 基于兴趣的景点推荐
        if travel_interests:
            recommendations.append("📍 景点推荐（基于您的兴趣）：")
            
            interest_suggestions = {
                "历史文化": f"  • 推荐游览 {destination} 的历史古迹、博物馆和文化街区",
                "自然风光": f"  • 推荐前往 {destination} 的公园、风景区和自然景观",
                "美食体验": f"  • 推荐品尝 {destination} 的特色美食和地道小吃",
                "购物娱乐": f"  • 推荐逛 {destination} 的商业街区和娱乐场所",
                "亲子游玩": f"  • 推荐带孩子去 {destination} 的游乐园、动物园等亲子场所",
                "艺术文艺": f"  • 推荐参观 {destination} 的美术馆、艺术区和文艺空间",
            }
            
            for interest in travel_interests:
                if interest in interest_suggestions:
                    recommendations.append(interest_suggestions[interest])
            recommendations.append("")
        
        # 2. 基于出行方式的建议
        if transport_preference != "未设置":
            recommendations.append("🚗 出行方式建议：")
            
            transport_suggestions = {
                "步行": "  • 建议选择景点集中的区域，安排步行游览路线\n  • 每天安排2-3个相近的景点，避免过度劳累",
                "公交": "  • 建议提前了解当地公交/地铁线路\n  • 可以购买当地交通卡，方便又实惠",
                "自驾": "  • 建议提前规划好停车场位置\n  • 可以安排一些郊区或周边的景点，更加自由",
                "混合": "  • 建议市区内使用公共交通，郊区景点考虑打车或租车\n  • 灵活选择最合适的出行方式",
            }
            
            if transport_preference in transport_suggestions:
                recommendations.append(transport_suggestions[transport_preference])
            recommendations.append("")
        
        # 3. 基于旅行节奏的行程安排
        if travel_pace != "未设置":
            recommendations.append("⏰ 行程节奏建议：")
            
            pace_suggestions = {
                "悠闲": "  • 每天安排2-3个景点，留出充足的休息和自由活动时间\n  • 建议中午回酒店休息，避开人流高峰",
                "适中": "  • 每天安排3-4个景点，上午、下午各安排1-2个\n  • 保持张弛有度，既充实又不会太累",
                "紧凑": "  • 每天安排4-5个景点，充分利用时间\n  • 建议提前购买门票，减少排队时间",
            }
            
            if travel_pace in pace_suggestions:
                recommendations.append(pace_suggestions[travel_pace])
            recommendations.append("")
        
        # 4. 基于预算的消费建议
        if budget_level != "未设置":
            recommendations.append("💰 消费建议：")
            
            budget_suggestions = {
                "经济": "  • 推荐选择性价比高的餐厅和住宿\n  • 可以多尝试当地小吃和特色美食\n  • 优先选择免费或门票较低的景点",
                "舒适": "  • 推荐选择品质与价格平衡的餐厅和酒店\n  • 可以适当体验一些特色餐厅和精品酒店\n  • 景点选择更加灵活多样",
                "豪华": "  • 推荐选择高品质的餐厅和五星级酒店\n  • 可以体验米其林餐厅和特色高端体验\n  • 优先选择精品景点和VIP服务",
            }
            
            if budget_level in budget_suggestions:
                recommendations.append(budget_suggestions[budget_level])
            recommendations.append("")
        
        # 5. 基于住宿偏好的建议
        if accommodation_preference:
            recommendations.append("🏨 住宿建议：")
            recommendations.append(f"  • 根据您的偏好：{', '.join(accommodation_preference)}")
            recommendations.append("  • 建议提前预订，确保符合您的要求")
            recommendations.append("")
        
        # 6. 基于餐饮偏好的建议
        if food_preference:
            recommendations.append("🍜 餐饮建议：")
            recommendations.append(f"  • 根据您的偏好：{', '.join(food_preference)}")
            
            if "本地特色" in food_preference:
                recommendations.append(f"  • 推荐品尝 {destination} 的地道特色菜")
            if "网红餐厅" in food_preference:
                recommendations.append("  • 建议提前预约热门网红餐厅")
            if "街边小吃" in food_preference:
                recommendations.append("  • 推荐逛当地的美食街和夜市")
            recommendations.append("")
        
        # 7. 特殊需求提醒
        if special_needs:
            recommendations.append("⚠️ 特殊需求提醒：")
            
            if "带小孩" in special_needs:
                recommendations.append("  • 建议选择亲子友好的景点和餐厅")
                recommendations.append("  • 行程安排要考虑孩子的作息时间")
            if "带老人" in special_needs:
                recommendations.append("  • 建议选择无障碍设施完善的景点")
                recommendations.append("  • 行程节奏要放慢，多安排休息时间")
            if "无障碍设施" in special_needs:
                recommendations.append("  • 提前确认景点和酒店的无障碍设施")
            if "宠物友好" in special_needs:
                recommendations.append("  • 提前确认酒店和景点是否允许携带宠物")
            recommendations.append("")
        
        # 8. 天气相关建议
        if weather_sensitive:
            recommendations.append("🌤️ 天气提醒：")
            recommendations.append("  • 建议出发前查看天气预报")
            recommendations.append("  • 准备雨天备选方案（室内景点、博物馆等）")
            recommendations.append("")
        
        # 9. 总结
        recommendations.append("💡 温馨提示：")
        recommendations.append("  • 以上建议基于您的个人偏好定制")
        recommendations.append("  • 具体行程可以根据实际情况灵活调整")
        recommendations.append("  • 如需更详细的景点、餐厅或路线信息，请随时告诉我！")
        
        return "\n".join(recommendations)
        
    except Exception as e:
        return f"生成个性化推荐失败：{e}"

# 当用户输入偏好时，会使用该tool来更新用户偏好
@tool
def update_user_preferences(
    runtime: ToolRuntime,
    travel_interests: list[str] | None = None,
    transport_preference: str | None = None,
    travel_pace: str | None = None,
    budget_level: str | None = None,
) -> str:
    """更新用户偏好信息。
    
    用于在对话过程中更新用户的旅行偏好。
    
    Args:
        runtime (ToolRuntime): 运行时上下文
        travel_interests: 旅行兴趣列表
        transport_preference: 出行方式偏好
        travel_pace: 旅行节奏
        budget_level: 预算水平
        
    Returns:
        str: 更新结果
    """
    try:
        state = runtime.state
        
        updated_items = []
        
        if travel_interests is not None:
            state["travel_interests"] = travel_interests
            updated_items.append(f"兴趣偏好：{', '.join(travel_interests)}")
        
        if transport_preference is not None:
            state["transport_preference"] = transport_preference
            updated_items.append(f"出行方式：{transport_preference}")
        
        if travel_pace is not None:
            state["travel_pace"] = travel_pace
            updated_items.append(f"旅行节奏：{travel_pace}")
        
        if budget_level is not None:
            state["budget_level"] = budget_level
            updated_items.append(f"预算水平：{budget_level}")
        
        if updated_items:
            state["preferences_collected"] = True
            return f"✅ 已更新您的偏好：\n" + "\n".join(f"  • {item}" for item in updated_items)
        else:
            return "未提供需要更新的偏好信息"
            
    except Exception as e:
        return f"更新偏好失败：{e}"

