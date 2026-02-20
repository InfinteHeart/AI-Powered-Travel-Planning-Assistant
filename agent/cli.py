# -*- coding: utf-8 -*-
"""
命令行交互界面
"""

from __future__ import annotations

import os
import sys

# 确保可以从项目根目录导入
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.agent import TravelPlanningAgent
from agent.text_utils import ensure_utf8_stdout
from agent.user_preference_state import (
    format_preferences_summary,
    get_preference_collection_prompt,
)


def interactive_chat() -> None:
    """命令行交互模式。"""
    ensure_utf8_stdout()

    print("=" * 60)
    print("欢迎使用旅行规划智能助手！")
    print("我可以帮您：")
    print("1. 查询火车票信息（高铁、动车等）")
    print("2. 查询车次经停站信息")
    print("3. 查询目的地天气")
    print("4. 搜索周边兴趣点（美食、景点等）")
    print("5. 规划公交/步行/驾车路线")
    print("6. 🎯 基于您的偏好生成个性化推荐")
    print("7. 🔍 搜索景点、餐厅、美食的真实评价和口碑")
    print("8. 🏨 搜索和推荐酒店")
    print("\n特点：")
    print("• 🆕 支持个性化偏好设置，为您定制专属旅行方案")
    print("• 🆕 支持网络搜索，获取最新的评价和口碑信息")
    print("• 🆕 支持酒店搜索和推荐")
    print("\n输入 '退出' 或 'quit' 结束对话")
    print("输入 '帮助' 或 'help' 查看功能说明")
    print("输入 '重置' 或 'reset' 开始新的对话")
    print("输入 '偏好' 或 'preference' 查看或设置您的旅行偏好")
    print("=" * 60)

    agent = TravelPlanningAgent()
    session_id = agent.create_new_session()
    
    # 询问用户是否要设置偏好
    print("\n" + "-" * 60)
    print("🎯 为了给您提供更个性化的旅行推荐，建议先设置您的旅行偏好。")
    print("您可以：")
    print("1. 现在设置偏好（输入 '是' 或 'y'）")
    print("2. 稍后再说（输入 '否' 或 'n'，或直接开始提问）")
    print("-" * 60)
    
    setup_choice = input("是否现在设置偏好？").strip().lower()
    
    if setup_choice in ['是', 'y', 'yes', '好', '设置', '可以']:
        print("\n" + get_preference_collection_prompt())
        print("\n请告诉我您的偏好：")
        preference_input = input("您：").strip()
        
        if preference_input:
            print("\n助手：", end="")
            response = agent.get_response(preference_input, session_id)
            print(response)

    while True:
        try:
            print("\n" + "-" * 60)
            user_input = input("您：").strip()

            if user_input.lower() in ["退出", "quit", "exit", "bye", "goodbye"]:
                print("\n感谢使用旅行规划助手，祝您旅途愉快！")
                break

            if user_input.lower() in ["重置", "reset", "重新开始", "新对话"]:
                session_id = agent.create_new_session()
                print("\n已开始新的对话。")
                print("提示：您可以输入 '偏好' 来设置新的旅行偏好。")
                continue
            
            if user_input.lower() in ["偏好", "preference", "设置偏好", "我的偏好"]:
                preferences = agent.get_session_preferences(session_id)
                
                if preferences.get("preferences_collected"):
                    # 已设置偏好，显示当前偏好
                    print("\n" + format_preferences_summary(preferences))
                    print("\n如需修改偏好，请直接告诉我，例如：")
                    print("'我想改成喜欢自然风光' 或 '我想改成紧凑节奏'")
                    print("如不需要修改，请直接提问其他问题。")
                else:
                    # 未设置偏好，提示设置
                    print("\n您还没有设置旅行偏好。")
                    print("\n" + get_preference_collection_prompt())
                continue

            if user_input.lower() in ["帮助", "help", "?"]:
                _print_help()
                continue

            if not user_input:
                print("请输入您的问题...")
                continue

            print("\n助手：", end="")
            response = agent.get_response(user_input, session_id)
            print(response)

        except KeyboardInterrupt:
            print("\n\n对话已中断。")
            break
        except EOFError:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n抱歉，发生了一个错误：{str(e)}")
            print("请重新尝试输入您的问题。")


def _print_help() -> None:
    """打印帮助信息。"""
    print("\n" + "=" * 60)
    print("我能帮您做以下事情：")
    print("\n1. 交通规划 - 例如：")
    print("   • '查一下明天北京到上海的高铁票'")
    print("   • '后天从广州去深圳的动车'")
    print("   • '查询G123次列车的经停站'")
    print()
    print("2. 天气查询 - 例如：")
    print("   • '上海明天天气怎么样'")
    print("   • '北京这周末的天气预报'")
    print()
    print("3. 地点查询 - 例如：")
    print("   • '外滩的地理位置'")
    print("   • '上海迪士尼的坐标'")
    print()
    print("4. 周边搜索 - 例如：")
    print("   • '北京有哪些好吃的'")
    print("   • '上海外滩周边景点'")
    print()
    print("5. 路线规划 - 例如：")
    print("   • '从上海站到外滩怎么坐公交'")
    print("   • '从人民广场步行到南京路'")
    print()
    print("6. 综合旅行规划 - 例如：")
    print("   • '我想去北京玩3天，帮我规划一下行程'")
    print("   • '周末去上海迪士尼，请帮我安排'")
    print()
    print("7. 🎯 个性化推荐 - 例如：")
    print("   • '我喜欢历史文化和美食，喜欢步行，节奏悠闲'")
    print("   • '给我推荐适合我的北京景点'")
    print("   • 输入 '偏好' 查看或修改您的旅行偏好")
    print()
    print("8. 🔍 评价查询 - 例如：")
    print("   • '故宫怎么样，值得去吗'")
    print("   • '北京烤鸭哪家好吃'")
    print("   • '海底捞火锅评价如何'")
    print("   • '上海小笼包推荐'")
    print("   • '南京路步行街购物体验怎么样'")
    print()
    print("9. 🏨 酒店推荐 - 例如：")
    print("   • '北京有什么好酒店'")
    print("   • '推荐一下上海的酒店'")
    print("   • '外滩附近有什么酒店'")
    print("\n对话特点：")
    print("• 使用 dynamic_prompt 自动选择合适的系统提示词（交通 / 目的地 / 评价 / 综合）")
    print("• 使用 SummarizationMiddleware 自动对长对话做摘要，保留关键信息")
    print("• 🆕 根据您的个人偏好提供定制化推荐")
    print("• 🆕 支持网络搜索，获取真实评价和最新信息")
    print("• 🆕 支持酒店搜索和推荐")
    print("• 可以进行多轮连续对话")
    print("=" * 60)


def main() -> None:
    """入口函数：启动交互式聊天。"""
    interactive_chat()


if __name__ == "__main__":
    main()

