---
title: "LangChain 安装和快速入门"
date: 2026-05-06T17:02:28+08:00
slug: "langchain-installation-and-quickstart"
image: ""
categories:
    - 技术
tags:
    - LangChain
draft: false
---
## LangChain-Python  扩展库安装

安装 langchain 的 Python 包：

```powershell
pip install -U langchain
# Requires Python 3.10+
```

官方示例用的是 claude 模型和接口，可以切换成其他模型和对应的 api 密钥。

**注意：**

* 目前 claude 注册验证手机号锁国区。
* LangChain 支持的其他聊天模型见：[https://docs.langchain.com/oss/python/integrations/chat](https://docs.langchain.com/oss/python/integrations/chat)

---

## 构建 agent 的关键概念

1. **定义系统提示词**：可以改善 Agent 的行为
   - 系统提示定义了 Agent 的角色和行为，可以使结果更加准确。
2. **创建工具**：集成外部数据
   - 模型可以通过调用自定义的函数与外部系统进行交互。
3. **配置模型**：获得一致的响应
4. **结构化输出**：获得可预测的结果
5. **对话记忆**：用于聊天时交互，记住之前的对话和上下文内容
   - 在生产环境中，使用一个持久化检查点器将消息历史保存到数据库中。
6. **创建和运行 agent**：测试 agent 的功能

---

## 快速构建一个 agent

### 使用 LangChain 和 DeepSeek 模型来获取天气信息

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
from langgraph.checkpoint.memory import InMemorySaver

# 定义系统提示
SYSTEM_PROMPT = """
你是一位经验丰富的天气预报员，说话喜欢用双关语。
你可以使用两个工具：
- get_weather_for_location：用于获取特定地点的天气信息
- get_user_location：用于获取用户的位置信息
如果用户询问天气，请确保你知道他们的位置。如果从问题中可以判断出他们指的是自己所在的任何地方，请使用 get_user_location 工具查找他们的位置。
"""


# 定义上下文和响应格式
@dataclass
class Context:
    """自定义运行时上下文，包含用户 ID 等信息。"""

    user_id: str


# 定义响应格式
@dataclass
class ResponseFormat:
    """定义工具响应的格式，这里我们包含一个双关语回应和天气状况信息。"""

    # 一个有趣的双关语回应，基于天气状况生成的幽默回复
    punny_response: str
    # 可选的天气状况信息，如果工具没有提供天气信息，可以为 None
    weather_conditions: str | None = None


# 定义工具
@tool
def get_weather_for_location(city: str) -> str:
    """获取指定城市的天气信息。"""
    return f"It's always sunny in {city}!"


@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """根据用户 ID 获取用户位置。"""
    user_id = runtime.context.user_id
    location = "中国江苏省南京市" if user_id == "1" else "越南胡志明市"
    print(
        f"--- [本地模型调用了工具] 识别到 UserID: {user_id}，返回位置: {location} ---"
    )
    return location


# 初始化本地 Qwen 模型
model = init_chat_model(
    model="deepseek-chat",
    temperature=0,
)


# 添加记忆功能
checkpointer = InMemorySaver()

# 创建和运行 Agent
agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_user_location, get_weather_for_location],
    context_schema=Context,
    response_format=ToolStrategy(ResponseFormat),
    checkpointer=checkpointer,
)

# `thread_id` 是给定对话的唯一标识符，允许我们在后续调用中继续这个对话。这里我们使用 "1" 作为示例线程 ID。
config = {"configurable": {"thread_id": "1"}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "外面的天气怎么样?"}]},
    config=config,
    context=Context(user_id="1"),
)

print(response.get("structured_response"))


# 注意：在实际应用中，你可能需要根据用户的输入动态调用工具来获取天气信息，而不是直接返回一个固定的字符串。这里我们为了演示工具调用和响应格式，简化了工具的实现。
response = agent.invoke(
    {"messages": [{"role": "user", "content": "thank you!"}]},
    config=config,
    context=Context(user_id="1"),
)

print(response.get("structured_response"))

```

使用了 deepseek-chat 模型，输出符合预期结果：

```powershell
--- [本地模型调用了工具] 识别到 UserID: 1，返回位置: 中国江苏省南京市 ---

ResponseFormat(punny_response='看来南京的天气真是"南"得一见的好！阳光明媚，让人心情都"京"彩起来！', weather_conditions="It's always sunny in 南京!")
Deserializing unregistered type __main__.ResponseFormat from checkpoint. This will be blocked in a future version. Set LANGGRAPH_STRICT_MSGPACK=true to block now, or add to allowed_msgpack_modules to allow explicitly: [('__main__', 'ResponseFormat')]

ResponseFormat(punny_response='不客气！希望我的天气预报能让你"雨"快！记得，无论天气如何，都要保持"阳"光心态！', weather_conditions=None)
```

#### **问题记录**

针对该代码示例，使用本地模型进行测试（ollama 下安装的 qwen:7B 和 14B 模型）。

使用 `init_chat_model` 方法创建模型时可以调用工具函数，但是输出格式内容不符合要求。

使用 `ChatOllama` 方法创建模型时甚至连工具函数都没有调用。（14B 的可以运行无压力，M3 MacBook Pro 18G+1T）

使用 `deepseek-chat` 模型可以输出预期格式结果。

##### **原因解释**

**1. `ChatOllama` 为何不触发工具？（协议与模板不匹配）**

* **底层机制** ：`ChatOllama` 默认调用的是 Ollama 的原生 API。虽然 Ollama 支持工具调用，但它对 **Prompt Template（提示词模板）** 的构造方式与 Qwen 模型预训练时习惯的格式（如 `<|im_start|>tool`）可能存在细微偏差。
* **结果** ：Qwen 无法从 `ChatOllama` 拼接的原始字符串中识别出这是一个“工具定义”，从而将其视作普通的系统指令，导致“选择性失明”。

**2. `init_chat_model` 为何能调工具但格式报错？（能力与复杂度的博弈）**

* **协议加持** ：当你通过 `init_chat_model` 调用本地模型时，通常走的是 Ollama 的  **OpenAI 兼容接口** 。Qwen 对 OpenAI 风格的工具调用有专门的微调，因此能成功触发第一步动作。
* **推理瓶颈** ：你的代码中使用了 `ToolStrategy(ResponseFormat)`，这本质上是 **“ReAct 循环 + 强制工具提取”** 的组合拳。
* 7B/14B 级别的模型逻辑深度有限，在处理多步 ReAct（思考->调工具->观察->再思考）时，其  **Attention（注意力）会被冗长的上下文稀释** 。
* 到了最后输出 `ResponseFormat` 这一步，小模型已无力维持严格的 JSON 约束，容易产生“幻觉”或直接输出自然语言，导致 Pydantic 校验失败。

**3. DeepSeek 为何表现完美？（算力碾压）**

* **模型等级** ：`deepseek-chat` (V3) 是千亿级参数的大模型，其 **指令遵循能力 (Instruction Following)** 和逻辑严密性远超 7B/14B 模型。
* **适配性** ：它在设计上就深度优化了对结构化输出和复杂工具链的支持，能轻松扛住 `ToolStrategy` 带来的逻辑压力。

##### 针对 14B 本地模型的落地建议

1. **放弃 `ToolStrategy`** ：不要强迫小模型在最后一步也输出工具格式。去掉 `response_format`，让它输出纯文本，后端再用正则提取。
2. **简化 Schema** ：尽量减少 Pydantic 类中的嵌套和字段数量。
3. **环境对齐** ：连接 Ollama 时，始终优先使用 `init_chat_model` 配合 `model_provider="openai"`，因为这是目前开源模型兼容性最稳的路径。

#### **使用 api key 的两种常见方式**

**（1）临时注入环境变量：**

```bash
export DEEPSEEK_API_KEY="你的_API_KEY_内容"
```

验证是否注入成功：

```bash
echo $DEEPSEEK_API_KEY
```

**（2）在项目根目录下创建一个 .env 文件，指定 DEEPSEEK_API_KEY 的值**

```bash
DEEPSEEK_API_KEY=sk-xxxxxx
```

### **ollama 的安装和本地模型安装使用**

1. **下载：** 访问 [Ollama 官网](https://ollama.com/download)，选择 macOS 下载。
2. **启动：** 安装后打开 Ollama 菜单栏图标。
3. **下载模型：** 打开终端 (Terminal)，输入：`ollama run qwen2.5:7b`

下载完成后，Ollama 会自动把模型文件加载到你 Mac 的 **统一内存**（Unified Memory）中。
加载成功后，终端提示符会变成： `>>> Send a message (/? for help)`

客户端界面：

![1778059136845](/image/LangChain安装和快速入门/1778059136845.png)

#### 快捷操作小贴士

- **终端交互界面退出对话：** 输入 `/exit` 或按 `Ctrl + D`。
- **查看已下载模型：** `ollama list`
- **查看当前运行的模型**：`ollama ps`
- **删除不用的模型，清理空间：** `ollama rm qwen2.5:7b`
- **彻底关闭后台的模型实例以释放显存/内存**：`ollama stop qwen2.5:7b`（或者在 mac 顶栏找到小羊驼图标，退出）

**注意点：**

- 并不是所有本地模型都能完美支持 `tools` 调用。如果发现它不听话（不调用函数直接乱猜），可能需要换一个专门针对 Tool-Calling 优化过的模型版本。
- 本地模型是**离线**的，但通过 LangChain 的 **Tool Calling（工具调用）** 机制，可以让它通过自定义 **Python 函数** 访问全世界的实时数据。
