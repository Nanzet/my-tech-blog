---
title: "LangChain 核心消息机制与工程化落地解析"
date: 2026-05-23T15:37:15+08:00
slug: "langchain-messages-engineering-practice"
image: ""
categories:
    - 技术
tags:
    - LangChain
    - 消息机制
draft: false
---

> [Messages - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/messages)
>

**一句话总结：LangChain 中的 Messages（消息机制）是大模型交互的基础数据载体，它通过标准化的对象（Role、Content、Metadata）统一了不同模型厂商的输入输出格式，是构建多轮对话、工具调用与多模态 Agent 应用的核心基石。**

---

## 常用核心概念与基础消息类详解

LangChain 统一定义了四大核心消息类，用来屏蔽底层 OpenAI、Anthropic 等不同模型厂商的 JSON 参数差异。它们均继承自基类 BaseMessage，并在实例中包含核心三要素：Role（角色）、Content（内容）、Metadata（元数据）。

### `SystemMessage`（系统消息）

+ <strong>核心作用</strong>：设定大模型的全局行为准则、人设（Persona）、输出格式和背景上下文。
+ <strong>API 特性</strong>：通常被放置在消息列表的<strong>第 0 号索引</strong>位置。在多轮对话中，为了维持 Agent 的核心设定，这部分内容通常需要被锁定（Pin），不能被滑动窗口轻易清理掉。
+ <strong>典型场景</strong>：`SystemMessage("你是一个 Python 专家，请始终以 JSON 格式返回结果。")`

```python
from langchain_core.messages import SystemMessage

# 设定系统级准则
sys_msg = SystemMessage(content="你是一个高级 Python 架构师，只输出生产级代码。")

# 独立运行测试：观察对象的内部结构
if __name__ == "__main__":
    print(f"Message 类型: {type(sys_msg)}")
    print(f"底层 Role 标识: {sys_msg.type}") # 输出: system
    print(f"承载的内容: {sys_msg.content}")
```

### `HumanMessage`（人类消息）

+ <strong>核心作用</strong>：承载用户的实际输入请求。
+ <strong>API 特性</strong>：
  + 支持纯文本输入（String）。
  + 支持<strong>多模态（Multimodal）输入</strong>。通过传入特定的 content_blocks（内容块），可以包含文本、Base64 编码的图片、PDF 文件或音频数据。
+ <strong>典型场景</strong>：接收前端传来的 User Prompt 或者是上传的文件。

```python
from langchain_core.messages import HumanMessage

# 普通文本输入
user_msg = HumanMessage(content="如何实现高并发限流？")

# 独立运行测试
if __name__ == "__main__":
    print(f"底层 Role 标识: {user_msg.type}") # 输出: human
    print(f"承载的内容: {user_msg.content}")
```

### `AIMessage`（AI 消息）

+ <strong>核心作用</strong>：承载大模型的响应输出。
+ <strong>关键 API 属性（面试/开发极常用）</strong>：
  + <strong>`content`</strong>：模型生成的普通文本内容。
  + <strong>`tool_calls`</strong>：如果大模型决定调用外部工具，这里会包含一个字典列表，指明要调用的 name（工具名）和 args（入参字典）。
  + <strong>`usage_metadata`</strong>：<strong>计费与监控的核心</strong>。包含 input_tokens（输入消耗）和 output_tokens（输出消耗）。
  + `content_blocks`：LangChain V1 引入的新特性，将不同厂商的特殊返回格式（如大模型的“思考/推理过程”）统一解析为强类型的块（如 ReasoningContentBlock）。

```python
# 假设这是模型的返回对象
# ai_msg.content -> 生成的文本
# ai_msg.tool_calls -> 模型决定调用的函数列表及参数（Agent 核心！）
# ai_msg.usage_metadata -> 消耗的 Token 数量
```

### `ToolMessage`（工具消息）

+ <strong>核心作用</strong>：用来向大模型提交本地工具（函数）的执行结果。
+ <strong>关键 API 属性（重点）</strong>：
  + `tool_call_id`：<strong>必须携带</strong>。用来与 AIMessage 中发起的那个 id 一一对应，完成请求-响应的闭环匹配。
  + `content`：必须是字符串格式，包含你想让大模型看到的工具执行结果。
  + `artifact`：<strong>极其重要的高级特性</strong>。专门用来存放“不需要给大模型看，但系统业务流需要用到”的结构化原始数据。

```python
from langchain_core.messages import AIMessage, ToolMessage

if __name__ == "__main__":
    # 1. 模拟大模型返回的 AIMessage（通常在 agent.invoke 后产生）
    ai_msg = AIMessage(
        content="", # 模型决定调用工具时，文本内容通常为空
        tool_calls=[{
            "name": "get_user_balance",
            "args": {"user_id": "9527"},
            "id": "call_abc123" # 全局唯一的调用 ID
        }],
        usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    )
    
    print("--- 1. 解析 AIMessage (大模型下发的 DTO) ---")
    print(f"要求调用的函数: {ai_msg.tool_calls[0]['name']}")
    print(f"提取的参数: {ai_msg.tool_calls[0]['args']}")
    print(f"Token 消耗: {ai_msg.usage_metadata}")

    # 2. 模拟后端执行完查库逻辑后，构造回调的 ToolMessage
    # 真实场景中： db_result = query_db(user_id="9527")
    db_result = "100.00" 
    
    tool_msg = ToolMessage(
        content=f"用户余额为 {db_result} 元", 
        tool_call_id="call_abc123" # 【核心防错点】必须与 ai_msg 中的 id 严格一致
    )
    
    print("\n--- 2. 解析 ToolMessage (后端返回的 DTO) ---")
    print(f"底层 Role 标识: {tool_msg.type}") # 输出: tool
    print(f"响应给模型的内容: {tool_msg.content}")
```

---

## 进阶 API 与标准化 Content Blocks (全量补充)

文档中提到了大量为了解决“跨厂商兼容性”而设计的强类型组件（特别是 V1 版本引入的 content_blocks）。为了不遗漏文档细节，这里做全景梳理：

### 消息块与流式输出 API

+ AIMessageChunk：用于流式输出（Streaming）场景。大模型流式吐出的碎片，可以相互拼接（chunk1 + chunk2）组合成完整的 AIMessage 对象。
+ init_chat_model：统一的聊天模型初始化函数，支持通过 output_version="v1" 参数强制启用标准的 Content Blocks 序列化。

```python
import os
from langchain.chat_models import init_chat_model

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx" # 替换为真实 Key 即可运行
    model = init_chat_model("gpt-4o-mini", model_provider="openai")

    chunks = []
    full_message = None

    print("开始流式接收 (模拟 SSE):")
    # stream() 会返回一个迭代器，每次 yield 出一个 AIMessageChunk
    for chunk in model.stream("请用 10 个字总结 Python 的特点。"):
        chunks.append(chunk)
        print(chunk.content, end="", flush=True) # 实时推给前端
        
        # 【核心操作】重载了 + 号，自动在内存中合并文本和工具参数
        full_message = chunk if full_message is None else full_message + chunk

    print("\n\n--- 接收完毕 ---")
    print("内存中拼接好的完整对象类型:", type(full_message))
    # 可以直接将 full_message 序列化存入 MySQL/Redis 的会话记录表中
    print("完整对象内容:", full_message.content)
```

### Core Blocks (核心内容块)

+ TextContentBlock：标准文本输出。
+ ReasoningContentBlock：用于承载具备深度思考能力的模型（如 DeepSeek-R1, Claude-3.5-Sonnet）的推理过程和步骤。

### Multimodal Blocks (多模态内容块)

+ ImageContentBlock：图像数据（支持 url、base64及 MIME 类型、file_id）。
+ AudioContentBlock：音频数据。
+ VideoContentBlock：视频数据。
+ FileContentBlock：通用文件（如 PDF）。
+ PlainTextContentBlock：纯文本文档（.txt, .md 等）。

### Tool Calling Blocks (工具调用相关块)

+ ToolCall：完整的函数调用结构。
+ ToolCallChunk：流式输出过程中的工具调用片段（含不完整的 JSON args）。
+ InvalidToolCall：用于捕获并包裹格式错误（如 JSON 解析失败）的工具调用。

### Server-Side Tool Blocks (服务端工具执行块)

+ ServerToolCall / ServerToolCallChunk / ServerToolResult：专门用于标识和记录在服务端（而非客户端 Agent 本地）执行的工具调用及结果。

### Provider-Specific Blocks (厂商特有块)

+ NonStandardContentBlock：作为“逃生舱”，用于处理某些厂商独有或处于实验阶段的奇特数据结构。

---

## 工程化代码示例

下面是一份完整的代码，模拟了一次包含 System/Human/AI/Tool 四大消息类的标准交互流程，重点展示了 **Token 监控** 和 <strong>Artifact 数据隔离机制</strong>的工程应用。

```python {title="message_protocol_demo.py"}
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 演示 LangChain 核心消息类交互、Artifact 隐形传参及 Token 监控
# requirements   : pip install -U langchain langchain-openai


from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


def demonstrate_message_protocol() -> None:
    # 初始化大模型 (支持通过 output_version="v1" 启用标准内容块格式)
    # os.environ["DEEPSEEK_API_KEY"] = "sk-your-api-key"
    model = init_chat_model(
        "deepseek-chat", model_provider="deepseek", output_version="v1"
    )

    # ==========================================
    # 1. 构造初始请求上下文 (SystemMessage & HumanMessage)
    # ==========================================
    messages = [
        SystemMessage(content="你是一个智能数据分析师，可以调用工具检索数据库。"),
        HumanMessage(content="请帮我查一下 'Doc1024' 文档里的核心内容是什么？"),
    ]

    # ==========================================
    # 2. 模拟第一轮通信：大模型发起工具调用 (AIMessage)
    # ==========================================
    # (注：真实场景中这是 model.invoke() 生成的，这里为了演示协议流转手动构造)
    ai_call_msg = AIMessage(
        content="",  # 模型此时不输出直接文本，仅发出工具调用指令
        tool_calls=[
            {
                "name": "search_database",
                "args": {"doc_id": "Doc1024"},
                "id": "call_abc123",  # 唯一的 Tool Call 事务 ID
            }
        ],
    )
    messages.append(ai_call_msg)

    # ==========================================
    # 3. 模拟工具执行并返回结果 (ToolMessage)
    # ==========================================
    print("--- [System] 正在执行本地数据库检索 ---")

    # 核心亮点：利用 artifact 实现业务数据与 LLM 消耗数据的隔离
    # db_text_content 是需要花费 Token 让大模型阅读的精简内容
    db_text_content = "该文档主要讲述了 2026 年第一季度的营收增长了 15%。"
    # hidden_metadata 是后端业务需要，但完全没必要给大模型看的数据
    hidden_metadata = {"url": "https://internal.db/doc/1024", "author": "张三"}

    tool_msg = ToolMessage(
        content=db_text_content,
        tool_call_id="call_abc123",  # 必须与 AIMessage 中的 id 严格对应匹配
        name="search_database",
        artifact=hidden_metadata,  # 将业务数据隐形挂载
    )
    messages.append(tool_msg)

    # ==========================================
    # 4. 第二轮通信：模型整合结果生成最终回复
    # ==========================================
    print("--- [System] 携带工具结果，再次请求大模型 ---")
    # 将完整的历史消息列表传入模型
    final_response = model.invoke(messages)

    # 将模型的最新回复真实地追加到上下文数组中
    messages.append(final_response)

    # 获取并打印大模型的最终回答
    print("\n[AI 最终回复]:")
    print(final_response.content)

    # 从上下文中提取隐藏在 artifact 中的业务数据
    print("\n[提取隐藏的 Artifact 数据]:")
    # 提取刚塞入的 ToolMessage 里的隐形数据
    print(f"为前端提取原文链接: {messages[-2].artifact['url']}")

    # 提取并打印计费监控指标 (usage_metadata)
    print("\n[审计与计费 - Token Usage]:")
    usage = final_response.usage_metadata
    if usage:
        print(f"输入消耗: {usage.get('input_tokens')} tokens")
        print(f"输出消耗: {usage.get('output_tokens')} tokens")
        print(f"总计计费: {usage.get('total_tokens')} tokens")


if __name__ == "__main__":
    # 请确保配置了真实的 API KEY 后再运行此代码
    demonstrate_message_protocol()

```

**输出结果：**

```powershell
--- [System] 正在执行本地数据库检索 ---
--- [System] 携带工具结果，再次请求大模型 ---

[AI 最终回复]:
[{'type': 'text', 'text': "根据数据库查询结果，文档 **'Doc1024'** 的核心内容是：\n\n<strong>2026 年第一季度的营收增长了 15%。</strong>"}]

[提取隐藏的 Artifact 数据]:
为前端提取原文链接: https://internal.db/doc/1024

[审计与计费 - Token Usage]:
输入消耗: 108 tokens
输出消耗: 31 tokens
总计计费: 139 tokens
```

---

## 常见踩坑与高频面试点

在 AI Agent 开发的面试和实际生产落地中，关于 Messages 机制的考察，往往集中在“上下文状态管理”、“跨模型兼容”和“数据成本隔离”上。

### 踩坑 1：误以为大模型调用会自动维护状态（invoke 的纯函数陷阱）

+ <strong>踩坑现场</strong>：就像我们刚经历的代码 Bug 一样。新手常以为调用 model.invoke(messages) 后，框架会自动把 AI 的最新回复追加到 messages 数组里，导致后续取数组索引时直接越界报错，或者在下一轮对话时发现 AI “失忆”了。
+ <strong>高频面试点</strong>：_“大模型的上下文究竟是如何管理的？”_
  + <strong>满分回答</strong>：大模型本质是无状态的（Stateless），model.invoke() 是一个纯函数，它只读不写。在简单的业务中，我们需要手动显式执行 messages.append(ai_response) 来维护状态流转；在复杂的 Agent 场景中，则必须引入状态机框架（如 LangGraph 的 MessagesState），由框架接管历史消息的 Reducer（合并与追加）操作。

### 踩坑 2：RAG 检索后的“数据污染”与 Token 爆仓

+ <strong>踩坑现场</strong>：检索工具去向量库查到了 3 篇文档，包含了文档的 Title、Author、DocID 甚至原始的 URL 链接。新手习惯性把这些字段全 json.dumps() 塞进 content 发给大模型，结果不仅瞬间耗尽 Token，大模型还容易产生幻觉（比如把内部 URL 拼写错后发给用户）。
+ <strong>高频面试点</strong>：_“在 Agent 工具调用中，如何实现业务数据与模型提示词的隔离？”_
  + <strong>满分回答</strong>：强烈推荐使用 ToolMessage 的 **artifact** 属性。将模型真正需要阅读的“纯净文本/摘要”放在 content 属性里；将业务系统（前端渲染、权限校验）需要的原始元数据（如 doc_id, url）挂载到 artifact 里。这些数据对大模型完全不可见，但后端可以通过解析 Context 数组随时提取，实现了完美的“前后端数据隔离”。

### 踩坑 3：硬编码解析带来的“跨厂商不兼容”

+ <strong>踩坑现场</strong>：处理深度思考模型（如 DeepSeek-R1, Claude-3.5-Sonnet）的 Reasoning（推理步骤）或多模态图片时，如果直接用 dict 硬解析 OpenAI 和 Anthropic 的原生响应结构，一旦业务要求切换底层模型，相关代码直接全量瘫痪。
+ <strong>高频面试点</strong>：_“如何设计一个兼容多模型厂商的 Agent 底层架构？”_
  + <strong>满分回答</strong>：利用 LangChain 经典的“适配器模式”。通过启用 output_version="v1"，利用 content_blocks 特性。框架会懒加载屏蔽各家 API 的底层 JSON 差异，统一转换为强类型的标准对象（如 ReasoningContentBlock, ImageContentBlock）。我们在业务层只针对这些标准 Block 编程，从而实现对模型厂商的平滑替换。

### 踩坑 4：缺乏监控导致“账单刺客”

+ <strong>踩坑现场</strong>：Agent 上线跑了几天，发现账单几千块，查日志却因为只存了纯文本（String），根本不知道哪一轮对话、哪个工具的调用消耗了异常的 Token。
+ <strong>高频面试点</strong>：_“生产环境下的 Agent 如何做成本审计与监控？”_
  + <strong>满分回答</strong>：绝对不能只提取大模型的文本回复。每次调用结束后，必须通过拦截器或切面提取 AIMessage.usage_metadata。里面包含了精准的 input_tokens、output_tokens 甚至大模型的 reasoning 额外消耗。将这个指标与 thread_id 绑定后异步打点（如落库 Elasticsearch 或 Prometheus），这是保障生产级应用成本可控的底线要求。

### 踩坑 5：tool_call_id 匹配错位（HTTP 400 灾难）

+ <strong>踩坑现场</strong>：在 Agent 的循环中，如果后端返回的 ToolMessage 漏传了 tool_call_id，或者在多工具并发（Parallel Tool Calls）时把 ID 映射搞串了，再次请求大模型时会直接收到 HTTP 400 (Bad Request) 报错，导致对话链路当场崩溃。
+ <strong>高频面试点</strong>：_“在处理大模型的多工具并发调用时，如何保证上下文的连贯性和准确性？”_
  + <strong>满分回答</strong>：必须严格保证请求-响应的闭环协议。大模型的 AIMessage 中下发了多少个 tool_calls，后端就必须对应追加多少个携带精准 tool_call_id 的 ToolMessage。在并发执行工具函数时，后端应当利用字典映射（Map）或并发上下文（如 asyncio.gather）严格锁定每个执行结果与其对应 id 的关联，绝不能依赖数组的返回顺序。

### 踩坑 6：流式返回（Streaming）状态下的落库难题

+ <strong>踩坑现场</strong>：为了前端体验开启了流式输出（SSE）。但后端需要在对话结束后把完整的对话保存到数据库，新手可能会在 for 循环里疯狂执行 DB Update 语句，导致数据库连接池被瞬间打满、数据库负载飙升。
+ <strong>高频面试点</strong>：_“大模型流式输出时，前端在实时打字，后端如何优雅地完成完整对话历史的持久化？”_
  + <strong>满分回答</strong>：绝不能高频写库，必须采用内存聚合策略。正确做法是利用 LangChain 消息块的“重载合并机制”。在内存中维护一个 full_message 变量，在 for chunk in model.stream(...) 循环中，利用 full_message += chunk 将 AIMessageChunk 碎片自动拼接。待流式传输彻底结束（循环跳出）后，拿到一个完整的 AIMessage 对象，再执行单次序列化落库（1 次 DB Insert）。

### 踩坑 7：多模态 Message 历史堆积引发的“负载风暴”

+ <strong>踩坑现场</strong>：HumanMessage 支持传入 Base64 编码的图片。因为大模型是无状态的，如果后端不加干预，在多轮对话中每次都会把包含巨大 Base64 字符串的整个历史数组全量发给 API。这会导致极高的网络 I/O 延迟和极其恐怖的 Token 计费。
+ <strong>高频面试点</strong>：_“在处理多模态 Agent（如图文问答）的多轮对话时，你有什么性能优化的经验？”_
  + <strong>满分回答</strong>：我会从两方面进行架构优化：一是<strong>引用替代</strong>，尽量传递经过鉴权的图片内网 URL（如 OSS 签名链接），让模型端自己去拉取，避免在 JSON 报文中塞入几十兆的 Base64 字符串；二是<strong>历史裁剪与摘要（Message Trimming/Summarization）</strong>，利用中间件，在进入下一轮对话前，将历史记录中的图片 Message 强制剥离，或替换为大模型最初对该图片的一句话文字总结，以维持极简的纯文本上下文。
