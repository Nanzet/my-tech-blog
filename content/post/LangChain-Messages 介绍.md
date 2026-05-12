---
title: "LangChain 消息模块详解：核心概念与实战指南"
date: 2026-05-11T17:35:41+08:00
slug: "langchain-messages-introduction"
image: ""
categories:
    - 技术
tags:
    - LangChain
draft: false
---

## 💡 一句话核心概念

LangChain 的 `Messages` 模块是一个<strong>标准化的多态数据契约（DTO）</strong>，它抹平了各个大模型厂商（如 OpenAI 的 dict、Anthropic 的 block）之间输入输出数据结构的差异，解决了在多轮对话和 Agent 状态机流转中“如何统一管理、拼接和持久化上下文（Context）”的痛点。

---

## 常用核心 API 及类名

在 Agent 开发中，不再直接传纯字符串，而是将所有的交互包装成<u>不同角色的 Message 对象</u>。

### `SystemMessage`

+ <strong>作用</strong>：全局配置与环境初始化。用于设定大模型的“人设”、行为准则、或者是给 Agent 提供全局的背景上下文。相当于系统级的初始 Prompt。

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

### `HumanMessage`

+ <strong>作用</strong>：用户的输入。它可以是简单的文本，也可以是多模态数据（图片、音频、文件的 base64 或 URL），相当于来自 Client 端的 Request Body。

```python
from langchain_core.messages import HumanMessage

# 普通文本输入
user_msg = HumanMessage(content="如何实现高并发限流？")

# 独立运行测试
if __name__ == "__main__":
    print(f"底层 Role 标识: {user_msg.type}") # 输出: human
    print(f"承载的内容: {user_msg.content}")
```

### `AIMessage`

+ <strong>作用</strong>：大模型的输出响应。它不仅仅包含生成的文本（`content`），还携带着极其重要的元数据：<strong>工具调用指令（</strong><strong>`tool_calls`</strong>**）** 和 <strong>Token 计费信息（</strong><strong>`usage_metadata`</strong><strong>）</strong>。

```python
# 假设这是模型的返回对象
# ai_msg.content -> 生成的文本
# ai_msg.tool_calls -> 模型决定调用的函数列表及参数（Agent 核心！）
# ai_msg.usage_metadata -> 消耗的 Token 数量
```

### `ToolMessage`

+ <strong>作用</strong>：外部工具执行结果的载体。当 Agent 调用了你写的后端 Python 函数（如查库）后，你需要<u>把结果包装成 </u><u>`ToolMessage`</u><u> 还给模型，完成回调</u>。**关键参数 **<strong>`tool_call_id`</strong>** 必须与 **<strong>`AIMessage`</strong>** 中的调用 ID 严格匹配。**

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

## 文档中提到的其他 API 和类名

### `AIMessageChunk`

+ <strong>作用</strong>：<u>流式（Streaming）响应的分片对象</u>。在实现后端 Server-Sent Events (SSE) 时，模型会一段段地吐出这个对象。LangChain 巧妙地重载了加法运算符，允许你把它们拼接成完整的 `AIMessage` 落库。

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

### `ContentBlock` (内容块协议)

+ <strong>作用</strong>：LangChain v1 引入的底层标准化结构。因为现在的模型输出太复杂了（比如 DeepSeek-R1 有 `thinking` 过程，GPT-4o 有图片输出），`ContentBlock` <u>把复杂的 </u><u>`content`</u><u> 解析成了强类型的字典列表</u>，如 `ReasoningContentBlock`（推理过程）或 `ImageContentBlock`（图像数据）。
+ <strong>应用场景</strong>：当你需要把模型的“思考过程（Reasoning）”和“最终答案（Text）”分开提取并展示给前端时。

```python
from langchain_core.messages import HumanMessage

if __name__ == "__main__":
    # 多模态 Message：包含文本和图片 URL（基于 ContentBlock 协议构建）
    human_msg = HumanMessage(
        content=[
            {"type": "text", "text": "请提取这张图片里的文字："},
            {"type": "image_url", "image_url": {"url": "https://example.com/sample.png"}}
        ]
    )
    print("多模态 ContentBlocks 结构:")
    for block in human_msg.content:
        print(f"- Block 类型: {block['type']}")
```

---

## 极简代码脚手架

这段代码展示了在后端视角下，四个核心 Message 是如何串联起一个最基础的“大模型工具调用”闭环的。

**langchain_message_flow_test.py：**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : LangChain 消息体系测试脚本 - 展示 SystemMessage、HumanMessage、ToolMessage 的基本用法和交互流程


from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

model = init_chat_model("deepseek-chat", temperature=0)


# 模拟你的后端业务函数并绑定给模型
def get_weather(location: str) -> str:
    return "晴天，25度"


model_with_tools = model.bind_tools([get_weather])

# 构造初始上下文
messages = [
    SystemMessage("你是一个气象助手。"),
    HumanMessage("帮我看看北京天气怎么样？"),
]

# 第一次调用：模型不会直接回答，而是返回一个包含工具调用指令的 AIMessage
ai_msg = model_with_tools.invoke(messages)
messages.append(ai_msg)  # 必须把模型的思考记录加进历史上下文中

# 后端路由：执行具体逻辑，并构造 ToolMessage 响应
for tool_call in ai_msg.tool_calls:
    if tool_call["name"] == "get_weather":
        result = get_weather(**tool_call["args"])
        # 包装成 ToolMessage 喂给模型，ID 必须完全匹配
        messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

# 第二次调用：模型拿着工具给的“事实”，生成最终的自然语言回答
final_response = model.invoke(messages)
print(final_response.content)

```

**输出结果：**

```powershell
北京今天天气晴朗，气温25度，体感比较舒适。适合外出活动，不过建议注意防晒和补水哦！
```

---

## 常见踩坑与高频面试点（高级研发视角）

针对资深后端转型，面试官和实际开发中最容易在以下几个点“翻车”：

### 高频踩坑：`tool_call_id` 匹配错误（HTTP 400 灾难）

+ <strong>痛点</strong>：在 Agent 的循环（ReAct Loop）中，如果你返回的 `ToolMessage` 的 `tool_call_id` 与模型刚才在 `AIMessage` 中下发的 ID 差了一个字符，或者顺序乱了，大模型厂商的 API 会直接抛出 HTTP 400 (Bad Request) 报错。
+ <strong>面试考点</strong>：多工具并发调用（Parallel Tool Calls）时，如何保证异步回调的 ID 映射准确性？这就要求后端在组装历史记录（Message History）时保持严格的字典/映射维护。

### 架构设计考点：流式返回 (`AIMessageChunk`) 的落库难题

+ <strong>面试官可能会问</strong>：“大模型流式输出时，前端确实通过 SSE 实时看到字了。但后端需要把这次完整的对话保存到 MySQL/Redis 以便日后查询，你怎么做？”
+ <strong>工程对策</strong>：绝不能频繁 Update 数据库。正确做法是像上面提到的，在内存中维护一个 `full_message` 变量，利用 `chunk1 + chunk2` 的重载机制在流式循环结束时一次性合并，拿到一个完整的 `AIMessage`，再将其序列化存入数据库。

### 性能踩坑：多模态 Message 导致的负载风暴

+ <strong>痛点</strong>：`HumanMessage` 支持传图片的 Base64 编码。但是，如果这是一次多轮对话，由于大模型是无状态的（Stateless），后端需要每次都把携带了巨大 Base64 字符串的 Message History 全量传给大模型接口，这会导致巨大的网络 I/O 延迟和极其恐怖的 Token 计费。
+ <strong>对策</strong>：如果支持，<u>尽量传递图片的 URL 让模型自己去拉</u>（比如基于文件服务的内网签名 URL）；或者在多轮对话中，利用 Middleware 将历史记录中的图片 Message “裁剪”掉（Message Trimming），只保留模型最初对该图片的文字总结。
