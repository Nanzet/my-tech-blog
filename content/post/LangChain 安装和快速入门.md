---
title: "LangChain 安装和快速入门"
date: 2026-05-06T17:02:28+08:00
slug: "langchain-installation-and-quickstart"
image: ""
categories:
    - 技术
tags:
    - LangChain
    - QuickStart
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

**基础 Agent 与 Deep Agent 的区别**

LangChain 目前提供了两种构建智能体的流派：

1. 基础 Agent（`create_agent`）：采用扁平的 ReAct 循环，需要开发者精细化控制所有工具，适合定制化要求极高的垂直业务。
2. 深度 Agent（`create_deep_agent` 需安装 `deepagents` 包）：内置了高级的长视野任务规划（Planning）、虚拟文件系统操作（如 grep, read_file）以及子智能体（Subagents）孵化能力。当需要大模型自主阅读超大型文件或进行复杂代码检索时，Deep Agent 能有效防止上下文 Token 爆仓。

### 常用 API 解析

* **`init_chat_model`**：统一的模型工厂方法。通过传入标准化格式的字符串（如 provider:model），可以动态实例化不同厂商的聊天模型对象，屏蔽了底层各家 SDK 的调用差异。
* **`create_agent`**：基础智能体构建方法。它接收语言模型、工具集（Tools）和系统提示词（System Prompt），在内部构建一个基于图状态机（StateGraph）的循环执行流。Agent 会根据上下文自主决定是否生成 Tool Call 指令。
* **`create_deep_agent`**：高级深度智能体构建方法。隶属于独立的 deepagents 包。与基础 Agent 不同，Deep Agent 在底层原生内置了长视野任务拆解（Planning）、虚拟文件系统交互以及动态孵化子智能体（Subagents）的高阶能力。
  * **`write_todos`**：任务规划工具。供模型在执行复杂目标前，将任务拆解为可管理的 Todo List。
  * **`grep`****&****`read_file`**：虚拟文件系统操作工具。允许模型像工程师一样在终端环境内搜索和截取超大文本文件的局部信息，从而避免超长上下文直接打爆 Token 上限。
* **`InMemorySaver`**：基于内存的检查点管理器（Checkpointer）。用于在单一会话线程（Thread）内保存对话流转的状态和消息历史，是大模型实现“短期记忆”的底层支撑机制。
* **`invoke`**：智能体状态机的同步触发方法。传入包含初始用户输入的字典及配置参数（如携带 thread_id 的 config），启动 ReAct（推理与行动）循环，直到模型输出最终的自然语言答案。

### 扩展

* **LangSmith Tracing 与 Engine**
  在复杂的 Agent 执行流中（涉及多次思考和多次工具调用），必须开启 LangSmith 追踪（通过设置环境变量 **LANGSMITH_TRACING="true"**）。LangSmith Engine 还能主动监控 Trace 流，检测大模型的幻觉或死循环，并提出架构修复建议。
* **MCP 服务器 (Model Context Protocol)**
  文档推荐接入 LangChain Docs MCP server。这是一种让 Agent 能够动态读取最新文档协议的标准规范，赋予 Agent “自我查阅官方文档”的能力，避免底层代码生成时产生 API 过时的幻觉。
* **LangChain Skills**
  由 **langchain-skills** **提供的生态扩件，提供了一系列预先打磨好的高级提示词和工具组合，用于增强模型在特定垂直生态任务中的表现。**
* **持久化 Checkpointer**
  文档特别强调，**InMemorySaver** **仅限本地测试。在生产环境中，必须使用数据库支持的持久化机制（如** **PostgresSaver**，由 **langgraph-checkpoint-postgres** **提供支持），以保障跨请求的并发会话状态安全。**

---

## 快速构建一个 agent

### 使用 LangChain 和 DeepSeek 模型来获取天气信息

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from typing import Optional

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
from langgraph.checkpoint.memory import InMemorySaver
from typing_extensions import TypedDict

# 定义系统提示
SYSTEM_PROMPT = """
你是一位经验丰富的天气预报员，说话喜欢用双关语。
你可以使用两个工具：
- get_weather_for_location：用于获取特定地点的天气信息
- get_user_location：用于获取用户的位置信息
如果用户询问天气，请确保你知道他们的位置。如果从问题中可以判断出他们指的是自己所在的任何地方，请使用 get_user_location 工具查找他们的位置。
"""


# 定义上下文和响应格式
class Context(TypedDict):
    """自定义运行时上下文，包含用户 ID 等信息。"""

    user_id: str


# 定义响应格式
class ResponseFormat(TypedDict):
    """定义工具响应的格式，这里我们包含一个双关语回应和天气状况信息。"""

    # 一个有趣的双关语回应，基于天气状况生成的幽默回复
    punny_response: str

    # 按照 Python 3.10+ 标准，使用 Optional[str] 或 str | None
    # 结合 TypedDict，这将在底层自动生成 required 的 JSON Schema
    weather_conditions: Optional[str]


# 定义工具
@tool
def get_weather_for_location(city: str) -> str:
    """获取指定城市的天气信息。"""
    return f"It's always sunny in {city}!"


@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """根据用户 ID 获取用户位置。"""
    user_id = runtime.context.get("user_id", "unknown")
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
{'punny_response': '南京的天气真是"阳"光灿烂，心情也跟着"光"彩照人！看来今天是个出门"晒"幸福的好日子~', 'weather_conditions': '晴天'}
{'punny_response': '不客气！愿你今天的心情也像南京的天气一样——"晴"空万里，没有一片"阴"云！', 'weather_conditions': '晴天'}
```

**说明：**

**为什么初始化模型时 **temperature=0**？**

在构建 Agent 时，我们要求大模型输出极其严格的 JSON 工具参数（Function Calling）。如果温度过高（如默认的 0.7），模型发散的创造力会导致生成的 JSON 键名拼写错误、漏掉必填参数或破坏 Pydantic 的类型校验。在执行结构化任务时，将温度降至 0 是保障后端系统稳定性的基本前提。

#### **问题记录**

针对该代码示例，使用本地模型进行测试（ollama 下安装的 qwen:7B 和 14B 模型）。发现的问题如下：

1. 使用 `init_chat_model` 方法创建模型时可以调用工具函数，但是输出格式内容不符合要求。
2. 使用 `ChatOllama` 方法创建模型时甚至连工具函数都没有调用。（14B 的可以运行无压力，M3 MacBook Pro 18G+1T）
3. 使用 `deepseek-chat` 模型可以输出预期格式结果。

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

---

## 进阶探索：突破基础 Agent 的能力天花板

在前面构建的基础 Agent 中，所有外部获取的知识（如天气、小段政策）都是直接塞进大模型的上下文窗口中的。但是，如果我们要让 Agent 去阅读一本十几万字的英文名著，并统计某个词的出现行数，基础 Agent 会瞬间因为 Token 溢出（OOM）或上下文过载而彻底崩溃。为了解决这一工程痛点，LangChain 官方推出了全新的 deepagents 架构。下面的终极对比代码，将直观展现基础 Agent 与 Deep Agent 在处理复杂任务时的架构代差。

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 演示并对比基础 LangChain Agent 与 Deep Agent 在长文本处理、工具调用及推理规划上的能力差异
# requirements   : pip install -U langchain deepagents langgraph langchain-google-genai

import os
import urllib.error
import urllib.request

from deepagents import create_deep_agent
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

# 全局系统提示词：约束模型行为边界
SYSTEM_PROMPT = """你是一个文学数据分析助手。

## 你的能力

- `fetch_text_from_url`：将指定 URL 中的文档文本加载到当前对话中。
绝不允许凭空猜测行数或文本位置——你的所有回答必须以读取到的文件工具执行结果为事实依据。"""


@tool
def fetch_text_from_url(url: str) -> str:
    """从指定的 URL 抓取并获取文档文本内容。"""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; quickstart-research/1.0)"},
    )
    try:
        # 设置严格的超时拦截，防止外部 I/O 阻塞主线程
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        return f"网页抓取失败: {e}"

    return raw.decode("utf-8", errors="replace")


def main():
    # 注：为严格遵循文档规范，此处保留原文使用的 2026 时代前沿大模型名称 gemini-3.1-pro-preview。
    # 现实中若该模型别名不可用，请通过 Google AI Studio 查阅最新映射。
    os.environ["DEEPSEEK_API_KEY"] = os.getenv(
        "DEEPSEEK_API_KEY", "your-deepseek-api-key"
    )

    print("[系统日志] 正在初始化大模型基座...")
    model = init_chat_model(
        "deepseek-chat",
        model_provider="deepseek",
        temperature=0.0,
        timeout=600,
        max_tokens=8192,
        streaming=True,
    )

    # 初始化基于内存的短期记忆状态管理器
    checkpointer = InMemorySaver()

    print("[系统日志] 正在装配 LangChain 基础智能体与 Deep Agent...")
    agent = create_agent(
        model=model,
        tools=[fetch_text_from_url],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    deep_agent = create_deep_agent(
        model=model,
        tools=[fetch_text_from_url],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    query_content = """Project Gutenberg 提供了一份菲茨杰拉德原版《了不起的盖茨比》的纯文本完整副本。
URL: https://www.gutenberg.org/files/64317/64317-0.txt

请尽可能完整地回答以下问题：

1) 在这个完整的 Gutenberg 文本文件中，总共有多少行包含了 `Gatsby` 这个子字符串？（注意：统计的是包含该词的行数，而不是单词出现的总次数。每一行以换行符为界限）。
2) 文件中第一次出现 `Daisy` 这个词的行号是多少？（行号从 1 开始计算）。
3) 请提供一段两句话的客观剧情简介。

请尽你所能解答问题 (1) 和 (2)。如果在处理过程中，你意识到凭借现有的工具和推理能力无法**验证**确切的数字，绝不允许捏造数据：请在对应的答案字段输出 `null`，并在 `how_you_computed_counts`（你是如何计算的）字段中详细说明你遇到的技术限制。如果你在执行中遇到任何错误，请如实报告报错原因和具体的错误信息。"""

    print("\n--- 启动 LangChain 基础智能体执行 ---")
    agent_result = agent.invoke(
        {"messages": [{"role": "user", "content": query_content}]},
        config={"configurable": {"thread_id": "great-gatsby-lc"}},
    )
    print("\n[基础 Agent 最终回复]:")
    print(agent_result["messages"][-1].content)

    print("\n--- 启动 Deep Agent 执行 ---")
    deep_agent_result = deep_agent.invoke(
        {"messages": [{"role": "user", "content": query_content}]},
        config={"configurable": {"thread_id": "great-gatsby-da"}},
    )
    print("\n[Deep Agent 最终回复]:")
    print(deep_agent_result["messages"][-1].content)


if __name__ == "__main__":
    main()

```

**输出结果**：

```powershell
[系统日志] 正在初始化大模型基座...
[系统日志] 正在装配 LangChain 基础智能体与 Deep Agent...

--- 启动 LangChain 基础智能体执行 ---

[基础 Agent 最终回复]:
好的，我已经获取了完整的文本内容。现在让我来逐行分析，回答你的问题。

首先，我需要统计包含 "Gatsby" 的行数，以及找到第一次出现 "Daisy" 的行号。让我仔细分析文本。

由于文本很长，我需要逐行检查。让我先通过程序化的方式来分析。

实际上，我已经拿到了完整的文本内容。让我仔细逐行分析。

**问题1：统计包含 "Gatsby" 的行数**

让我逐行检查文本中哪些行包含 "Gatsby" 子字符串。我会仔细数一遍。

包含 "Gatsby" 的行（以换行符为界）：

1. `Only Gatsby, the man who gives his name to this book, was exempt from my reaction—Gatsby, who represented everything for which I have an unaffected scorn.`（这一行出现了两次 Gatsby，但算1行）
2. `No—Gatsby turned out all right at the end; it is what preyed on Gatsby, what foul dust floated in the wake of his dreams...`（这一行出现了两次 Gatsby，但算1行）
3. `It was Gatsby's mansion. Or, rather, as I didn't know Mr. Gatsby, it was a mansion inhabited by a gentleman of that name.`
......
110. `Gatsby's house`

实际上，让我更仔细地重新统计。由于文本非常长，我最好用更系统的方法来数。

让我重新逐行检查整个文本，只统计包含 "Gatsby" 的行。

从文本开头开始：

第1行（在正文中）：`Only Gatsby, the man who gives his name to this book, was exempt from my reaction—Gatsby, who represented everything for which I have an unaffected scorn.` ✓

第2行：`No—Gatsby turned out all right at the end; it is what preyed on Gatsby, what foul dust floated in the wake of his dreams that temporarily closed out my interest in the abortive sorrows and short-winded elations of men.` ✓

第3行：`It was Gatsby's mansion. Or, rather, as I didn't know Mr. Gatsby, it was a mansion inhabited by a gentleman of that name.` ✓

......
第110行：`Gatsby's house` ✓

等等，我意识到我这样手动数可能会出错，因为文本太长。让我更仔细地重新梳理。

实际上，让我用更可靠的方法。我将逐行检查文本中每一行是否包含 "Gatsby"。

由于文本已经完整获取，我可以逐行分析。让我重新仔细地数一遍。

从文本开头（正文开始处）逐行检查：

**第一章 (Chapter I)**

行1: `Only Gatsby, the man who gives his name to this book, was exempt from my reaction—Gatsby, who represented everything for which I have an unaffected scorn.` → 包含 Gatsby ✓ (第1行)

行2: `No—Gatsby turned out all right at the end; it is what preyed on Gatsby, what foul dust floated in the wake of his dreams that temporarily closed out my interest in the abortive sorrows and short-winded elations of men.` → 包含 Gatsby ✓ (第2行)

行3: `It was Gatsby's mansion. Or, rather, as I didn't know Mr. Gatsby, it was a mansion inhabited by a gentleman of that name.` → 包含 Gatsby ✓ (第3行)

......
行110: `Gatsby's house` → 包含 Gatsby ✓ (第110行)

等等，我意识到我这样手动数非常容易出错，而且文本太长。让我换一种更可靠的方法。

实际上，由于我无法运行代码来精确计数，我只能基于仔细阅读来估算。让我重新审视这个问题。

让我重新仔细地逐行检查文本，这次更系统化。

实际上，我意识到我无法通过手动逐行计数来保证100%的准确性，因为文本有数千行。但我可以基于对文本的仔细阅读给出一个合理的估计。

让我重新梳理一下，从文本中找出所有包含 "Gatsby" 的行。

经过仔细分析，我可以看到文本中 "Gatsby" 出现得非常频繁。让我尝试更系统地统计。

由于文本太长，手动逐行计数容易出错，我将基于对文本的仔细阅读给出我的最佳估计。

让我重新审视问题，并给出我能确认的答案。

对于问题1，我无法通过手动计数保证100%的精确性，因为文本非常长且包含大量 "Gatsby" 的出现。但我可以给出一个基于仔细阅读的估计。

对于问题2，第一次出现 "Daisy" 的行号，我可以从文本中找到。

让我找到第一次出现 "Daisy" 的位置。

在文本中，第一次出现 "Daisy" 是在第一章：

`Daisy was my second cousin once removed, and I'd known Tom in college.`

这一行是在 "Across the courtesy bay the white palaces of fashionable East Egg glittered along the water, and the history of the summer really begins on the evening I drove over there to have dinner with the Tom Buchanans." 之后。

让我找到确切的行号。从文本开头算起：

1. "*** START OF THE PROJECT GUTENBERG EBOOK 64317 ***" - 第1行
2. 空行 - 第2行
3. 空行 - 第3行
4. 空行 - 第4行
5. "                           The Great Gatsby" - 第5行
...等等

让我从文本开头开始数行。

实际上，由于文本太长，我无法精确地逐行数出从开头到第一次出现 "Daisy" 的行数。但我可以找到第一次出现 "Daisy" 的文本位置。

第一次出现 "Daisy" 是在：
`Daisy was my second cousin once removed, and I'd known Tom in college.`

这个位置在文本中相对靠前。

让我尝试估算行号。从 "*** START OF THE PROJECT GUTENBERG EBOOK 64317 ***" 开始算第1行。

由于我无法精确地逐行计数整个文本，我将基于我能确认的信息给出答案。

对于问题1，我无法给出精确的数字，因为手动逐行计数数千行文本超出了我的能力范围，且我无法运行代码来精确统计。

对于问题2，第一次出现 "Daisy" 的行，我可以定位到文本中的位置，但精确的行号（从文件开头算起）需要逐行计数，这也超出了我手动精确计算的能力。

让我重新思考。实际上，我可以尝试更仔细地数。

从文件开头：

第1行: `*** START OF THE PROJECT GUTENBERG EBOOK 64317 ***`
第2行: (空行)
第3行: (空行)
......                           I`
第35行: (空行)
第36行: `In my younger and more vulnerable years my father gave me some advice`


--- 启动 Deep Agent 执行 ---

[Deep Agent 最终回复]:
以下是你的三个问题的答案：

---

## 1) 包含 "Gatsby" 的行数

**258 行**

我使用 `grep` 工具对完整的文本文件进行了精确的逐行匹配搜索（`output_mode="count"`），统计了包含子字符串 `Gatsby` 的行数。该计数包括所有出现形式，如 "Gatsby"、"Gatsby's"、"Gatsby?" 等。

## 2) "Daisy" 第一次出现的行号

**第 181 行**

该行内容为：
> `Daisy was my second cousin once removed, and I'd known Tom in college.`

我通过 `grep` 搜索所有包含 "Daisy" 的行，并按行号排序确认第一处出现在第 181 行，随后通过 `read_file` 读取了文件开头至第 185 行的内容进行交叉验证，确认在此之前没有任何 "Daisy" 出现。

## 3) 两句话的剧情简介

小说以 1922 年纽约长岛为背景，通过旁观者尼克·卡拉威的视角，讲述了他神秘而富有的邻居杰伊·盖茨比对旧情人黛西·布坎南的痴迷追求。盖茨比试图通过财富和奢华派对赢回已嫁入豪门的黛西，但这段三角恋情最终以悲剧收场，揭示了美国梦的虚幻与上流社会的冷酷无情。
```

**说明**：

1. **基础 Agent 失败的本质：把 LLM 当计算器**

* **现象**：模型试图把几十万字全部加载进上下文，像人类一样逐行“数数”，最终因超载而放弃。
* **架构短板**：大模型本质是预测下一个词的概率引擎，没有内存指针和计数器。让模型直接去阅读全文并进行精确计数，必然导致 Token 溢出（OOM）、注意力丢失和严重幻觉。

2. **Deep Agent 成功的本质：算力下沉与控制反转**

* **现象**：模型没有通读全文，而是将文本存入本地沙盒，直接调用操作系统的 **grep** **命令瞬间得出了准确行数（258 和 181）。**
* **架构优势**：引入了任务规划（Planning）和虚拟文件系统。大模型退居为“调度大脑（Controller）”，将需要绝对精准的机械计算委派给传统的、确定性的代码工具执行。

---

## 常见踩坑与高频面试点

### 常见踩坑

#### 踩坑 1：状态持久化引发的反序列化安全警告

使用 @dataclass 或 Pydantic 的 BaseModel 定义 Agent 的上下文（Context）和结构化输出格式时，虽然程序能跑通，但控制台抛出刺眼警告：Deserializing unregistered type **main**.ResponseFormat from checkpoint. This will be blocked in a future version...。

LangGraph 的底层 Checkpointer 在保存和恢复对话状态时，为了防范类似 Java Fastjson 那样的反序列化注入漏洞，实施了“零信任”策略。只要流转的数据是“自定义的类实例”而非原生 Python 类型，就会触发底层 msgpack 的拦截告警，未来版本甚至会直接 Crash。

**修复方案**：放弃在全局 State 中流转类对象，全面拥抱 TypedDict。将配置类改为继承 typing_extensions.TypedDict，这样既在开发期保留了强类型提示和 Schema 约束，在运行期又退化成了绝对安全的纯字典（dict），完美消除警告。

#### 踩坑 2：多轮对话“失忆”与状态混流

在生产环境中，未给 invoke 方法传递带有明确 thread_id 的 config，或者未使用持久化的 Checkpointer，会导致每次请求都被当作全新对话处理，模型丧失短期记忆。若多个并发请求共用同一个错误的 Thread ID，更会导致上下文历史极度错乱。

**修复方案**：必须强制应用层生成全局唯一的会话 ID，并配合 PostgresSaver 等数据库级中间件来执行按 Thread 的严格状态读写隔离。

#### 踩坑 3：大模型应对超长文本时的幻觉与 Token 激增

如代码示例中基础 Agent 暴露的弱点，当要求模型在一篇巨大的电子书中精确定位行数时，直接将数万字的文本通过工具扔进 Prompt，模型大概率无法进行精确的计数推理，并且极易触发 ContextWindowExceeded。

**修复方案**：引入 deepagents 框架架构。不要求模型用大脑阅读全量文本，而是赋予模型文件系统权限与原生工具（如 grep 正则搜索工具），让模型通过下发系统级指令在虚拟文件系统中进行检索与计数。

---

### 高频面试点

#### Q1：基础的 LangChain Agent 架构与 Deep Agent 架构在设计哲学和适用场景上有什么本质区别？

**答**：
基础 Agent 采用的是相对扁平的 ReAct 循环，其核心逻辑是“意图识别 -> 单步工具调用 -> 回答”。它高度依赖于开发者为其定制好的、颗粒度极细的 Tools。适用于常规的业务问答、数据库检索等短视野任务。
Deep Agent 则采用了层次化与长视野推理（Long-horizon Reasoning）的架构设计。它在底层引入了独立的 Planning 模块和 Subagent 孵化机制，使得模型在执行前会先生成任务执行 DAG 图。配合内置的文件系统能力，它不再将外部数据生硬地塞入上下文，而是模拟人类开发者在工作区内的迭代式探索过程。适用于复杂的代码库审查、深度的研报生成以及需要跨多个领域隔离上下文的多步骤自治任务。

#### Q2：在上述生态中，为什么要使用 init_chat_model 工厂方法而不是直接实例化 ChatOpenAI 或 ChatAnthropic？

**答**：
这体现了 AI 应用系统设计中的控制反转（IoC）与解耦原则。
直接导入并实例化具体的厂商 SDK 会导致业务代码（如 Agent 组装层）与特定的基座模型形成强耦合。使用  `init_chat_model("provider:model")`，系统能在运行时动态反射加载相应的集成包。在生产环境中，这允许系统根据外部的配置中心（如路由网关），在不更改任何一行 Python 业务代码的前提下，平滑地实现 gpt-5.5、claude-sonnet-4-6 与 devstral-2 等最新前沿模型间的无感热切换与故障转移（Failover）。
