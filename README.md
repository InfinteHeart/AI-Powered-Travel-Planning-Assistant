# 🌍 智能旅行规划助手

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-v1-green.svg)](https://python.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

基于 LangChain v1 和 LangGraph 构建的智能旅行规划系统  
集成多源 API 和 MCP 协议，实现全流程旅行规划和个性化推荐

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [架构设计](#-架构设计) • [使用示例](#-使用示例) • [开发文档](#-开发文档)

</div>

---

## ✨ 功能特性

### 🚄 交通查询
- **火车票查询**：集成 12306 MCP 服务，支持高铁、动车票查询
- **车次信息**：查询车次经停站、发车时间、票价信息
- **跨语言调用**：通过 STDIO 协议与 Node.js MCP 服务通信

### 🗺️ 地理信息
- **天气查询**：实时获取目的地天气信息
- **地点搜索**：支持地理编码、POI 搜索
- **周边推荐**：查找附近的美食、景点、酒店等

### 🚗 路线规划
- **多种出行方式**：支持公交/地铁、步行、驾车三种方式
- **智能规划**：根据用户偏好自动选择最优路线
- **详细导航**：提供分步导航指引

### 🏨 酒店推荐
- **智能搜索**：集成 AIGoHotel MCP 服务（通过 ModelScope）
- **星级筛选**：支持按星级、价格、位置筛选
- **个性化推荐**：根据预算和偏好自动匹配

### 🔍 评价搜索
- **真实口碑**：集成 Tavily 搜索 API，获取景点、餐厅的真实评价
- **网络搜索**：实时获取最新的旅游资讯和攻略

### 🎯 个性化推荐
- **用户画像**：维护 8 个维度的旅行偏好
  - 兴趣偏好（历史文化、自然风光、美食体验等）
  - 出行方式（步行、公交、自驾、混合）
  - 旅行节奏（悠闲、适中、紧凑）
  - 预算水平（经济、舒适、豪华）
  - 住宿偏好、餐饮偏好、特殊需求、天气敏感度
- **智能工作流**：基于 LangGraph 构建 5 节点推荐流程
  - 地点搜索 → 评价查询 → 酒店推荐 → 路线规划 → 结果生成
- **动态适配**：根据偏好自动调整搜索参数

### 💬 对话管理
- **多轮对话**：基于 LangGraph Checkpointer 实现会话状态持久化
- **上下文摘要**：自动压缩长对话（触发阈值 4000 tokens）
- **动态提示词**：根据对话内容自动切换系统提示词

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+ (用于 12306 MCP 服务)
- pip 或 conda

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/InfinteHeart/AI-Powered-Travel-Planning-Assistant.git
cd AI-Powered-Travel-Planning-Assistant
```

2. **安装 Python 依赖**

```bash
pip install langchain langgraph langchain-openai python-dotenv requests tavily-python
```

3. **配置环境变量**

创建 `.env` 文件并配置以下 API Keys：

```env
# DeepSeek API (或其他兼容 OpenAI 的 LLM)
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 高德地图 API
GAODE_API_KEY=your_gaode_api_key

# Tavily 搜索 API (可选)
TAVILY_API_KEY=your_tavily_api_key

# AIGoHotel URL
AIGOHOTEL_MCP_URL=your_aigohotel-mcp_url
```

4. **安装 12306 MCP 服务**

```bash
cd mcp/12306-mcp-main
npm install
npm run build
cd ../..
```

5. **运行助手**

```bash
# 方式 1: 使用完整版 Agent (推荐)
python -m agent.cli

# 方式 2: 使用简化版 Agent
python mcp-agent.py
```

---

## 🏗️ 架构设计

### 系统架构

```
用户输入 → Agent (LangChain)
         ↓
    中间件层 (Middleware)
    - SummarizationMiddleware (对话摘要)
    - DynamicPrompt (动态提示词)
         ↓
    工具层 (Tools)
    - 12306 MCP Client (STDIO 通信)
    - 高德 API Client (HTTP REST)
    - AIGoHotel MCP Client (ModelScope)
    - Tavily Search API
         ↓
    工作流层 (Workflow)
    - LangGraph StateGraph
    - 5节点推荐流程
         ↓
    状态管理层 (State Management)
    - TravelContext (运行时上下文)
    - UserPreferenceState (用户偏好状态)
    - SessionManager (会话管理)
         ↓
    持久化层 (Persistence)
    - InMemorySaver (LangGraph Checkpointer)
```

### 目录结构

```
project/
├── agent/                      # Agent 核心逻辑
│   ├── agent.py                # 主 Agent 类
│   ├── cli.py                  # 命令行交互界面
│   ├── middleware.py           # 中间件实现
│   ├── session_manager.py      # 会话管理
│   ├── preference_manager.py   # 偏好管理
│   ├── context_types.py        # TravelContext 定义
│   └── user_preference_state.py # UserPreferenceState 定义
├── client/                     # API 客户端
│   ├── mcp_12306_stdio_client.py  # 12306 MCP 客户端
│   ├── gaode_client.py            # 高德地图客户端
│   ├── aigohotel_client.py        # AIGoHotel MCP 客户端
│   └── route_planning_client.py   # 路线规划客户端
├── tools/                      # LangChain 工具
│   ├── traffic_tools.py        # 交通查询工具
│   ├── gaode_tools.py          # 高德地图工具
│   ├── hotel_tools.py          # 酒店搜索工具
│   ├── web_search_tools.py     # 网络搜索工具
│   └── preference_tools.py     # 偏好管理工具
├── workflow/                   # LangGraph 工作流
│   └── recommendation_workflow.py  # 推荐工作流
├── prompts/                    # 提示词模板
│   └── travel_system_prompts.py    # 系统提示词
├── mcp/                        # MCP 服务
│   └── 12306-mcp-main/         # 12306 MCP 服务
└── README.md                   # 本文件
```

### 核心技术

- **LangChain v1**: Agent 框架、工具调用、中间件机制（摘要、动态提示词）
- **LangGraph**: StateGraph 状态机编排、Checkpointer 会话管理
- **MCP 协议**: STDIO 和 JSON-RPC 2.0 通信
- **DeepSeek Chat**: 大语言模型 (temperature=0.1)
- **类型安全**: TypedDict、Optional、Literal 类型注解

---

## 📖 使用示例

### 基础查询

```
用户: 帮我查一下明天从北京到上海的高铁票
助手: [调用 12306 MCP] 为您查询到以下车次...

用户: 上海明天天气怎么样？
助手: [调用高德 API] 上海明天多云，气温 15-22°C...

用户: 推荐一些外滩附近的美食
助手: [调用高德 POI 搜索] 为您找到以下餐厅...
```

### 个性化推荐

```
用户: 我想设置一下旅行偏好
助手: 好的，请告诉我您的偏好...

用户: 我喜欢历史文化和美食，喜欢步行，节奏悠闲一点，预算舒适就好
助手: [更新用户偏好] 已记录您的偏好！

用户: 帮我规划一下上海两日游
助手: [启动推荐工作流]
      - 搜索历史文化景点和美食地点
      - 查询景点评价和口碑
      - 推荐 3-4 星舒适型酒店
      - 规划步行路线
      - 生成悠闲节奏的行程安排
```

### 酒店搜索

```
用户: 帮我找一下外滩附近的酒店，3-4星的
助手: [调用 AIGoHotel MCP] 为您找到以下酒店：
      1. 上海外滩XX酒店 (4星) - ¥580/晚
         位置：距离外滩 500m
         评分：4.5/5.0
      2. ...
```

### 路线规划

```
用户: 从外滩到东方明珠怎么走？
助手: [调用高德路线规划]
      推荐方案：步行
      距离：约 2.1 公里
      时间：约 25 分钟
      路线：沿中山东一路向南...
```

---

## 🔧 开发文档

### API Keys 获取

1. **DeepSeek API**: [https://platform.deepseek.com/](https://platform.deepseek.com/)
2. **高德地图 API**: [https://lbs.amap.com/](https://lbs.amap.com/)
3. **Tavily Search API**: [https://tavily.com/](https://tavily.com/)
4. **AIGoHotel MCP Server API**：[https://mcp.agentichotel.cn/apply](https://mcp.agentichotel.cn/apply)

### 扩展开发

#### 添加新工具

1. 在 `client/` 目录创建客户端文件
2. 在 `tools/` 目录创建工具文件，使用 `@tool` 装饰器
3. 在 `agent/agent.py` 中注册工具

```python
from langchain.tools import tool

@tool
def your_new_tool(param: str) -> str:
    """工具描述"""
    # 调用客户端
    result = your_client_function(param)
    return result
```

#### 自定义工作流

在 `workflow/` 目录创建新的工作流文件：

```python
from langgraph.graph import StateGraph

workflow = StateGraph(YourState)
workflow.add_node("node1", node1_function)
workflow.add_node("node2", node2_function)
workflow.add_edge("node1", "node2")
workflow.set_entry_point("node1")
workflow.set_finish_point("node2")
```

#### 自定义中间件

在 `agent/middleware.py` 中添加新的中间件：

```python
from langchain.agents.middleware import Middleware

class YourMiddleware(Middleware):
    def process_input(self, input_data):
        # 处理输入
        return modified_input
    
    def process_output(self, output_data):
        # 处理输出
        return modified_output
```

---

## 📊 技术亮点

1. **多协议集成**: 同时支持 HTTP REST、MCP STDIO、MCP HTTP 三种通信协议
2. **状态机编排**: 使用 LangGraph 实现复杂业务流程的可视化编排
3. **智能上下文管理**: 自动摘要 + 动态提示词，优化长对话性能
4. **双层状态管理**: TravelContext（运行时上下文）+ UserPreferenceState（用户偏好）分离设计
5. **类型安全**: 全面使用 TypedDict、Optional、Literal 等类型注解
6. **模块化设计**: 清晰的分层架构，易于扩展和维护
7. **偏好驱动推荐**: 基于用户画像自动调整搜索参数

---

## 📝 项目成果

- ✅ 实现 **13 个工具函数**，覆盖交通、地理、酒店、搜索等领域
- ✅ 构建 **5 节点工作流**，实现端到端的旅行规划自动化
- ✅ 支持 **8 维度用户画像**，提供个性化推荐
- ✅ 对话摘要机制将上下文长度控制在 **4000 tokens** 以内
- ✅ 集成 **3 个外部 API** 和 **2 个 MCP 服务**

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request


## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 [Issue](https://github.com/InfinteHeart/AI-Powered-Travel-Planning-Assistant/issues)
- 发送邮件至: 19861629721@163.com

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！⭐**

</div>****
