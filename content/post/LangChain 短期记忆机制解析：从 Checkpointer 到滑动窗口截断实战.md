---
title: "LangChain 短期记忆机制解析：从 Checkpointer 到滑动窗口截断实战"
date: 2026-05-28T16:00:14+08:00
slug: "langchain-short-term-memory-checkpointer-trim"
image: ""
categories:
    - 技术
tags:
    - LangChain
    - 短期记忆
draft: false
---

> [Short-term memory - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/short-term-memory)
>

**一句话总结：短期记忆（Short-term memory）是 AI Agent 在单次会话（Thread）内保持多轮交互上下文的核心机制，通过状态检查点（Checkpointer）实现状态持久化，并结合截断、删除和摘要等策略解决大模型上下文窗口受限及注意力分散的问题。**

****

**注意：**

1. <strong><font style="color:#DF2A3F;">在 LangChain 的 create_agent 底层机制中，通过 system_prompt 传入的系统提示词，是不会被持久化存储到 AgentState 的 messages 数组中的！</font></strong>
2. <strong><font style="color:#DF2A3F;">根据 OpenAI 的强契约协议：ToolMessage 的前一条消息，必须是包含 tool_calls 的 AIMessage。 孤立的 ToolMessage 会直接导致网关拒绝服务（HTTP 400）。</font></strong>

---

## 核心概念与常用 API 解析

在 LangChain 和 LangGraph 的架构中，短期记忆并非单纯的数组变量，而是深度集成在图状态（Graph State）中的上下文管理系统。

+ <strong>AgentState</strong>：<u>Agent 的基础状态数据结构</u>。默认提供 messages 键来存储对话历史。支持通过继承该类添加自定义字段（如 user_id、preferences），以在整个会话生命周期中流转结构化数据。
+ <strong>checkpointer</strong>：<u>状态持久化接口</u>。Agent 每次被调用或完成一个步骤（如工具调用）后，都会通过 Checkpointer 将当前状态写入存储介质。测试环境常用 InMemorySaver，生产环境则依赖 PostgresSaver 等数据库级实现。它依靠外部传入的 thread_id 来严格隔离和恢复不同会话的上下文。
+ <strong>InMemorySaver 与 PostgresSaver</strong>：checkpointer 的具体实现类。InMemorySaver 将状态保存在内存中，适用于开发调试；PostgresSaver 将状态持久化到 PostgreSQL 数据库中，适用于生产环境。
+ <strong>ToolRuntime</strong>：工具运行时注入对象。当在工具函数的参数中声明它时，底层会自动注入。工具可通过 `runtime.state` 读取当前的短期记忆，或通过返回 Command 对象直接更新状态。
  + <strong>读状态</strong>：通过 `runtime.state` 获取当前对话的上下文（如用户的 VIP 级别）。
  + <strong>写状态</strong>：通过返回 `Command(update={...})` 来直接修改 Agent 的记忆，供下游其他工具或大模型使用。

---

## 周边与扩展 API 梳理

为了干预上下文和处理大模型的复杂记忆，文档还介绍了以下高级拦截与修改机制：

+ <strong>@before_model</strong>：<u>前置中间件装饰器</u>。在状态传递给大模型之前触发，常用于执行历史消息的动态截断或系统提示词的动态修改。
+ <strong>@after_model</strong>：<u>后置中间件装饰器</u>。在大模型返回生成结果之后触发，常用于输出验证，如扫描生成的最新消息并抹除敏感信息。
+ <strong>@dynamic_prompt</strong>：<u>动态提示词中间件</u>。允许在模型调用前，通过读取 `request.runtime.context` 或当前的状态数据，动态拼接并返回新的系统提示词（System Prompt）。
+ <strong>RemoveMessage 与 REMOVE_ALL_MESSAGES</strong>：<u>状态清除指令</u>。由于 AgentState 中对 messages 字段采用了追加和合并的 Reducer 机制，直接赋予新列表是无效的，必须在更新指令中返回 RemoveMessage 对象来触发底层的物理删除逻辑。
+ <strong>SummarizationMiddleware</strong>：<u>官方内置的消息摘要中间件</u>。自动监控对话的 Token 使用量，并在达到阈值时触发摘要压缩机制。
+ <strong>Command</strong>：<u>状态更新指令类</u>。允许工具在执行完毕后，直接向 Agent 返回 `Command(update={...})` 来突变（Mutate） AgentState 中的记忆字段。

---

## 工程化代码落地示例

以下代码整合了自定义状态扩展、前置截断中间件（Trim）、以及工具动态读写短期记忆（Command）的完整工作流。

```python {title="agent_short_term_memory.py"}
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 带有短期记忆持久化、状态扩展及滑动窗口截断机制的 Agent 示例
# requirements   : pip install -U langchain langchain-deepseek langgraph

from typing import Any

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import before_model
from langchain.chat_models import init_chat_model
from langchain.messages import RemoveMessage, ToolMessage
from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime
from langgraph.types import Command


# 扩展默认的短期记忆状态，增加结构化业务字段
class CustomAgentState(AgentState):
    user_name: str


# 定义中间件：带有“协议边界感知”的滑动窗口截断，在每次调用大模型前执行截断，防止 Token 溢出
@before_model
def trim_messages_middleware(
    state: CustomAgentState, runtime: Runtime
) -> dict[str, Any] | None:
    """保留初始对话和最近的交互，严格保证 Tool Calling 协议链不断裂"""
    messages = state["messages"]
    print(f"[系统日志] 当前消息总数: {len(messages)}，正在执行 Trim 中间件...")

    # 如果消息较少，无需截断
    if len(messages) <= 4:
        return None

    # 保留第一条消息（确立对话基调）
    first_msg = messages[0]

    # 核心算法：逆向收集，寻找安全边界
    recent_messages = []
    # 从最后一条消息开始，往前倒推（跳过第一条 first_msg）
    for msg in reversed(messages[1:]):
        # 每次把消息插入到最前面
        recent_messages.insert(0, msg)

        # 假设我们期望保留最近的 3 条消息
        if len(recent_messages) >= 3:
            # 【边界校验】：切出来的片段开头是 ToolMessage 吗？
            if recent_messages[0].type == "tool":
                # 危险！这是一个孤儿节点，必须继续往前找它的源头 (AIMessage)
                continue

            # 如果开头是 HumanMessage 或 AIMessage，这是安全边界，停止收集！
            break

    # 组装最终安全的 Payload
    new_messages = [first_msg] + recent_messages
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *new_messages]}


# 工具定义：直接写入 Agent 的短期记忆状态
@tool
def update_user_name(name: str, runtime: ToolRuntime[Any, CustomAgentState]) -> Command:
    """当用户提到自己的名字时，调用此工具更新上下文记忆。"""
    print(f"[系统日志] 正在将名字 {name} 写入短期记忆状态...")

    return Command(
        update={
            "user_name": name,
            "messages": [
                ToolMessage(
                    content=f"已成功记录用户姓名为 {name}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


# 工具定义：读取 Agent 的短期记忆状态
@tool
def greet_user(runtime: ToolRuntime[Any, CustomAgentState]) -> str | Command:
    """使用此工具向用户打招呼，会从记忆中读取用户的名字。"""
    user_name = runtime.state.get("user_name")

    if not user_name:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="记忆中没有名字，请调用 update_user_name 工具先记录名字。",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )
    return f"检索记忆成功，用户的名字是：{user_name}！"


def main():
    model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)

    checkpointer = InMemorySaver()

    agent = create_agent(
        model=model,
        tools=[update_user_name, greet_user],
        state_schema=CustomAgentState,
        middleware=[trim_messages_middleware],
        checkpointer=checkpointer,
        system_prompt="你是一个智能助手。请善用工具读写用户的个人信息。",
    )

    config: RunnableConfig = {"configurable": {"thread_id": "session_888"}}

    print("--- 第一轮交互：提供信息触发状态写入 ---")
    response_1 = agent.invoke(
        {"messages": [{"role": "user", "content": "你好，我是工程师张三。"}]}, config
    )
    print(f"AI 回复: {response_1['messages'][-1].content}\n")

    print("--- 第二、三轮交互：模拟填充上下文触发 Trim ---")
    agent.invoke({"messages": [{"role": "user", "content": "今天天气不错。"}]}, config)
    agent.invoke(
        {"messages": [{"role": "user", "content": "中午吃点什么好呢？"}]}, config
    )

    print("--- 第四轮交互：触发工具读取状态记忆 ---")
    response_4 = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "向我打个招呼吧，调用你的 greet_user 工具。",
                }
            ]
        },
        config,
    )
    print(f"AI 回复: {response_4['messages'][-1].content}\n")


if __name__ == "__main__":
    main()

```

**输出结果：**

```powershell
--- 第一轮交互：提供信息触发状态写入 ---
[系统日志] 当前消息总数: 1，正在执行 Trim 中间件...
[系统日志] 正在将名字 张三 写入短期记忆状态...
[系统日志] 当前消息总数: 3，正在执行 Trim 中间件...
[系统日志] 当前消息总数: 5，正在执行 Trim 中间件...
AI 回复: 你好，张三！很高兴认识你！😊

我是你的智能助手，有什么需要帮忙的吗？无论是工作上的问题、技术咨询，还是日常事务，都可以随时找我！

--- 第二、三轮交互：模拟填充上下文触发 Trim ---
[系统日志] 当前消息总数: 7，正在执行 Trim 中间件...
[系统日志] 当前消息总数: 7，正在执行 Trim 中间件...
--- 第四轮交互：触发工具读取状态记忆 ---
[系统日志] 当前消息总数: 6，正在执行 Trim 中间件...
[系统日志] 当前消息总数: 6，正在执行 Trim 中间件...
AI 回复: 你好，张三！很高兴认识你，工程师！😊 有什么我可以帮你的吗？
```

---

## 常见踩坑与高频面试点

在复杂 Agent 系统的开发与面试环节，短期记忆的维护直接关系到系统的稳定性与使用成本。

### 踩坑 1：截断消息（Trim）破坏了大模型协议结构

+ <strong>现象与痛点</strong>：在编写 trim_messages 时单纯按条数（如 messages[-5:]）截断。如果在截断边界处，刚好保留了 ToolMessage 却丢失了对应的 AIMessage（包含 tool_calls 的那条），大模型 API 会直接抛出 HTTP 400 格式验证错误，导致对话链断裂。
+ <strong>核心对策</strong>：截断策略必须具备“Schema 感知”。如果最后 N 条消息的起始处出现了孤立的工具回调结果，必须将其一并移除，或向上回溯保留成对的 Tool Call。同时，必须保留对话流中第一条 SystemMessage。

### 高频考点 1：消息列表的 Reducer 更新机制

+ <strong>面试官提问</strong>：如果在工具中直接通过 state["messages"] = new_messages 来修改历史记录，为什么不生效？
+ <strong>满分回答</strong>：LangGraph 的 AgentState 对 messages 字段默认配置了 add_messages Reducer（聚合器）。这意味着所有直接写入 messages 键的字典操作，在底层都会被转译为 Append（追加） 或 Merge（ID相同的合并）。如果要物理删除上下文消息，必须显式传递 RemoveMessage(id=...) 对象，框架层才会逆向执行移除逻辑。

### 高频考点 2：超长上下文的 4 大应对策略

+ <strong>面试官提问</strong>：“当用户的多轮对话历史越来越长，超出了大模型的 Token 限制，或者导致 API 极度昂贵时，在工程上有哪几种解决方案？”
+ <strong>满分回答</strong>：针对记忆过载问题，通常有 4 种标准对策：
  + <strong>Trim messages (截断消息)</strong>：采用滑动窗口机制，通过 @before_model 中间件动态移除最前面的 N 条消息。实现最简单、开销为零，但会导致 Agent 丧失对早期对话的记忆。
  + <strong>Delete messages (删除消息)</strong>：利用 RemoveMessage 从图状态中永久性地物理删除指定消息。通常配合 @after_model 使用，用于主动清洗包含密码、密钥等敏感词的消息或执行强制清空。
  + <strong>Summarize messages (摘要消息)</strong>：引入 SummarizationMiddleware。当对话 Token 数达到设定阈值时，自动触发一个小模型将早期的多条消息压缩成一段高密度的摘要文本，并用摘要替换原消息列表。这种方案在保留全局长效语义和压缩 Token 之间取得了最佳平衡。
  + <strong>Custom strategies (自定义策略)</strong>：在复杂的业务链路中，结合<strong>自定义的 Middleware</strong>编写极细粒度的裁剪、替换规则（例如<u>针对多模态 Agent 定向剔除历史记录中的 Base64 图片残骸</u>）。

### 高频考点 3：滑动窗口截断（Trim） vs 摘要压缩（Summarize）的取舍

+ <strong>面试官提问</strong>：面对超长对话导致 Context 溢出的问题，Trim 和 Summarize 该如何选型？
+ <strong>满分回答</strong>：
  + <strong>Trim 方案</strong>：延迟极低，成本零开销，适合任务导向型、具有局部上下文依赖的 Agent（如<u>点餐、代码审查</u>），因为此类任务无需追溯太早的聊天记录。
  + <strong>Summarize 方案</strong>：依赖 SummarizationMiddleware 进行后台的小模型推理压缩。它保护了全局长效逻辑不丢失，适合<u>情感陪伴、长流程推理型 Agent</u>。缺点是带来了<u>额外的 Token 消耗与异步推理延迟</u>。在生产环境中，<strong>通常会将两套方案结合：短周期采用 Trim 防爆仓，长周期异步执行归档 Summarize 注入到系统 Prompt 中</strong>。
