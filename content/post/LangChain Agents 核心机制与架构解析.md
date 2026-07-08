---
title: "LangChain Agents 核心机制与架构解析"
date: 2026-05-07T22:02:41+08:00
lastmod: 2026-07-08T22:32:41+08:00
slug: "langchain-agents-architecture-deep-dive"
image: ""
categories:
    -  技术
tags:
    - LangChain
    - Agents
draft: false
---
> [Agents - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/agents)

## 一句话总结

在 `LangChain` 体系中，智能体（`Agent`）是由大语言模型（`Model`）与运行容器（`Harness`）组合而成的可配置执行循环；它在状态机中持续决策并调用工具，结合中间件实现容错、脱敏、上下文压缩与人工审批，是构建具备自主行动、复杂推理和长任务处理能力的 AI 应用核心基石。

---

## 核心概念与常用 API 解析

`Agent` 的核心不再是单次问答，而是一个受控的执行循环。模型读取当前 `State`，决定是否调用工具；运行时执行工具并把结果写回 `messages`；模型继续基于新上下文推理，直到不再请求工具并生成最终回答。

> **补充理解：`State` 是什么？**
> `State` 可以理解为 Agent 在 LangGraph 中流转的“运行状态快照”，至少包含 `messages`。用户输入、模型的工具调用决策、工具返回结果、最终回答都会作为状态更新写回 `State`，从而支撑多步推理、工具调用、流式输出和 checkpoint 恢复。

### `Agent = Model + Harness`

官方文档用 `Agent = Model + Harness` 描述架构边界：

- `Model`：推理核心，负责工具选择、工具结果解释、任务终止判断和最终响应生成。
- `Harness`：围绕模型循环的一整套运行容器，包括 `system_prompt`、`tools`、`middleware`、`checkpointer`、`context_schema`、`store` 等。其中 `checkpointer` 负责保存和恢复会话线程中的 `State`，`context_schema` 定义单次运行时 `context` 的结构，`store` 负责跨会话的长期记忆存储。

这意味着生产级 `Agent` 的质量不只取决于模型本身，还取决于上下文工程、工具 schema（工具入参结构定义）、状态恢复、异常处理、安全护栏和观测能力。

### `create_agent()`：Agent 的统一构建入口

`create_agent()` 是 LangChain 构建 `Agent` 的核心工厂方法。它将 `model`、`tools`、`system_prompt`、`response_format`、`middleware` 等组件组装成一个可执行的图结构，并支持 `invoke()`、`stream_events()`、`checkpoint`、`interrupt` 和多 Agent 嵌套。

其中 `stream_events()` 用于实时观察 Agent 的消息生成、工具调用和状态变化；`interrupt` 用于在高风险动作前暂停 Agent，保存当前 `State`，等待人工审批或外部决策后再恢复执行。

```python
from langchain.agents import create_agent
from langchain.tools import tool

@tool
def search(query: str) -> str:
    """根据查询词搜索信息。"""
    return f"查询结果：{query}"

agent = create_agent(
    model="openai:gpt-5.5",
    tools=[search],
    system_prompt="你是一个简洁、准确的 AI 助手。",
)
```

### `model=`：模型选择与 provider 绑定

`model=` 可以传入 `"provider:model"` 形式的字符串，也可以传入已经初始化好的模型实例。文档中出现的模型名称包括：

- `google_genai:gemini-3.5-flash`
- `openai:gpt-5.5`
- `anthropic:claude-sonnet-4-6`
- `openrouter:z-ai/glm-5.2`
- `fireworks:accounts/fireworks/models/kimi-k2p7-code`
- `baseten:zai-org/GLM-5.2`
- `ollama:north-mini-code-1.0`

模型能力会影响 `tool calling`、`structured output`、上下文窗口、多模态输入、推理稳定性和延迟成本。生产选型时不能只看生成质量，还要验证目标模型**是否稳定支持工具调用、结构化输出和长上下文推理**。

### `tools=` 与 `@tool`：Agent 的行动接口

`tools` 是模型可调用的动作集合，可以是普通 `Python callable`（可调用的 Python 对象）、`LangChain tool` 或 `tool dict`（工具定义字典）。工具的函数名、参数类型和 `docstring` 会被转换成模型可理解的 `schema`（结构定义），因此工具描述会直接影响模型是否能正确选择工具并生成参数。

```python
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息。"""
    return f"{city} 当前天气晴朗。"
```

工程上应让工具名语义明确、参数强类型、docstring 描述清楚输入输出边界。不要把鉴权信息、租户信息等敏感业务上下文暴露为模型可自由生成的工具参数，应通过 `context` 或服务端逻辑注入。

### `system_prompt=`：行为策略与任务边界

`system_prompt=` 用于定义 Agent 的行为基调、回答风格、任务边界和安全规则。它可以传入字符串，也可以传入 `SystemMessage`。如果提示词依赖用户身份、租户权限、功能开关或运行时状态，更适合通过 `middleware` 或 `runtime.context` 动态注入，而不是拼接大量脆弱的字符串。

> `SystemMessage`（系统消息对象）：LangChain 中表示系统级指令的消息对象，用于承载 `Agent` 的行为规则、回答风格、任务边界和安全约束。

### `response_format=`：结构化输出

`response_format=` 用于让 Agent 返回经过 schema 校验的结构化结果。常见写法是传入 `Pydantic BaseModel`：

> `Pydantic BaseModel`：Pydantic 提供的数据模型基类，用于声明结构化数据的字段和类型，并在运行时进行校验。在 `response_format=` 中传入 `BaseModel` 子类，可以让 `Agent` 返回符合该结构定义的 `structured_response`。

```python
from pydantic import BaseModel
from langchain.agents import create_agent

class Answer(BaseModel):
    summary: str
    confidence: float

agent = create_agent(
    model="openai:gpt-5.5",
    tools=[],
    response_format=Answer,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "请总结 AI Agent 的发展趋势。"}]}
)

structured = result["structured_response"]
```

当直接传入 schema 类型时，LangChain 会根据模型能力自动选择策略：

- `ProviderStrategy`（原生结构化输出策略）：使用模型厂商原生结构化输出，通常更稳定。
- `ToolStrategy`（工具调用结构化输出策略）：通过工具调用协议模拟结构化输出，兼容面更广。

最终结构化结果从 `result["structured_response"]` 中读取。上线前必须验证目标模型**是否能同时稳定处理业务工具调用和最终结构化输出**。

### `invoke()`、`thread_id` 与 `checkpointer`

`invoke()` 是一次完整 Agent run 的入口。输入通常是：

```python
{"messages": [{"role": "user", "content": "请总结 AI Agent 工程化能力。"}]}
```

如果需要多轮会话，需要在 `config` 中传入 `thread_id`：

```python
config = {"configurable": {"thread_id": "session-001"}}
```

但 `thread_id` 只是会话作用域标识，真正保存状态的是 `checkpointer`。本地示例可以使用 `InMemorySaver()`，**生产环境应替换为持久化 checkpoint**。

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="openai:gpt-5.5",
    tools=[],
    checkpointer=InMemorySaver(),
)
```

### `context_schema`、`context` 与 `runtime.context`

`context` 用于传递单次运行的业务上下文，例如 `user_id`、租户、权限、功能开关、请求来源等。通过 `context_schema` 定义结构，再在 `invoke()` 时传入。

> `context`（单次运行时上下文）：只在当前这次 `invoke()` / run 中生效，用于传递本次运行的业务数据，不负责保存对话历史，也不等同于长期记忆。

```python
from dataclasses import dataclass

@dataclass
class RequestContext:
    user_id: str
    tenant_id: str

result = agent.invoke(
    {"messages": [{"role": "user", "content": "请查询我的任务。"}]},
    config={"configurable": {"thread_id": "session-001"}},
    context=RequestContext(user_id="user-123", tenant_id="tenant-ai"),
)
```

工具和中间件可以通过 `runtime.context` 读取调用 `invoke()` 时传入的 `context` 数据，例如 `user_id`、`tenant_id`、权限和功能开关。

需要严格区分以下概念：

- `thread_id`：会话线程标识，用于配合 `checkpointer` 恢复短期状态。
- `context`：单次运行时上下文，用于本次 run 的业务依赖注入。
- `store`：跨线程、跨会话的长期记忆存储。

### `stream_events()`：中间过程观测

`invoke()` 只返回最终结果。复杂 Agent 往往会执行多次模型调用和工具调用，因此需要 `stream_events()` 或 `stream()` 暴露中间状态、工具调用和进度更新。生产 UI、调试工具路由、观察长任务执行轨迹时，流式事件比最终结果更重要。

> **`stream()` 和 `stream_events()` 的区别：**
> `stream()` 用于消费 Agent 的状态更新流，适合业务侧展示中间结果；`stream_events()` 用于消费更细粒度的运行事件流，适合调试工具调用、观测执行链路和构建 tracing。

---

## 周边与扩展 API 梳理

`middleware` 是工程化 Agent 的核心扩展点。它不是独立运行时，而是挂载在 `create_agent()` 返回的 Agent 图上，在**模型调用前后**、**工具调用前后**、**状态更新或中断恢复**等关键位置插入确定性逻辑。

### 容错、降级与调用限制

- `ModelRetryMiddleware`：处理模型调用的瞬时失败，例如限流、超时、网络抖动。
- `ToolRetryMiddleware`：处理工具执行失败，避免每个工具都手写重复 `try/except`。
- `ModelCallLimitMiddleware`：限制模型调用次数，防止无限循环和成本失控。
- `ToolCallLimitMiddleware`：限制工具调用次数，可按全局或特定工具维度控制。
- `ModelFallbackMiddleware`：主模型失败时切换备用模型，用于 provider redundancy、成本降级和高可用兜底。

这类中间件的核心价值是把基础设施失败、成本边界和执行上限从 prompt 软约束变成运行时硬约束。

### 安全护栏与人工介入

- `PIIMiddleware`：检测并处理个人身份信息，例如邮箱、电话等。它把隐私保护从提示词提醒升级为确定性拦截。
- `HumanInTheLoopMiddleware`：在高影响工具调用前触发人工审批。典型场景包括写文件、发邮件、数据库更新、支付、外部系统写操作。

`HumanInTheLoopMiddleware` 依赖 checkpoint 保存中断状态。人工决策通常包括 `approve`、`edit`、`reject`、`respond`。它本质上是在工具执行前设置运行时门禁，而不是事后审计。

### 上下文管理与长期记忆

- `SummarizationMiddleware`（摘要压缩中间件）：当上下文接近窗口上限时自动压缩旧消息，同时保留近期消息。
- `MemoryMiddleware`（长期记忆中间件）：加载长期指令或记忆，例如 `sources=["./AGENTS.md"]`。
- `SkillsMiddleware`（技能加载中间件）：按需加载领域技能，避免一次性把所有知识塞入上下文。
- `store` 与 `runtime.store`：`store` 是长期记忆存储，`runtime.store` 是工具或中间件在运行时访问这份长期存储的入口，适合读写用户偏好、组织规则、业务实体和经验信息。

> **版本注意：`SummarizationMiddleware` 的旧参数已不推荐使用。**
> `summary_prefix`、`max_tokens_before_summary`、`messages_to_keep` 属于 deprecated 参数，新代码建议分别改用 `summary_prompt`、`trigger=("tokens", value)`、`keep=("messages", value)`。其中 `trigger` 用于定义“什么时候触发摘要”，`keep` 用于定义“摘要后保留多少近期上下文”。

### 执行环境与长任务工作区

- `FilesystemMiddleware`（文件工作区中间件）：给 Agent 提供可读写工作区，适合保存中间产物、草稿、文件分析结果和跨步骤状态。
- `StateBackend`：为 `deepagents` 中间件提供状态后端。
- `Sandboxes`：用于隔离执行环境，降低代码执行和文件操作风险。
- `Interpreters`：用于代码解释执行，适合数据分析、日志处理、代码研究等任务。

长任务不应把全部材料塞进模型上下文，而应通过文件系统、工具检索、摘要和子 Agent 分层处理。

### 规划与多智能体委派

- `TodoListMiddleware`：为 Agent 提供显式任务列表能力，适合多步骤规划和长任务跟踪。
- `SubAgentMiddleware`：让主 Agent 把子任务委派给上下文隔离的子 Agent。
- `create_deep_agent`：预组装文件系统、摘要、子 Agent、prompt caching 等能力，适合长时间运行的 coding 和 research 任务。
- `name=`：为 Agent 设置标识符，便于嵌入 `multi-agent` 系统或作为子图使用。

`SubAgentMiddleware` 的典型架构是 supervisor 模式：主 Agent 负责路由、规划和汇总，子 Agent 负责专业任务执行。它能减少主上下文污染，并降低工具过多导致的注意力稀释。

> `supervisor` 模式：由一个主 Agent 作为“总控”，负责拆解任务、调度子 Agent 和汇总结果；各子 Agent 拥有独立上下文，专注完成具体子任务。

### 观测、评估与 LangSmith

`LangSmith` 用于 trace Agent 的执行轨迹、调试工具调用、评估输出质量、监控异常和分析 token 成本。对于 Agent 系统，观测对象不是最终文本，而是完整决策链路：模型调用、工具调用、状态更新、中断恢复、重试、成本和延迟。

`LangSmith` 不是简单的日志工具，而是 Agent 的可观测性与评估平台，用于追踪执行链路、分析工具调用、监控成本延迟，并系统性评估输出质量。

---

## 工程化代码落地示例

本节通过两个可独立运行的脚本，展示 `LangChain Agents` 在工程中的典型落地方式：示例 1 聚焦生产级 `Agent` 调用链路，覆盖工具调用、结构化输出、运行时上下文、短期记忆和容错控制；示例 2 聚焦长任务 `Agent Harness`，展示如何通过上下文压缩、技能加载、本地资源管理和子 `Agent` 委派支撑复杂任务执行。

### 示例 1：生产级 `Agent` 调用链路：工具调用、结构化输出与短期记忆

enterprise_agent_pipeline.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author : nanzet
# Description : 演示具备工具调用、结构化输出、短期记忆、上下文注入和容错控制的生产级 Agent
# requirements : pip install -U langchain langchain-google-genai langgraph typing_extensions

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
from langchain.tools import ToolRuntime, tool
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver
from typing_extensions import TypedDict

MODEL_NAME = "google_genai:gemini-3.5-flash"


@dataclass
class RequestContext:
    user_id: str
    tenant_id: str


class AgentAnswer(TypedDict):
    summary: str
    confidence: float
    next_actions: list[str]


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量：{name}。请设置后重新运行脚本。")
    return value


def build_agent() -> Any:

    @tool
    def search(query: str, runtime: ToolRuntime[RequestContext]) -> str:
        """根据查询词检索信息，并返回中文摘要。"""
        return (
            f"用户 {runtime.context.user_id} 在租户 {runtime.context.tenant_id} 中查询：{query}。"
            "模拟检索结果：Agent 的核心是模型根据上下文决定是否调用工具，"
            "工具结果会写回消息状态，模型继续推理直到生成最终答案。"
        )

    return create_agent(
        model=MODEL_NAME,
        tools=[search],
        system_prompt=(
            "你是一个严谨的 AI Agent 架构助手。"
            "请使用中文回答，优先给出工程可落地的结论，避免空泛表达。"
        ),
        response_format=AgentAnswer,
        context_schema=RequestContext,
        checkpointer=InMemorySaver(),
        middleware=[
            ModelRetryMiddleware(max_retries=3),  # 模型调用失败时最多重试 3 次
            ToolRetryMiddleware(max_retries=2),  # 工具调用失败时最多重试 2 次
            ModelCallLimitMiddleware(
                run_limit=8, exit_behavior="end"
            ),  # 当前这次 run 中，最多允许 8 次模型调用。超过后优雅结束，防止模型无限循环。
            ToolCallLimitMiddleware(
                run_limit=5, exit_behavior="continue"
            ),  # 当前这次 run 中，最多允许 5 次工具调用。超过后拦截工具调用，但让模型继续根据已有上下文收尾回答。
        ],
        name="research_assistant",
    )


def main() -> int:
    try:
        require_env("GOOGLE_API_KEY")

        agent = build_agent()
        config = {"configurable": {"thread_id": str(uuid7())}}
        context = RequestContext(user_id="user-123", tenant_id="tenant-ai-agent")

        first_result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "请检索并总结 AI Agent 工程化落地的三个关键能力。",
                    }
                ]
            },
            config=config,
            context=context,
        )

        structured_response = first_result["structured_response"]
        print("结构化摘要：")
        print(json.dumps(structured_response, ensure_ascii=False, indent=2))

        second_result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "继续说明这些能力在高级 AI Agent 面试中应该如何表达。",
                    }
                ]
            },
            config=config,
            context=context,
        )

        second_structured = second_result["structured_response"]
        print("第二轮结构化回答：")
        print(json.dumps(second_structured, ensure_ascii=False, indent=2))
        return 0

    except ImportError as exc:
        print(f"依赖导入失败：{exc}")
        print(
            "请执行：pip install -U langchain langchain-google-genai langgraph typing_extensions"
        )
        return 1
    except Exception as exc:
        print(f"脚本执行失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**输出结果：**

```powershell
结构化摘要：
{
  "summary": "AI Agent 工程化落地的三个关键能力如下：\n\n1. **冷热解耦的结构化记忆管理能力**：解决 LLM 上下文（Context）窗口限制与记忆丢失问题。工程落地需构建**短期记忆**（基于 Redis 的会话滑动窗口与动态摘要）与**长期记忆**（基于向量数据库的 RAG 语义检索与 Key-Value 用户画像存储）的冷热分离架构，并建立记忆的自动写入、剪枝与关联检索机制。\n\n2. **确定性执行与安全工具编排能力**：解决大模型输出“幻觉”与企业级业务高确定性要求的冲突。工程落地需通过**强类型 Schema 校验**（如 JSON Schema 校验参数）、**工具调用的异常容错与重试机制**、**代码解释器的沙箱安全隔离**，并结合**状态机/有状态工作流引擎（如 LangGraph、Temporal）**，在 Agent 推理与确定性执行流之间建立安全边界。\n\n3. **DAG 状态链路可观测性与闭环评估能力**：解决 Agent 内部推理“黑盒”、故障排查困难以及迭代效果无法量化的问题。工程落地需引入**分布式 Trace 链路追踪**（如 OpenTelemetry、LangSmith），将 Planning-Reasoning-Action 拆解为有向无环图（DAG）并可视化；同时建立**回归评估流水线**，使用金标准数据集（Golden Dataset）与 LLM-as-a-judge 机制，实现 Agent 提示词和逻辑迭代的自动化量化评估。",
  "confidence": 0.95,
  "next_actions": [
    "设计并实现基于 Redis + 向量数据库的 Agent 双层记忆存储方案，优化多轮对话上下文消耗。",
    "引入 LangGraph 框架，定义包含人工确认（Human-in-the-loop）的安全工具编排工作流。",
    "在测试环境中部署 LangSmith 或 Phoenix 观测服务，接入 Trace 埋点以实现 Agent 执行链路的全面可视化监控。"
  ]
}
第二轮结构化回答：
{
  "summary": "在高级 AI Agent 面试中，候选人应避免“套用 LangChain 默认模板”的初级描述，转而采用“痛点痛击 -> 架构权衡 -> 指标量化”的高级叙事结构。以下是针对三大关键能力的高分面试表达策略：\n\n1. **记忆管理能力面试表达：从“接入向量库”升级为“高并发冷热解耦的记忆引擎设计”**\n   * **痛点引入**：若将全部历史多轮会话直接塞入 Prompt，不仅会导致 Token 成本呈指数级上升，还会因大模型“Lost in the Middle（中间信息迷失）”导致推理准确率下降。\n   * **高分话术**：在架构设计中，我采用了**冷热解耦的记忆架构**。**短期记忆**基于 Redis 实现，采用“滑动窗口 + 异步 LLM 自动摘要压缩”机制，确保每次携带的上下文不超过 4K Token；**长期记忆**采用基于 Pydantic-Schema 结构化的 KV 存储（存储用户画像与偏好）和基于语义分片（Semantic Chunking）的向量库检索（RAG）。同时，设计了**记忆衰减算法（如结合时间权重的 Ebbinghaus 算法）**，动态计算记忆召回的 Relevance 评分，从而在保障 Agent 长期拟人化认知的同时，将单次 API Token 成本降低了 40%。\n\n2. **工具编排能力面试表达：从“调用 Function Calling”升级为“状态机强约束与防刷防爆控制”**\n   * **痛点引入**：完全自由的 ReAct（Reasoning and Acting）架构极易陷入“工具死循环”或在异常输入下产生不确定性的系统越权，造成账单爆炸和安全合规风险。\n   * **高分话术**：为了在企业级落地中兼顾 Agent 的灵活性与业务的硬确定性，我采用了 **LangGraph / 状态机（State Graph）** 对 Agent 推理路径进行局部强约束。对于高危工具调用（如资金交易、写库操作），在状态机的边（Edge）上配置了 **Human-In-The-Loop（人工介入）中断挂起机制**；在工具层自研了 **Pydantic 动态 Schema 校验拦截器**，对 LLM 吐出的 JSON 进行静态类型强校。针对黑客攻击或模型死循环，设计了**熔断器模式（Circuit Breaker）**，单次 Session 的工具调用次数（Max Iterations）严格限制在 5 次以内，单次会话超时限制在 15s 以内，保障了系统高可用与安全防御。\n\n3. **可观测性能力面试表达：从“看后台 Log”升级为“基于 OpenTelemetry 的 DAG 树状 Tracing 与闭环评估体系”**\n   * **痛点引入**：Agent 的推理过程是多步且非线性的，传统的单点 APM 日志无法还原“LLM 为什么在第三步选错了工具”这一黑盒现场。\n   * **高分话术**：我为生产环境引入了 **OpenTelemetry 规范与 Phoenix/LangSmith 深度集成的 Trace 监控架构**。每一次 Agent 的复杂调度都会生成一个 Trace ID，将 Planning -> Tool Call -> Observation -> Re-planning 的闭环拆解为树状 Spans，能够秒级定位是 Prompt 语义偏移、API 延迟还是 LLM 幻觉导致的任务失败。此外，我们搭建了**自动化回归评估管线（CI/CD Evaluation Pipeline）**，积累了 500+ 条真实业务场景的 Golden Dataset，采用 `Ragas` 框架评估检索召回率与内容忠实度，并配合 **LLM-as-a-Judge** 双模型交叉评分。每一次 Agent 拓扑逻辑或 Prompt 的修改，必须通过自动化 Regression Test 且评分提升后才能灰度发布，使 Agent 的策略调优走向数据驱动。",
  "confidence": 0.98,
  "next_actions": [
    "结合你目前的实际项目，将上述“冷热记忆”、“状态机熔断”、“DAG Trace”话术整理进个人简历的“项目深挖（Deep Dive）”模块中。",
    "模拟面试官可能提出的追问（如：“如何解决向量检索的噪声污染？”“多并发下 Redis 锁如何设计？”），准备对应的技术底座支持方案。"
  ]
}
```

**代码说明：**

* 该脚本演示一个偏生产化的 `Agent` 调用链路，覆盖工具调用、结构化输出、短期记忆、运行时上下文注入和调用限制。
* `RequestContext` 使用 `dataclass` 定义单次运行的业务上下文，包括 `user_id` 和 `tenant_id`，并通过 `context_schema=RequestContext` 注册给 `Agent`。
* `search()` 使用 `@tool` 声明为工具函数，并通过 `runtime.context` 读取 `invoke()` 时传入的 `context` 数据，实现工具侧的运行时上下文访问。
* `AgentAnswer` 使用 `TypedDict` 定义结构化输出 schema，避免自定义 `Pydantic` 类型被 `checkpointer` 序列化时产生未注册类型 warning。
* `create_agent()` 中的 `response_format=AgentAnswer` 用于约束最终结构化结果，输出会写入 `result["structured_response"]`。
* `checkpointer=InMemorySaver()` 启用短期记忆，配合 `thread_id` 保存同一会话线程下的消息状态，使第二轮调用可以接续第一轮上下文。
* `config={"configurable": {"thread_id": str(uuid7())}}` 为当前会话生成唯一线程标识，用于隔离不同会话的短期状态。
* `ModelRetryMiddleware` 和 `ToolRetryMiddleware` 分别处理模型调用与工具调用的失败重试，提升瞬时错误下的稳定性。
* `ModelCallLimitMiddleware` 和 `ToolCallLimitMiddleware` 分别限制单次 `run` 中的模型调用次数和工具调用次数，防止 Agent 无限循环或工具滥用。
* `exit_behavior="end"` 表示模型调用超限后直接结束当前运行；`exit_behavior="continue"` 表示工具调用超限后跳过后续工具执行，让模型基于已有上下文继续收尾回答。
* 脚本连续调用两次 `agent.invoke()`，并复用同一个 `config` 和 `thread_id`，用于演示短期记忆如何让第二轮问题接续第一轮对话状态。

### 示例 2：长任务 `Agent Harness`：上下文压缩、技能加载与子 `Agent` 委派

deep_agent_harness_demo.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author : nanzet
# Description : 演示 Deep Agents 风格的文件系统、摘要、技能、任务列表和子 Agent 委派配置
# requirements : pip install -U langchain langchain-google-genai langchain-deepseek langgraph deepagents


import os
import sys
from pathlib import Path
from typing import Any

from deepagents.backends import StateBackend
from deepagents.middleware import (
    FilesystemMiddleware,
    MemoryMiddleware,
    SkillsMiddleware,
    SummarizationMiddleware,
)
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.tools import tool

MAIN_MODEL_NAME = "google_genai:gemini-3.5-flash"
SUMMARY_MODEL_NAME = MAIN_MODEL_NAME
SUB_AGENT_MODEL_NAME = "deepseek:deepseek-v4-flash"

SCRIPT_DIR = Path(__file__).resolve().parent
AGENTS_FILE = SCRIPT_DIR / "AGENTS.md"
SKILLS_DIR = SCRIPT_DIR / "skills"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量：{name}。请设置后重新运行脚本。")
    return value


def prepare_local_sources() -> None:
    AGENTS_FILE.write_text(
        "请始终使用中文输出，并优先给出工程化结论。\n",
        encoding="utf-8",
    )
    SKILLS_DIR.mkdir(exist_ok=True)
    (SKILLS_DIR / "research.md").write_text(
        "研究任务需要先拆解问题，再检索证据，最后输出结构化结论。\n",
        encoding="utf-8",
    )


def extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                if text:
                    text_parts.append(text)
        if text_parts:
            return "\n".join(text_parts)

    return str(content)


def build_agent() -> Any:

    @tool
    def search(query: str) -> str:
        """根据查询词搜索资料，并返回中文摘要。"""
        return (
            f"查询：{query}。模拟结果：长任务 Agent 通常需要上下文压缩、"
            "文件系统工作区、显式任务列表和子 Agent 隔离上下文。"
        )

    backend = StateBackend()

    return create_agent(
        model=MAIN_MODEL_NAME,
        tools=[search],
        system_prompt=(
            "你是主控 Agent，负责规划任务、委派研究子 Agent，"
            "并用中文输出结构清晰的最终结论。"
        ),
        middleware=[
            FilesystemMiddleware(backend=backend),
            SummarizationMiddleware(
                model=SUMMARY_MODEL_NAME,
                backend=backend,
                trigger=("tokens", 4000),
                keep=("messages", 20),
            ),
            MemoryMiddleware(backend=backend, sources=[str(AGENTS_FILE)]),
            SkillsMiddleware(backend=backend, sources=[str(SKILLS_DIR)]),
            TodoListMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=[
                    {
                        "name": "researcher",
                        "description": "搜索资料并返回结构化中文摘要。",
                        "system_prompt": "请使用搜索工具研究问题，并用中文总结关键点。",
                        "tools": [search],
                        "model": SUB_AGENT_MODEL_NAME,
                        "middleware": [],
                    }
                ],
            ),
        ],
        name="research_supervisor",
    )


def main() -> int:
    try:
        require_env("GOOGLE_API_KEY")
        require_env("DEEPSEEK_API_KEY")
        prepare_local_sources()

        agent = build_agent()

        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "请研究 LangChain Agent 在长任务中的上下文管理和任务委派方案。",
                    }
                ]
            },
            config={"configurable": {"thread_id": "deep-agent-demo-thread"}},
        )

        final_content = result["messages"][-1].content
        print("最终回答：")
        print(extract_text_content(final_content))
        return 0

    except ImportError as exc:
        print(f"依赖导入失败：{exc}")
        print(
            "请执行：pip install -U langchain langchain-google-genai langchain-deepseek langgraph deepagents"
        )
        return 1
    except Exception as exc:
        print(f"脚本执行失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**输出结果：**

````powershell
最终回答：
# LangChain Agent 在长任务中的上下文管理与任务委派方案深度研究报告

在构建生产级 AI Agent 系统的过程中，**长任务（Long-running Tasks）**（例如软件自主开发、多源异构数据分析、多阶段业务审批工作流）是最具挑战性的场景。单一 Agent 在面对此类任务时，通常会遭遇**上下文窗口溢出（Token 膨胀）**、**注意力失焦（Lost in the Middle）**、**工具调用过载（Tool Overload）** 以及 **规划失效（Planning Failure）** 等多重瓶颈。

本报告对基于 LangChain / LangGraph 生态系统的**长任务上下文管理**与**任务委派（多 Agent 协同）**方案进行系统性梳理、对比，并深入剖析二者的**协同效应**，最终提供生产级的最佳实践架构设计模式。

---

## 第一部分：长任务中的上下文管理方案

传统的 Prompt 工程记忆模式在长交互、复杂推理的长任务中捉襟见肘，LangGraph 引入的基于状态持久化的管理机制彻底改变了这一现状。

### 1. 传统 LangChain 记忆机制的演进与局限

| 方案名称 | 实现原理 | 优点 | 缺点（长任务瓶颈） | 典型适用场景 |
| :--- | :--- | :--- | :--- | :--- |
| **滑动窗口**<br>`ConversationBufferWindowMemory` | 仅保留最近 $k$ 轮对话，直接丢弃更早的交互记录。 | 实现极其简单，Token 消耗有硬性上限，低延迟。 | 远期关键信息（如任务初始目标、全局约束、用户设定）会无情丢失。 | 简单客服、短轮次单向 QA。 |
| **摘要记忆**<br>`ConversationSummaryMemory` | 触发 LLM 对历史消息进行再摘要，用摘要文本替代旧历史。 | 能够极大地压缩 Token，理论上可保留全局核心语义。 | **摘要漂移（Summarization Drift）**：反复摘要导致信息失真，且容易滋生 LLM 幻觉；增加了额外的 LLM 调用开销。 | 中等长度（20~100轮）对话。 |
| **语义检索记忆**<br>`VectorStoreRetrieverMemory` | 向量化对话，检索时提取与当前 Query 语义最相似的历史片段。 | 可存储几乎无限的历史。 | **碎片化上下文**：检索结果丧失时间轴连贯性；若 Embedding 匹配不佳，关键决策依据会漏召。 | 知识库型客服、跨 Session 记忆回溯。 |
| **消息裁剪**<br>`trim_messages` | 通过 Tiktoken 或 LLM Tokenizer 按 Token 预算对消息列表进行切片。 | 精准控制 Token 边界，避免窗口溢出（Out-of-Memory）。 | 属于生硬的物理截断，缺乏智能语义筛选。 | 作为系统兜底的安全网（Guardrail）。 |

---

### 2. LangGraph 现代状态管理哲学

LangGraph 改变了“记忆即 Prompt 拼接”的传统认知，将上下文管理升华为**有结构、可持久化、可审计、可回溯的状态机管理**。

```
                   ┌─────────────────────────────┐
                   │        State (类型定义)      │
                   │  - messages: Annotated[...] │
                   │  - global_context: dict     │
                   │  - summary: str             │
                   └──────────────┬──────────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               ▼                  ▼                  ▼
     ┌──────────────────┐┌──────────────────┐┌──────────────────┐
     │  SQLite / Postgre││   Thread ID      ││  Time Travel     │
     │   Checkpointer   ││ (多用户/会话隔离)  ││ (历史版本链/回滚)│
     └──────────────────┘└──────────────────┘└──────────────────┘
```

#### A. 结构化 State 与 Checkpointer (持久化层)

* **状态结构化**：在 LangGraph 中，State 通常通过 TypedDict 或 Pydantic 模型定义。不仅能存原始 Message 数组，还可以存强类型的结构化字段（如 `user_profile: dict`, `task_steps: list`）。
* **增量持久化（Checkpointing）**：Checkpointer（如 `AsyncPostgresSaver` 或 `SqliteSaver`）在**每个节点（Node）执行完毕后，自动保存 State 差异（Diff）的快照**。这保证了即使应用突然中断、重启，Agent 也能从最后一个正确的 Checkpoint 完美恢复。

#### B. 线程（Threads）与多会话管理

* 通过配置 `thread_id` 实现物理隔离。在同一个 `thread_id` 内，LangGraph 自动关联其对应的 Checkpoint 版本链。多用户并发交互时，上下文完全隔离，无需开发者手动管理会话状态存取。

#### C. `add_messages` 增量合并与高级修剪

* **自动去重合并**：使用 `Annotated[list, add_messages]` 定义的消息列表，当传入具有相同 `id` 的消息时，会自动覆盖或删除（如传入一个带有 `id` 且 `content=""` 的消息进行逻辑删除），避免了消息列表的无序膨胀。
* **边界懒压缩策略（Lazy Compression）**：在 Node 内部执行 LLM 调用前，仅在 Token 逼近限制（例如大于 8000 tokens）时，才触发“更新 Summary 字段 + 裁剪 recent messages”的组合策略，这既保证了近期上下文的连贯，又通过 Summary 字段保留了远期关键决策。

#### D. 历史回溯（Time Travel）与人工介入（Human-in-the-loop）

* **Time Travel**：允许开发者或用户获取某一 `thread_id` 的所有 checkpoint 历史，选择特定的 `checkpoint_id` “跳转历史分支”，在当时的状态下注入新的 Prompt 或变量重新执行。这在长任务由于某一步工具调用失败需要“倒带重来”时，提供了系统级容错。
* **Human-in-the-loop (HIL)**：通过 `interrupt_before`（或 `interrupt_after`）显式中断图的执行，将状态冻结，等待人工审批（Approve）、修改（Modify）状态。人工修改后的数据（通过 `update_state`）能够无缝合并回当前状态，极大地降低了长任务在核心决策点的偏离概率。

---

## 第二部分：长任务中的任务委派（Task Delegation）方案

当长任务的复杂性超越了单个 Agent 的推理上限，必须引入**任务委派与多 Agent 协作**。

### 1. 为什么长任务需要任务委派？

1. **突破“工具过载（Tool Overload）”**：LLM 能够完美遵循的工具指令数量通常在 5 个以内。超过 10 个工具时，Agent 频繁出现误用、漏用工具。委派可以将工具按职责分散给不同 Worker。
2. **避免“级联错误累积”**：长任务中，第一步的微小偏差会导致后续规划全盘崩溃。通过委派，每个子任务执行完毕后都会回到主控（Orchestrator）处进行校验，及时斩断错误链路。
3. **状态隔离与注意力聚焦**：子 Agent 运行时拥有纯净的、仅与子任务相关的上下文空间，不受全局复杂历史的干扰。

---

### 2. 多 Agent 任务委派三大核心设计模式

#### Pattern 1: 树状/分层级协作模式（Hierarchical Agent Teams / Supervisor-Worker）

* **结构**：一个高能力的 **Supervisor Agent（主控）** 充当项目经理，拥有任务拆解、动态路由、结果校验的能力。下挂多个 **Worker Agents（执行员）**，各自配备专用工具。
* **通信与状态流转**：
    1. Supervisor 接收全局 Task，将其拆解为 Sub-tasks。
    2. Supervisor 产生决策，利用条件边（Conditional Edges）将 Payload 分发至对应的 Worker。
    3. Worker 运行在其局部 State 空间中，执行完毕后向 Supervisor 提交结果（Response）。
    4. Supervisor 进行 QA 校验，如果合格，则更新全局 State，继续分发下一步；若不合格，则要求原 Worker 重试或重规划。
* **优缺点**：
  * *优点*：流程高度可控、可审计，单点纠错能力强。
  * *缺点*：对 Supervisor 的推理能力要求极高，存在单点瓶颈；相比对等协作延迟稍高。

#### Pattern 2: 网络/对等协作模式（Network / Collaborative Pattern）

* **结构**：去中心化。Agent A 执行完自己的动作后，直接决定将任务交棒给 Agent B 或 Agent C。
* **通信与状态流转**：
  * 通过共享的消息图（MessageGraph）或共享 State。每个 Agent 根据当前 State 内的最近一条消息（或特定状态标记），自主决定自己是否应当“抢占”任务并处理，处理完后再追加消息，触发下一个 Agent 的激活。
* **优缺点**：
  * *优点*：高度动态、灵活性强，适合发散型、探索型任务（如多人脑暴、跨角色代码重构）。
  * *缺点*：容易产生“死锁”或“死循环”，状态流转难以追踪，不适合严肃商业流。

#### Pattern 3: 编排式（Orchestration） vs 编舞式（Choreography）

* **编排式（Orchestration）**：由一个明确的“中枢逻辑（可以是 Supervisor LLM，也可以是固定的 Python 状态机图逻辑）”显式规划所有的 Step。
* **编舞式（Choreography）**：没有集中式中枢，每个 Agent 订阅事件流，自主做出响应。

> *在长任务最佳实践中*：通常在**顶层使用编排式**（确保大方向不偏偏、满足业务合规与 SLA），在**底层子任务执行时采用编舞式**或微型对等网络以提升局部吞吐量。

---

### 3. LangGraph 中子图（Subgraphs）作为独立委派单元的设计

在 LangGraph 中，**子图（Subgraph）** 是任务委派的最佳技术载体。

```python
# 1. 定义子任务执行团队（Worker Subgraph）的独立 State
class ResearchTeamState(TypedDict):
    query: str
    raw_docs: List[str]
    synthesized_report: str

research_graph = StateGraph(ResearchTeamState)
research_graph.add_node("retrieve", retrieve_node)
research_graph.add_node("synthesize", synthesize_node)
research_graph.set_entry_point("retrieve")
research_graph.set_finish_point("synthesize")
compiled_research_team = research_graph.compile()

# 2. 在主控（Supervisor）图中将其作为一个普通 Node 嵌入
class MainState(TypedDict):
    main_task: str
    sub_task_payload: dict  # 传递给子图的 Payload
    final_result: str

main_builder = StateGraph(MainState)
main_builder.add_node("supervisor", supervisor_node)
main_builder.add_node("research_node", compiled_research_team)  # 嵌入子图
```

**子图通信协议与状态同步机制：**

* **单向注入与抽取（State Mapping）**：当主图跳转到子图节点时，主图的 `sub_task_payload` 会被提取并映射到子图的 `query`。
* **状态隔离**：子图在运行 `retrieve` 和 `synthesize` 时的所有消息和中间变量，仅保留在子图的独立 Checkpoint 中，主图对其完全“无感”，从而彻底避免了主图的上下文遭受海量原始网页数据的污染。
* **结果合并（Reduction）**：当子图执行到 Finish Point 时，它只将最终的 `synthesized_report` 传回主图节点，主图将其 merge 到全局 State 中。

---

## 第三部分：上下文管理与任务委派的协同效应

上下文管理与任务委派并不是割裂的两个技术点，在长任务中，它们呈现出强烈的**相辅相成（Synergistic）**关系：

```
┌─────────────────────────────────────────────────────────────┐
│                       任务委派 (Task)                        │
│ ┌────────────────────────┐       ┌────────────────────────┐ │
│ │    主控 (Supervisor)    ├──────►│     子图 (Subgraph)    │ │
│ └───────────▲────────────┘       └───────────┬────────────┘ │
└─────────────┼────────────────────────────────┼──────────────┘
              │ 过滤、裁剪、变量映射            │ 仅返回高置信度结果
┌─────────────┴────────────────────────────────▼──────────────┐
│                    上下文管理 (Context)                     │
│ ┌────────────────────────┐       ┌────────────────────────┐ │
│ │  全局轻量 State / LTM   │       │   局部临时 State / STM │ │
│ └────────────────────────┘       └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

1. **任务委派是最好的“上下文物理隔离墙”**：
    传统的 Context Management 费尽心思想用各种算法压缩 Prompt。而 **Task Delegation 机制直接从物理上将全局长任务划分为一个个“微型状态图（Subgraphs）”**。每个子图拥有专属、短暂生命周期的短期记忆（STM），执行完毕后随手丢弃，只将“干燥度极高、信息密度极高”的结论汇入全局长期记忆（LTM）。这从根源上消除了 `Lost in the Middle` 效应。
2. **上下文管理为主控决策提供“精准沙盒”**：
    主控（Supervisor）在做复杂的任务拆解和下一步分配时，最忌讳垃圾信息干扰。通过 LangGraph 的 `Message Trimming` 和状态过滤，主控节点在调用时永远只暴露**任务定义、当前阶段进度、人工干预输入、以及上一个 Worker 的精炼 Response**。高置信度、低噪的上下文，使主控的规划（Planning）成功率呈指数级提升。
3. **Checkpointer 守护分布式委派的全局一致性**：
    当一个复杂的 Supervisor-Worker 体系中有多层嵌套子图时，一旦最深层的 Worker 发生 API 报错、网络断开或逻辑异常，Checkpointer 能够提供**全链路分布式事务般的状态恢复**。我们可以精确回退到导致异常的那个子 checkpoint，重新委派，避免了整个分布式 Agent Team 从头跑一次带来的巨大 Token 消耗和时间开销。

---

## 第四部分：长任务 Agent 最佳实践架构设计模式

结合上述研究，以下推荐三种可在生产环境中直接落地的 Agent 架构模式：

### Pattern A: 边界裁剪编排模式（Border-Trimming Orchestrator）

* **核心思路**：主控全局控盘。在每个 Worker Node 的**入口边（Entry Edge）** 和 **出口边（Exit Edge）** 强制加入 Context Filter。
* **实现要点**：
  * 在进入 Worker A 之前，通过 Python 逻辑自动剥离全局 State 中除 `A_task_instruction`、`A_necessary_schema` 以外的所有无用字段。
  * Worker A 结束后，在返回主图前，调用 `trim_messages(strategy="last", max_tokens=1000)`，仅保留最近一轮交互，并将核心指标（如 `extracted_data: dict`）存入全局结构化变量，绝不让 Worker 内部的“嘴碎”吐回给全局。

### Pattern B: 带有人工审核的层级子图容错模式（Checkpointed Hierarchical HIL）

* **核心思路**：适合高合规、高精度的长任务。将任务委派给多个 Subgraph，但在 Subgraph 之间和关键执行节点加入 `interrupt_before`。
* **设计示例**：
    1. **Orchestrator** 分解任务得到 `Plan_v1`。
    2. 触发 `interrupt_before["execute_plan"]` 暂停，系统通知人工校验 `Plan_v1`。
    3. 人工在前端界面若发现不合理，通过 `graph.update_state(config, {"plan": "修正后的Plan_v1"})` 动态注入。
    4. 调用 `graph.invoke(None, config)` 唤醒 Agent，进入各 Worker 节点执行。
    5. 若 Worker 执行失败，系统通过 Time Travel 回滚到步骤 2 的 Checkpoint，人工再次纠偏重新运行。

### Pattern C: 双轨记忆共享网络模式（Dual-Track Memory Shared Network）

* **核心思路**：既保留全局上下文的“大局观（长期记忆 LTM）”，又保障子任务执行的高频响应（短期记忆 STM）。
* **实现机制**：
  * **Track 1（全局长期记忆轨）**：在顶层 State 中维护一个只读的 `GlobalContext`（包含：用户长效偏好、系统核心目标、关键参数约束），该字段在整个长任务运行期间**只读不写**，在每次委派给 Worker 时强制作为 System Prompt 注入。
  * **Track 2（局部短期工作轨）**：Worker 在执行复杂的多步交互、代码尝试时，产生海量的中间消息，全部存留在 `MessagesState` 中。当 Worker 退出时，通过一个特定的 `summarize_node` 将消息压缩成 200 字以内的 `progress_update`，追加至主图，同时 `MessagesState` 被整体归档/截断清空。

---

## 总结

在长任务场景下，LangChain / LangGraph 提供了目前业界最完备的理论框架和技术实现：

* **上下文管理**不再局限于单纯的 Prompt 拼接或全量向量检索，而是基于 **Checkpointer 机制**，通过**结构化状态、多线程隔离、懒摘要压缩、Time Travel、HIL人工介入**，构建了兼顾弹性、可追溯性和低 token 消耗的鲁棒上下文层。
* **任务委派**通过 **Supervisor-Worker 分层架构** 和 **独立子图（Subgraphs）** 实现了职责专业化、状态高度隔离。
* **两者的完美结合**，通过**物理划分上下文域（State Isolation）**与**边界数据精准映射**，极大地稀释了复杂长任务的熵增速度，是将 Agent 从“玩具原型”推向“生产级系统”的必由之路。

````

**代码说明：**

* 该脚本演示一个 `Deep Agents` 风格的长任务 `Agent Harness`，重点展示文件系统工作区、上下文压缩、技能加载、任务列表和子 `Agent` 委派。
* `MAIN_MODEL_NAME="google_genai:gemini-3.5-flash"` 作为主控 `Agent` 模型，负责规划、路由和最终汇总；`SUB_AGENT_MODEL_NAME="deepseek:deepseek-v4-flash"` 作为研究子 `Agent` 模型，负责具体资料研究任务。
* `SCRIPT_DIR`、`AGENTS_FILE` 和 `SKILLS_DIR` 用于固定本地资源生成路径，确保 `AGENTS.md` 和 `skills/` 始终创建在脚本同级目录，而不是当前终端运行目录。
* `prepare_local_sources()` 会生成本地长期指令文件 `AGENTS.md` 和技能说明目录 `skills/`，供 `MemoryMiddleware` 和 `SkillsMiddleware` 加载。
* `FilesystemMiddleware` 提供文件系统工作区能力，让长任务可以围绕文件进行读写和中间结果管理。
* `SummarizationMiddleware` 通过 `trigger=("tokens", 4000)` 和 `keep=("messages", 20)` 在上下文过长时自动摘要旧消息，降低上下文窗口压力。
* `MemoryMiddleware` 从 `AGENTS.md` 加载长期指令，`SkillsMiddleware` 从 `skills/` 加载任务技能说明，用于增强 `Agent` 的长期行为约束和领域能力。
* `TodoListMiddleware` 为复杂任务提供显式任务列表管理，帮助 `Agent` 拆解、跟踪和推进长任务。
* `SubAgentMiddleware` 注册名为 `researcher` 的子 `Agent`，由主控 `Agent` 负责委派研究任务，子 `Agent` 使用独立模型和工具完成专业子任务。
* `extract_text_content()` 用于从模型返回的 `content parts` 中提取纯文本，避免直接打印 `type`、`text`、`extras.signature` 等底层响应结构。
* `thread_id="deep-agent-demo-thread"` 用于标识当前会话线程，方便 `Agent` 在同一线程中维持任务状态。

---

## 常见踩坑与高频面试点

### 常见踩坑

#### 踩坑 1：只传 `thread_id`，但没有配置 `checkpointer`

- 原因：`thread_id` 只是会话作用域标识，不负责保存状态。
- 修复方式：本地调试使用 `checkpointer=InMemorySaver()`，生产环境使用持久化 checkpointer（例如 `PostgresSaver`、`AsyncPostgresSaver`、`SqliteSaver`、`MongoDBSaver` 或 Redis 类后端。其中 `PostgresSaver` / `AsyncPostgresSaver` 更适合多实例生产部署，因为它能在进程重启、任务中断、人工审批和长任务恢复场景中可靠保存并恢复图状态）；涉及多轮对话、HITL 中断恢复和长任务续跑时必须配置。

#### 踩坑 2：混淆 `context`、`thread_id` 与 `store`

- 原因：`context` 是单次运行时依赖，`thread_id` 是短期会话线程，`store` 是长期记忆。
- 修复方式：把 `user_id`、租户、权限放入 `context`；把会话连续性放入 `thread_id` 与 `checkpointer`；把跨会话偏好、组织规则和业务实体放入 `store`。

#### 踩坑 3：工具 schema 设计过于随意

- 原因：模型依赖工具名、参数类型和 docstring 进行工具选择与参数生成。
- 修复方式：使用 `@tool`，保持参数强类型，docstring 明确工具能力、输入含义和输出边界，避免让模型生成鉴权类参数。

#### 踩坑 4：用 `system_prompt` 替代确定性安全策略

- 原因：prompt 是**软约束**，无法稳定处理隐私、审批、调用次数和高风险动作。
- 修复方式：使用 `PIIMiddleware`、`HumanInTheLoopMiddleware`、`ModelCallLimitMiddleware`、`ToolCallLimitMiddleware` 等中间件实现**硬边界**。

#### 踩坑 5：长任务不做上下文管理

- 原因：Agent 循环会不断累积 `messages`、工具结果和中间步骤，最终导致上下文溢出或注意力污染。
- 修复方式：使用 `SummarizationMiddleware`、`FilesystemMiddleware`、`MemoryMiddleware`、`SkillsMiddleware` 和子 Agent 隔离上下文。

#### 踩坑 6：结构化输出与工具调用没有联合验证

- 原因：`response_format` 可能走 `ProviderStrategy` 或 `ToolStrategy`，不同模型对结构化输出和工具调用并用的支持程度不同。
- 修复方式：上线前针对目标模型压测 `structured_response` 成功率、schema 兼容性和工具调用冲突情况。

#### 踩坑 7：缺少流式观测和 LangSmith trace

- 原因：只看最终回答无法定位工具选择错误、循环过长、token 成本异常、上下文污染和重试风暴。
- 修复方式：开发阶段使用 `stream_events()` 观察执行过程，生产阶段接入 `LangSmith` 做 tracing（调用链追踪）、eval（效果评估） 和 monitoring（线上监控）。

---

### 高频面试点

#### Q1：LangChain Agent 的核心执行模型是什么？

**答：** 核心是 `model` -> `tool_calls` -> `tool_results` -> `model` 的状态循环。模型读取当前 `State` 中的 `messages` 和上下文，决定是否调用工具；运行时执行工具并把结果写回状态；模型继续推理，直到不再请求工具并输出最终答案。相比普通 `LLM.invoke()`，Agent 多了行动能力、状态演进和多步决策；相比固定工作流，Agent 的步骤数量和工具选择由模型动态决定。

#### Q2：为什么官方说 Agent = Model + Harness？

**答：** `Model` 是推理引擎，负责工具选择、工具结果解释和任务终止判断；`Harness` 是运行容器，包含 `tools`、`system_prompt`、`middleware`、`checkpointer`、`context_schema`、`store` 和流式机制。单纯模型调用只能生成文本，而 `Harness` 让模型具备可控执行、状态恢复、安全拦截和工程扩展能力。

#### Q3：create_agent() 的架构定位是什么？

**答：** `create_agent()` 是构建 Agent harness 的统一入口，它把 `model=`、`tools=`、`system_prompt=`、`response_format=`、`middleware=`、`checkpointer=`、`context_schema=` 等组装成可执行图。底层依赖 LangGraph 的状态图能力，因此支持 `invoke()`、`stream_events()`、`checkpoint`、`interrupt` 和子图组合。相比手写循环，它提供标准化、可组合、可观测的 Agent 运行框架。

#### Q4：thread_id、context、store 如何区分？

**答：** 三者分别解决会话连续性、运行时依赖注入和长期知识沉淀。

* `thread_id` 是会话线程的唯一标识符，配合 `checkpointer` 保存、关联和恢复该线程下的短期消息历史与图状态；
* `context` 是单次运行时输入，通过 `runtime.context` 给工具和中间件读取；
* `store` 不绑定某一次会话线程，而是保存可长期复用的信息，例如用户偏好、业务规则和组织知识；在同一应用内，只要多条会话线程或多个 `Agent` 运行共享同一个 `store` 后端，就可以通过 `runtime.store` 读取这些长期记忆。

#### Q5：ProviderStrategy 和 ToolStrategy 的区别是什么？

**答：** `ProviderStrategy` 使用模型厂商原生结构化输出能力，约束更强、解析更稳定；`ToolStrategy` 通过工具调用协议让模型输出符合 schema 的参数，兼容更多模型但依赖 `tool calling` 质量。直接传 `response_format=Schema` 时，LangChain 会根据模型能力自动选择。工程上必须验证目标模型是否能同时稳定处理业务工具和最终结构化响应。

#### Q6：为什么生产 Agent 必须重视 middleware？

**答：** 很多生产控制不能交给模型自觉完成。`middleware` 可以在模型调用、工具调用、状态更新等生命周期中插入确定性逻辑，例如重试、`fallback`、调用限制、`PII` 处理、人工审批和上下文压缩。相比 `prompt`，`middleware` 更可测试、更可组合、更可审计。

> 这里的 `fallback` 指降级或备用路径切换，例如主模型失败时切换到备用模型，主工具不可用时切换到备用工具，或结构化输出失败时切换到更保守的解析策略。

#### Q7：什么时候应该引入 SubAgentMiddleware？

**答：** 当**任务跨领域**、**工具集合很大**、**上下文容易污染**、需要**并行研究或隔离风险**时，应引入 `SubAgentMiddleware`。主 `Agent` 作为 `supervisor` 负责任务拆解、路由和汇总；子 Agent 使用独立 `system_prompt`、`tools`、`model` 和上下文完成专门任务。它*比单 Agent 更能降低注意力稀释*，*比固定流程更保留动态任务拆解能力*。

#### Q8：HumanInTheLoopMiddleware 的底层机制是什么？

**答：** `HumanInTheLoopMiddleware` 在*模型生成工具调用之后、工具执行之前*检查 `interrupt_on` 策略；命中后触发 `LangGraph interrupt`，并依赖 `checkpoint` 保存当前图状态。人工返回 `approve`、`edit`、`reject` 或 `respond` 后，Agent 从中断点恢复。它*是执行前控制，而不是事后审计*。

> 官方 `HumanInTheLoopMiddleware` 文档里，`interrupt_on` 的值主要有三种写法：
>
> ```python
> HumanInTheLoopMiddleware(
>     interrupt_on={
>         "write_file": True,
>         "execute_sql": {"allowed_decisions": ["approve", "reject"]},
>         "read_data": False,
>     }
> )
> ```
>
> 含义是：
>
> * 当模型准备调用 `write_file` 时，触发人工审批。
> * 当模型准备调用 `execute_sql` 时，触发人工审批，但人工只能 `approve` 或 `reject`。
> * 当模型准备调用 `read_data` 时，不触发人工审批，直接执行。
>
> `interrupt_on` 用于配置哪些工具调用需要人工审批，以及允许人工做哪些决策。它可以对某个工具设置 `True`、`False`，或设置 `allowed_decisions` 与 `when` 条件函数。人工决策中，`approve` 表示按原参数执行，`edit` 表示修改参数后执行，`reject` 表示拒绝执行并把反馈交还给模型，`respond` 表示人工直接作为工具结果返回，通常用于 `ask_user` 这类交互式工具。

#### Q9：如何防止 Agent 无限循环和成本失控？

**答：** 需要多层控制：核心原则是把开放式推理循环约束在次数、时间、成本和权限边界内。

* **`Model` 层**：设置 `timeout` 和 `max_retries`；
* **`Agent` 层**：使用 `ModelCallLimitMiddleware` 和 `ToolCallLimitMiddleware`；
* **`Tool` 层**：保证幂等、限流和超时。
  * 幂等：用于防止同一工具调用被重复执行后产生重复副作用；
  * 限流：用于限制工具调用频率和次数，避免 Agent 循环调用导致成本、额度或外部系统压力失控；
  * 超时：用于防止单次工具调用长时间阻塞整个 Agent 执行循环。
* **观测层**：使用 `LangSmith` 追踪调用链、`token`、延迟和错误。

#### Q10：如何判断一个 Agent 是否生产可用？

**答：** 不能只看最终回答质量，而要**评估完整决策轨迹**，包括**工具调用准确率**、**结构化输出成功率**、**平均模型调用次数**、**工具失败恢复**、**上下文压缩质量**、**HITL 命中率**、**PII 拦截率**、**延迟**、**token 成本**和**回归测试表现**。Agent 是“推理 + 执行”的闭环系统，因此评估对象必须覆盖执行轨迹和外部副作用。
