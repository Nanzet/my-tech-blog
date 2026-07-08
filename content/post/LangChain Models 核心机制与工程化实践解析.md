---
title: "LangChain Models 核心机制与工程化实践解析"
date: 2026-05-08T22:11:17+08:00
lastmod: 2026-07-08T15:31:00+08:00
slug: "langchain-models-engineering-guide"
image: ""
categories:
    - 技术
tags:
    - LangChain
    - Models
draft: false
---
> [Models - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/models)

## 一句话总结

在 `LangChain` 框架中，`Models` 是 `Agent` 的推理决策引擎，它通过统一的 `ChatModel` 接口屏蔽多 provider API 差异，并提供流式输出、工具调用、结构化输出、多模态处理、动态模型路由与可观测性能力，是构建复杂交互和自治化工作流的核心基础。

## 核心概念与常用 API 解析

### `model`：Agent 的推理引擎

`model` 不只是文本生成器，而是 `Agent` 循环中的决策核心：它读取 `messages`，判断是否需要调用工具，解释工具结果，并决定何时输出最终回答。在 `Agent = Model + Harness` 结构中，`model` 负责推理与决策，`Harness` 负责工具、中间件、上下文、状态和运行控制。

`Models` 模块既可以独立调用，也可以传入 `create_agent()`：

```python
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

model = init_chat_model("google_genai:gemini-3.5-flash", timeout=60, max_retries=6)
agent = create_agent(model=model, tools=[])
```

### `init_chat_model()`：统一模型初始化入口

`init_chat_model()` 是官方推荐的模型工厂方法，支持通过 `provider:model` 字符串或独立 `model` 名称初始化聊天模型。LangChain 的 provider integration package 会把模型名直接传给 provider API，因此新模型名通常不需要等待 LangChain 主包更新。

支持的模型名称包括：`gpt-5.5`、`openai:gpt-5.5`、`claude-sonnet-4-6`、`azure_openai:gpt-5.5`、`google_genai:gemini-2.5-flash-lite`、`us.anthropic.claude-sonnet-4-6`、`microsoft/Phi-3-mini-4k-instruct`、`auto`、`google_genai:gemini-3.5-flash`、`gpt-5.4-mini`、`gpt-5-nano`、`claude-haiku-4-5-20251001`等。

常见 provider 与模型类包括：

- `OpenAI`：`ChatOpenAI`
- `Anthropic`：`ChatAnthropic`
- `Azure OpenAI`：`AzureChatOpenAI`
- `Google Gemini`：`ChatGoogleGenerativeAI`
- `AWS Bedrock`：`ChatBedrock`
- `HuggingFace`：`HuggingFaceEndpoint`、`ChatHuggingFace`
- `OpenRouter`：`ChatOpenRouter`
- `Ollama`：本地模型入口之一

### 常用模型参数

- `model` 用于指定模型名称或模型标识符，也可以写成 `provider:model`，例如 `google_genai:gemini-3.5-flash`。
- `api_key` 用于 provider 鉴权，生产环境应通过环境变量或密钥管理服务注入，例如 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`GOOGLE_API_KEY`、`AZURE_OPENAI_API_KEY`、`OPENROUTER_API_KEY`、`HUGGINGFACEHUB_API_TOKEN`。
- `temperature` 控制输出随机性，低值更稳定，高值更发散。
- `max_tokens` 控制最大输出 token 数。
- `timeout` 控制模型请求超时时间。
- `max_retries` 控制失败重试次数，默认值是 `6`。文档说明网络错误、`429` 和 `5xx` 会自动重试，`401`、`404` 等客户端错误不会重试。长任务 `Agent` 可将 `max_retries` 提高到 `10` 到 `15`，并配合持久化 `checkpointer` 保存进度。

### `invoke()`、`stream()`、`batch()`：三种核心调用方式

- `invoke()` 是单次完整调用，返回完整 `AIMessage`：

```python
response = model.invoke("请用一句话解释 LangChain 的模型抽象。")
print(response.text)
```

- `stream()` 返回多个 `AIMessageChunk`，适合实时 UI、长文本生成、工具调用片段和推理块展示：

```python
for chunk in model.stream("请解释模型流式输出的价值。"):
    print(chunk.text, end="", flush=True)
```

- `batch()` 是 LangChain 客户端并发调用多个独立输入，不等同于 `OpenAI` 或 `Anthropic` 的 provider 原生 batch API：
  - `batch_as_completed()` 会在每个输入完成时立即返回结果，结果可能乱序，需要用返回的输入索引重建顺序。

```python
responses = model.batch(
    ["解释工具调用。", "解释结构化输出。"],
    config={"max_concurrency": 2},
)
```

> * `invoke()`：**同步调用**，输入一次请求，返回一次完整结果。
> * `ainvoke()`：**异步调用**，以异步方式返回完整结果。
> * `stream()`：**同步流式调用**，逐块返回模型输出。
> * `astream()`：**异步流式调用**。
> * `astream_events()`：**异步事件流调用**，返回运行过程中的事件。

### 标准消息协议

`Message` 是模型上下文的基本单位，包含 `role`、`content` 和元数据。常见类型包括：

- `SystemMessage`：系统消息对象，用于定义模型角色、行为边界和安全约束。
- `HumanMessage`：用户消息对象。
- `AIMessage`：模型输出消息对象，可能包含 `text`、`content`、`content_blocks`、`tool_calls`、`usage_metadata`、`response_metadata`。
- `AIMessageChunk`：流式模型输出消息片段，可累加为完整 `AIMessage`。
- `ToolMessage`：工具结果消息，带有 `tool_call_id`，用于和模型生成的工具调用请求对齐。
- `ToolCallChunk`：流式工具调用片段，工具参数可能被拆成多段返回。

### `bind_tools()`：模型级工具调用

`bind_tools()` 将工具 schema 暴露给模型。模型返回的是工具调用请求，不会自动执行工具；独立使用模型时，开发者需要执行工具并把 `ToolMessage` 追加回 `messages`。使用 `create_agent()` 时，Agent loop 会自动处理工具执行循环。

```python
from langchain.tools import tool

@tool
def get_weather(location: str) -> str:
    """查询指定城市的天气。"""
    return f"{location} 天气晴朗。"

model_with_tools = model.bind_tools([get_weather])
response = model_with_tools.invoke("查询北京天气。")
print(response.tool_calls)
```

`bind_tools()` 的常用控制参数包括：

- `tool_choice="any"`：强制调用任意一个工具。
- `tool_choice="tool_1"`：强制调用指定工具。
- `parallel_tool_calls=False`：禁用并行工具调用。

### `with_structured_output()`：结构化输出

`with_structured_output()` 用于让模型输出符合 schema 的结构化结果，支持 `Pydantic BaseModel`、`TypedDict` 和 `JSON Schema`。

```python
from pydantic import BaseModel, Field

class Movie(BaseModel):
    title: str = Field(description="电影标题")
    year: int = Field(description="上映年份")
    director: str = Field(description="导演")
    rating: float = Field(description="十分制评分")

model_with_structure = model.with_structured_output(
    Movie,
    method="json_schema",
    include_raw=True,
)

response = model_with_structure.invoke("请给出电影《盗梦空间》的基本信息。")
print(response["parsed"])
print(response["raw"])
print(response["parsing_error"])
```

> 注意：上述代码加了 `include_raw=True` 后，`response` 不再直接是 `Movie` 对象，而是一个字典。

`with_structured_output()` 的 `method` 参数常见取值包括：

- `method="json_schema"`：使用 provider 原生结构化输出能力。
- `method="function_calling"`：通过工具调用模拟结构化输出。
- `method="json_mode"`：要求输出合法 JSON，但 schema 约束主要依赖 prompt。

`include_raw=True` 是 `with_structured_output()` 的调试参数，开启后会同时返回原始 `AIMessage`、解析后的 `parsed` 结果和 `parsing_error`，适合排查结构化输出解析失败或查看 token 用量等原始响应元数据。

## 周边与扩展 API 梳理

### `ModelProfile` 与 `model.profile`

`model.profile` 是 `langchain>=1.1` 引入的**模型能力档案**，可能包含 `max_input_tokens`、`image_inputs`、`reasoning_output`、`tool_calling`、`structured_output` 等字段。它让系统可以动态判断模型能力，而不是在业务代码中硬编码模型能力表。

典型用途包括：

- `SummarizationMiddleware` 根据 `max_input_tokens` 判断何时触发摘要压缩。
- `create_agent()` 根据 `structured_output` 自动推断 `ProviderStrategy` 或 `ToolStrategy`。
- `image_inputs` 可用于多模态能力门控：在传入图片前先判断模型是否支持图片输入，避免把图片内容发送给只支持文本的模型。
- `Deep Agents Code` 根据 `tool_calling`、文本 I/O 和上下文窗口筛选可用模型。

`model.profile` 目前是 beta 特性。若数据缺失或过旧，可以通过自定义 `profile` 覆盖，也可以通过 `models.dev`、`profile_augmentations.toml` 和 `langchain-model-profiles` 更新上游数据。

### `ProviderStrategy` 与 `ToolStrategy`

`ProviderStrategy` 可理解为“原生结构化输出策略”，依赖 provider 自身的 structured output 能力，通常更可靠。

`ToolStrategy` 可理解为“工具调用结构化输出策略”，通过 tool calling 将结构化结果包装成一次工具调用返回。

在 `create_agent(response_format=Schema)` 中，LangChain 可根据 `model.profile` 自动推断策略。若模型能力数据缺失或 provider 行为特殊，可以手动指定。

### `content_blocks`：多模态、推理与工具调用的统一载体

`content_blocks` 是 LangChain 统一不同 provider 输出形态的关键抽象，可能包含：

- `{"type": "text"}`：普通文本。
- `{"type": "reasoning"}`：推理过程。
- `{"type": "image"}`：图片输出。
- `{"type": "tool_call"}`：工具调用。
- `{"type": "server_tool_call"}`：服务端工具调用。
- `{"type": "server_tool_result"}`：服务端工具结果。

多模态模型可以通过 `content_blocks` 接收或返回图片、音频、视频等非文本内容。推理型模型也可在 `content_blocks` 中返回 `reasoning` 块，便于前端把“推理过程”和“最终正文”分开渲染。

### Prompt caching

Prompt caching 用于降低重复长上下文的延迟与成本，主要有三层：

- provider 隐式缓存：例如 `OpenAI`、`Gemini` 自动命中缓存。
- provider 显式控制：例如 `ChatOpenAI` 的 `prompt_cache_key`、`Anthropic` 的 `cache_control`、`AWS Bedrock` 的 `cachePoint`。
- LangChain middleware：例如 `AnthropicPromptCachingMiddleware`、`BedrockPromptCachingMiddleware`，用于缓存稳定系统提示词和工具内容。

缓存命中通常会反映在 `usage_metadata` 中，但很多 provider 只有在输入 token 超过最低阈值时才启用缓存。

### Server-side tool use

Server-side tool use 指 provider 在服务端执行工具，例如 `web_search` 或 code interpreter。它和普通 `@tool` 的区别是：普通工具由你的应用执行，并通过 `ToolMessage` 返回结果；server-side tool 由 provider 执行，结果以 `server_tool_call` 和 `server_tool_result` 出现在 `content_blocks` 中。

```python
tool = {"type": "web_search"}
model_with_tools = model.bind_tools([tool])
```

### `InMemoryRateLimiter` 与 `rate_limiter`

`rate_limiter` 用于限制模型调用速率。`InMemoryRateLimiter` 是进程内线程安全限流器，可通过 `requests_per_second`、`check_every_n_seconds`、`max_bucket_size` 控制请求节奏和突发容量。

它只能限制单位时间请求数量，不能限制请求大小、token 成本或 payload 大小；生产环境通常还需要配合 `max_concurrency`、预算系统和 provider quota 监控。

### `base_url`、`openai_proxy` 与 router 集成

* `base_url` 用于把 `OpenAI` 协议请求发送到 OpenAI-compatible 服务，例如自建 `vLLM` 或公司内部模型网关；

```python
model = init_chat_model(
    model="MODEL_NAME",
    model_provider="openai",
    base_url="https://your-vllm-server.example.com/v1",
    api_key="YOUR_API_KEY",
)
```

> 用 `ChatOpenAI` / `OpenAI` 协议，但把请求地址改成你的 `vLLM`、`Together AI` 或其他 OpenAI-compatible 服务。

* `openai_proxy` 用于配置 HTTP 网络代理，不改变目标 provider；

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-5.5",
    openai_proxy="http://proxy.example.com:8080",
)
```

> 请求还是发给 OpenAI 官方 API，但网络流量先经过公司代理服务器。

* router：模型路由平台，比如`OpenRouter`、`LiteLLM` 这类平台，它是模型 router，不只是代理地址，通常有自己的路由参数、provider 元数据和 fallback 能力。LangChain 官方建议优先用专用集成如 `ChatOpenRouter`、`ChatLiteLLM` 或 `ChatLiteLLMRouter` 等专用集成。

```python
from langchain_openrouter import ChatOpenRouter

model = ChatOpenRouter(
    model="auto",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
```

> 如果只是接一个普通 OpenAI-compatible 模型服务，用 `base_url` 可以；如果接的是 `OpenRouter`、`LiteLLM` 这种带路由能力的平台，优先用它们的 LangChain 专用 integration，不要简单伪装成 `openai` provider。

### `logprobs` 与 token usage

`logprobs=True` 通常通过 `model.bind(logprobs=True)` 开启，返回的 token 级别概率信息位于 `response.response_metadata["logprobs"]`；

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    model="gpt-5.5",
    model_provider="openai",
).bind(logprobs=True)

response = model.invoke("请用一句话解释 LangChain 的模型抽象。")

# token 级别概率信息
print(response.response_metadata["logprobs"])

# token 用量信息
print(response.usage_metadata)
```

`usage_metadata` 是模型响应中的 token 用量信息，可包含 `input_tokens`、`output_tokens`、`total_tokens`、`cache_read`、`reasoning` 等字段，也可以通过 `UsageMetadataCallbackHandler` 或 `get_usage_metadata_callback()` 聚合统计多模型调用成本。

```python
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback

model_1 = init_chat_model(model="gpt-5.4-mini")
model_2 = init_chat_model(model="claude-haiku-4-5-20251001")

with get_usage_metadata_callback() as cb:
    model_1.invoke("请用一句话解释 token。")
    model_2.invoke("请用一句话解释模型成本统计。")
    print(cb.usage_metadata)
```

### `RunnableConfig`

`RunnableConfig` 是**运行时控制平面**，常见字段包括：

- `run_name`：当前 run 名称。
- `tags`：用于追踪、筛选和分组。
- `metadata`：业务上下文元数据，例如 `user_id`。
- `callbacks`：回调处理器。
- `max_concurrency`：批处理最大并发。
- `recursion_limit`：复杂链路递归深度上限。

这些配置对 `LangSmith` 调用链追踪、成本归因、线上监控和自定义日志非常关键。

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5.5", model_provider="openai")

responses = model.batch(
    [
        "请解释 invoke()。",
        "请解释 stream()。",
        "请解释 batch()。",
    ],
    config={
        "run_name": "模型 API 批处理解释",
        "tags": ["models", "batch"],
        "metadata": {"user_id": "user-123"},
        "max_concurrency": 2,
    },
)

for response in responses:
    print(response.text)
```

> `RunnableConfig` 不是模型初始化参数，而是每次调用时通过 `config={...}` 传入，用于控制本次运行的追踪信息、回调、并发和递归限制。

### `configurable_fields` 与运行时可配置模型

如果 `init_chat_model()` 不指定具体模型，默认 `model` 和 `model_provider` 可通过 `config["configurable"]` 动态传入。也可以通过 `configurable_fields=("model", "model_provider", "temperature", "max_tokens")` 限定可配置字段，并通过 `config_prefix` 区分多个模型节点。

```python
configurable_model = init_chat_model(temperature=0)

configurable_model.invoke(
    "请介绍你自己。",
    config={"configurable": {"model": "gpt-5-nano"}},
)
```

### `@wrap_model_call` 与动态模型路由

动态模型路由通过 `@wrap_model_call` 中间件实现，可在 `@wrap_model_call` 中读取 `request.state` 里的当前 Agent 状态，例如 `request.state["messages"]`，再结合运行时上下文、租户等级、任务复杂度和成本策略切换模型。

关键 API 包括：

- `@wrap_model_call`
- `ModelRequest`
- `ModelResponse`
- `request.override(model=model)`

注意：动态模型选择与结构化输出结合时，不支持传入已经 `bind_tools()` 的 pre-bound model。需要结构化输出时，应传入未预绑定的模型实例，让 `create_agent()` 或 `Harness` 接管工具绑定和响应格式绑定。

> 注意：`request.state` 和 `runtime.context` 不是同一个东西。
>
> * `request.state`：Agent 当前运行中不断变化的状态，例如 `messages`、中间结果、工具调用轨迹等。
> * `runtime.context`：单次运行时传入的外部业务上下文，例如 `user_id`、租户、权限、套餐等级等。

### LangSmith 与 LangSmith Engine

`LangSmith` 用于模型调用链追踪、工具路由检查、token 成本分析、错误定位和线上监控。`LangSmith Engine` 可监控 traces，发现 recurring issues 并提出修复建议。对 `Models` 模块而言，它主要用于比较 provider、定位结构化输出失败、分析延迟、追踪 `tool_calls` 和统计 token 成本。

## 工程化代码落地示例

本节通过三个可独立运行的脚本，展示 `LangChain Models` 在工程中的典型用法：示例 1 覆盖 `ChatModel` 的基础调用、流式输出、工具调用、结构化输出和 `token` 统计；示例 2 演示运行时模型配置、批处理并发和速率限制；示例 3 展示如何在 `Agent` 中通过 `@wrap_model_call` 实现动态模型路由，并保持结构化输出能力。

### 示例 1：生产级 ChatModel 调用链路：流式输出、工具调用与结构化结果

models_production_demo.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author : nanzet
# Description : 演示 LangChain ChatModel 的初始化、调用、流式输出、工具调用、结构化输出和 token 用量统计
# requirements : pip install -U langchain-google-genai pydantic typing_extensions

import json
import os
import sys
from typing import Any

from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_core.callbacks import UsageMetadataCallbackHandler
from pydantic import BaseModel, Field

MODEL_NAME = "google_genai:gemini-3.5-flash"


class Movie(BaseModel):
    """电影结构化信息。"""

    title: str = Field(description="电影标题")
    year: int = Field(description="上映年份")
    director: str = Field(description="导演")
    rating: float = Field(description="十分制评分")


@tool
def get_weather(location: str) -> str:
    """查询指定地点的天气。"""
    return f"{location} 当前天气晴朗，适合外出。"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量：{name}。请设置后重新运行脚本。")
    return value


def text_of(message: Any) -> str:
    text = getattr(message, "text", None)
    if isinstance(text, str) and text:
        return text

    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(part for part in parts if part)

    return str(message)


def print_structured_response(response: Any) -> None:
    if hasattr(response, "model_dump_json"):
        print(response.model_dump_json(indent=2))
    elif isinstance(response, (dict, list)):
        print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        print(str(response))


def run_basic_invocation(model: Any) -> None:
    print("基础调用结果：")
    response = model.invoke("请用两句话解释 LangChain 的模型抽象。")
    print(text_of(response))


def run_streaming(model: Any) -> None:
    print("\n流式输出结果：")
    for chunk in model.stream("请用三点说明为什么模型流式输出能改善用户体验。"):
        print(text_of(chunk), end="", flush=True)
    print()


def run_tool_calling(model: Any) -> None:
    print("\n工具调用结果：")
    available_tools = {"get_weather": get_weather}
    model_with_tools = model.bind_tools(list(available_tools.values()))
    messages: list[Any] = [
        {"role": "user", "content": "请查询北京和上海的天气，并给出简短建议。"}
    ]

    ai_message = model_with_tools.invoke(messages)
    messages.append(ai_message)

    if not ai_message.tool_calls:
        print("模型没有请求调用工具，直接输出：")
        print(text_of(ai_message))
        return

    for tool_call in ai_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        print(f"准备执行工具：{tool_name}，参数：{tool_args}")

        selected_tool = available_tools.get(tool_name)
        if selected_tool is None:
            print(f"模型请求了未注册工具：{tool_name}，已跳过该工具调用。")
            continue

        tool_result = selected_tool.invoke(tool_call)
        messages.append(tool_result)

    final_response = model_with_tools.invoke(messages)
    print(text_of(final_response))


def run_structured_output(model: Any) -> None:
    print("\n结构化输出结果：")
    model_with_structure = model.with_structured_output(Movie)
    response = model_with_structure.invoke("请给出电影《盗梦空间》的基本信息。")
    print_structured_response(response)


def run_usage_tracking(model: Any) -> None:
    print("\nToken 用量统计：")
    callback = UsageMetadataCallbackHandler()
    response = model.invoke(
        "请用一句话说明 token 用量统计在生产环境中的价值。",
        config={
            "run_name": "模型用量统计示例",
            "tags": ["models", "usage"],
            "metadata": {"user_id": "demo-user"},
            "callbacks": [callback],
        },
    )
    print(text_of(response))
    print(callback.usage_metadata)


def main() -> int:
    try:
        require_env("GOOGLE_API_KEY")

        model = init_chat_model(
            MODEL_NAME,
            temperature=0,
            timeout=60,
            max_tokens=2000,
            max_retries=6,
        )

        run_basic_invocation(model)
        run_streaming(model)
        run_tool_calling(model)
        run_structured_output(model)
        run_usage_tracking(model)
        return 0

    except ImportError as exc:
        print(f"依赖导入失败：{exc}")
        print(
            "请执行：pip install -U langchain-google-genai pydantic typing_extensions"
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
基础调用结果：
LangChain的模型抽象通过统一的接口，将不同厂商的大模型标准化为“语言模型（LLMs）”和“聊天模型（Chat Models）”两大类。

这种设计屏蔽了底层API的细节差异，使开发者无需修改核心代码，即可在不同的模型之间进行无缝切换与组合。

流式输出结果：
模型流式输出（Streaming Output，即字词逐个或逐块实时呈现）是现代大语言模型应用（如 ChatGPT）的标配。它能显著改善用户体验，原因主要体现在以下三点：

### 1. 显著降低“首字延迟”，消除用户的等待焦虑
* **原理解析**：大模型生成完整回答通常需要数秒甚至数十秒。如果采用“非流式输出”（一次性返回全部结果），用户在等待期间只能面对加载动画（如 Loading 菊花图），容易产生系统卡死或响应缓慢的挫败感。
* **体验提升**：流式输出让**首字响应时间（Time to First Token, TTFT）**缩短至几百毫秒。用户几乎在按下发送键的瞬间就能看到模型开始“说话”，这种即时反馈极大地缓解了等待焦虑，让交互显得流畅且高效。

### 2. 符合人类阅读习惯，提供更自然的“渐进式”认知体验
* **原理解析**：人类的阅读和信息处理是线性的。如果瞬间弹出一大段文字（“信息轰炸”），用户需要花时间重新定位阅读起点，容易产生视觉疲劳和认知过载。
* **体验提升**：流式输出模仿了人类说话或打字的自然节奏。用户可以跟随文字生成的进度**边出边读**。这种渐进式的信息呈现方式不仅更具拟人感（像在与真人对话），还能让用户的大脑同步消化信息，提高阅读的舒适度和理解效率。

### 3. 支持实时反馈与即时干预，提高任务处理效率
* **原理解析**：在长文本生成或复杂任务中，模型有时会“幻觉”（胡说八道）或偏离用户的真实意图。
* **体验提升**：通过流式输出，用户可以在模型刚开始生成的几秒内，就判断出方向是否正确。如果发现模型理解有误，用户可以**立即点击“停止生成”**并修改 Prompt（提示词），而不需要傻傻等待模型吐完几百个错字。这种“过程可控性”极大地节省了用户的时间，提升了人机协作的整体效率。

工具调用结果：
准备执行工具：get_weather，参数：{'location': '北京'}
准备执行工具：get_weather，参数：{'location': '上海'}
北京和上海目前的天气都非常好：

*   **北京**：当前天气晴朗，非常适合外出。
*   **上海**：当前天气同样晴朗，适合出行。

**简短建议**：两地今天都是晴空万里，非常适合进行户外活动或晾晒衣物。不过紫外线可能较强，外出时请注意防晒和补水。

结构化输出结果：
{
  "title": "盗梦空间",
  "year": 2010,
  "director": "克里斯托弗·诺兰",
  "rating": 9.4
}

Token 用量统计：
Token 用量统计是生产环境中实现**精细化成本控制**、**精准商业化计费**以及**系统容量与异常监控**的核心数据基石。
{'gemini-3.5-flash': {'input_tokens': 16, 'output_tokens': 712, 'total_tokens': 728, 'input_token_details': {'cache_read': 0}, 'output_token_details': {'reasoning': 676}}}
```

**代码说明：**

* **模型初始化**：脚本通过 `init_chat_model()` 初始化 `google_genai:gemini-3.5-flash`，并设置 `temperature=0`、`timeout=60`、`max_tokens=2000` 和 `max_retries=6`，用于控制输出稳定性、请求超时、生成长度和失败重试。
* **基础调用**：`run_basic_invocation()` 演示 `model.invoke()` 的最小用法，输入一段中文 prompt，返回完整的 `AIMessage`。
* **流式输出**：`run_streaming()` 演示 `model.stream()`，逐步接收模型生成的 `AIMessageChunk`，适合长文本生成和实时 UI 展示。
* **工具调用**：`get_weather()` 使用 `@tool` 声明为模型可调用工具，`run_tool_calling()` 通过 `model.bind_tools()` 将工具 schema 暴露给模型，再根据 `response.tool_calls` 手动执行工具并把工具结果追加回 `messages`。
  * **工具调用兜底**：`available_tools` 保存已注册工具映射；如果模型请求了未注册工具，脚本会打印提示并跳过，避免静默忽略或伪造错误的 `ToolMessage`。
* **结构化输出**：`Movie` 使用 `Pydantic BaseModel` 定义结构化 schema，`run_structured_output()` 通过 `model.with_structured_output(Movie)` 要求模型返回符合 schema 的电影信息。
  * **结构化结果打印**：`print_structured_response()` 兼容 `Pydantic BaseModel`、`dict`、`list` 和其他返回类型，避免结构化 schema 从 `Pydantic` 换成 `TypedDict` 或 `JSON Schema` 后打印逻辑失效。
* **Token 用量统计**：`run_usage_tracking()` 使用 `UsageMetadataCallbackHandler` 统计模型调用的 `input_tokens`、`output_tokens`、`total_tokens` 等信息，适合生产环境中的成本分析和调用监控。
* **响应文本提取**：`text_of()` 统一处理 `message.text`、字符串 `content` 和 `content_blocks`，避免不同 provider 返回格式差异导致打印异常。

### 示例 2：运行时可配置模型与并发限流控制

models_configurable_demo.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author : nanzet
# Description : 演示 LangChain 可配置模型、批处理并发控制和速率限制器
# requirements : pip install -U langchain langchain-deepseek

import os
import sys
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.rate_limiters import InMemoryRateLimiter


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量：{name}。请设置后重新运行脚本。")
    return value


def text_of(message: Any) -> str:
    text = getattr(message, "text", None)
    if isinstance(text, str) and text:
        return text
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else str(content)


def main() -> int:
    try:
        require_env("DEEPSEEK_API_KEY")

        rate_limiter = InMemoryRateLimiter(
            requests_per_second=0.2,
            check_every_n_seconds=0.1,
            max_bucket_size=2,
        )

        configurable_model = init_chat_model(
            temperature=0,
            timeout=60,
            max_tokens=3000,
            rate_limiter=rate_limiter,
            configurable_fields=(
                "model",
                "model_provider",
                "temperature",
                "max_tokens",
            ),
        )

        response = configurable_model.invoke(
            "请用一句话说明运行时可配置模型的价值。",
            config={
                "configurable": {
                    "model": "deepseek-v4-pro",
                    "model_provider": "deepseek",
                }
            },
        )
        print("可配置模型调用结果：")
        print(text_of(response))

        questions = [
            "请解释模型批处理的适用场景。",
            "请解释 max_concurrency 的作用。",
            "请解释 rate_limiter 的作用。",
        ]

        responses = configurable_model.batch(
            questions,
            config={
                "max_concurrency": 2,
                "configurable": {
                    "model": "deepseek-v4-pro",
                    "model_provider": "deepseek",
                },
            },
        )

        print("\n批处理结果：")
        for index, item in enumerate(responses, start=1):
            print(f"{index}. {text_of(item)}")

        return 0

    except ImportError as exc:
        print(f"依赖导入失败：{exc}")
        print("请执行： pip install -U langchain langchain-deepseek")
        return 1
    except Exception as exc:
        print(f"脚本执行失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

```

**输出结果：**

```powershell
可配置模型调用结果：
运行时可配置模型的价值在于它使系统能够在不停机、不重新部署的情况下动态调整行为，从而实时响应业务需求变化，显著提升敏捷性与连续性。

批处理结果：
1. 模型批处理（Model Batching）是指将多个输入样本合并成一个批次（batch），一次性送入模型进行计算，而非逐个样本串行处理。它在深度学习推理和训练中被广泛使用，其适用场景主要取决于性能收益、延迟要求、硬件特性及数据特性等因素。

以下是模型批处理的核心适用场景和分析：

### 1. 高吞吐量优先的离线处理场景
这是批处理最典型、收益最大的场景。
- **场景举例**：
  - 大规模数据标注或特征提取
  - 离线批量推理（如每日定时对千万级图片打标、文本分类、向量化）
  - 模型训练过程（训练本身就依赖于大批次梯度下降）
- **为何适用**：
  - 不要求低延迟，更关注单位时间内处理的总样本数（吞吐量）。
  - 通过增加批次大小，可以充分利用 GPU 的并行计算单元，提高计算密度，将数据传输和核函数启动的开销均摊到更多样本上。
  - 离线任务通常可以将大量数据预先整理好，天然形成批次。

### 2. GPU/TPU 等高度并行硬件的利用
批处理的最大驱动力来自硬件的并行架构。
- **场景举例**：
  - 任何在 GPU 上运行的卷积神经网络（CNN）或 Transformer 模型推理。
  - 在 CPU 上利用 SIMD（单指令多数据流）指令集时，批次处理也能带来大幅加速（尤其在启用供应商库如 Intel OpenVINO、ONNX Runtime 优化时）。
- **为何适用**：
  - GPU 有成千上万个计算核心，单条样本无法填满算力，会导致计算单元大量空闲。
  - 批处理可以将矩阵乘法等操作从“矩阵-向量”运算转变为“矩阵-矩阵”运算，后者的算术强度（计算/访存比）更高，能更好地隐藏内存访问延迟，达到接近硬件的峰值算力。

### 3. 最大化内存带宽利用率
- **场景举例**：
  - 模型权重加载是瓶颈的轻量级模型（如 MobileNet 在小设备上）。
  - 推理过程中需要频繁从显存/内存读取相同权重与多条输入进行计算。
- **为何适用**：
  - 当处理单个样本时，模型权重必须从内存中读取一次。如果批次中有  N  个样本，权重只需要读取一次，却可以重复用于  N  次计算。
  - 这种方式将内存读取开销均摊，让访存瓶颈型模型变为计算瓶颈型，从而提升吞吐。

### 4. 可容忍可控延迟的在线服务
在线服务通常要求低延迟，但某些场景允许适度增加延迟以换取更高的资源利用率和更低的单次推理成本。
- **场景举例**：
  - 异步推理服务：用户提交任务后不立即等待结果，而是通过回调或轮询获取。
  - 推荐系统的候选集打分阶段：一次请求可能需要对上百个候选 item 打分，天然形成一个批次。
  - 智能客服中同时输入多条相似问法进行意图识别。
- **为何适用**：
  - 可以设置一个极短的时间窗口（如 5–20 毫秒）来攒批：将窗口内到达的请求合并成一个动态批次，一次性推理后拆分结果返回。
  - 这种方法牺牲了微秒到毫秒级的尾部延迟，但可以在保证系统整体响应在可接受范围（如 50ms）内的情况下，数倍提升服务实例的吞吐和硬件利用率。
  - 典型技术：TensorFlow Serving、Triton Inference Server 的动态批处理功能。

### 5. 序列长度或输入形状一致的场景（利于静态批处理）
- **场景举例**：
  - 图像分类、目标检测（经过预处理 resize 后尺寸固定）。
  - 文本分类（通过 padding 对齐到相同长度）。
  - 嵌入向量查找。
- **为何适用**：
  - 如果不需复杂的可变长度处理或掩码，直接拼接成规整张量效率最高。
  - 静态形状可以充分利用计算图的优化和 XLA 等编译加速。
  - 即使长度不一，通过填充（padding）和掩码（mask）仍然可以组成批次，是为动态批处理，在 NLP 模型中极为普遍。

### 6. 模型计算量较大，但并非极端巨大的情况
- **场景举例**：
  - ResNet-50、BERT-base、Stable Diffusion 等模型。
- **为何适用**：
  - 如果模型计算量极小（如简单的逻辑回归），CPU 上可能单条推理就很快，批次会引入组包和解包开销，反而得不偿失。
  - 如果模型极大（如 175B LLM），单个 GPU 显存可能仅能容纳 1 条请求（batch size=1），此时无法进行传统批处理，需转而使用连续批处理技术（如 vLLM 的 continuous batching）来调度注意力机制中的 KV cache，提升吞吐，但这属于更高级的批处理变体。
- **不适用的反例**：
  - 在极度实时、要求逐样本响应的流式场景（如实时语音对话），且硬件资源足够，可以接受单样本推理。
  - 某些边缘端设备，内存极度受限，无法容纳大于 1 的 batch size。

### 总结：决定是否使用批处理的关键决策因子
如果你面对一个具体任务，可以通过以下问题判断：
1. **对延迟的要求是毫秒级实时还是秒级异步？** → 异步或可容忍延迟则积极使用。
2. **硬件是 GPU 还是纯 CPU？** → GPU 上收益巨大；CPU 上需测试，小模型和高并发时也有明显收益。
3. **数据是否可以轻易积累成批？** → 离线全量或攒批窗口内请求量足够。
4. **模型计算量是否足够大？** → 足够大才值得，极简模型受益小。
5. **是否有内存/显存承载更大 batch？** → 需要确保不引发 OOM，并可配合梯度累积（训练）或 offload 技术。

批处理是一项用延迟换吞吐、用空间换时间的核心技术，在大多数非严格实时的深度学习应用中都是适用的，甚至已成为标准操作模式。
2. `max_concurrency` 是一个常见的配置参数，中文可译为“最大并发数”，它的核心作用是**限制同时执行的操作（如请求、任务、线程、协程）数量**。无论在后端服务、异步编程、分布式任务队列还是网络请求中，这个参数都用于控制资源消耗、保护系统稳定性并优化吞吐量。

在不同的技术场景中，它的具体含义和效果如下：

---

### 1. 异步与并发编程（如 `asyncio.Semaphore`、`ThreadPoolExecutor`）
- **限制协程/线程同时运行的数量**  
  当你使用 `asyncio` 发起大量网络请求时，如果同时发起 1000 个请求，可能会耗尽带宽、导致目标服务器限流或本地端口耗尽。通过 `max_concurrency`（常通过 `asyncio.Semaphore(max_concurrency)` 实现），可以保证**任意时刻只有 N 个协程在同时执行**，其余协程排队等待。
- **效果**：平滑负载、避免触发远端限流、降低内存与连接数峰值。

### 2. HTTP 客户端（如 `aiohttp`、`httpx`、爬虫框架）
- **控制对同一域名的并发连接数**  
  例如 `aiohttp` 的 `TCPConnector` 有 `limit` 参数（等同于 `max_concurrency`），它限制同时打开的连接数。  
  **作用**：遵守目标网站的爬虫礼仪、防止被判定为攻击、减少超时和错误重试。

### 3. API 与微服务网关（如 FastAPI 的后台任务、自定义并发控制）
- **保护下游服务**  
  当你的服务需要调用第三方 API，且该 API 有明确的 QPS/并发数限制（如“同一账号最多 5 个并发请求”）时，设置 `max_concurrency=5` 可以确保不会超出限制，避免被拒绝服务。
- **后端压力控制**  
  在消费消息队列或者后台批量任务时，限制并发数可以防止 CPU 满载、数据库连接池耗尽。

### 4. 分布式任务队列（如 Celery）
- **工作进程/协程的并发粒度**  
  Celery 的 `--concurrency` 或 `worker_concurrency` 决定了工作节点**同时能处理多少个任务**。  
  - 如果设为 1，任务严格串行。
  - 如果设为 10，节点同时拉取并执行最多 10 个任务。
  **作用**：平衡任务吞吐量与系统资源（CPU 核数、内存、数据库连接）。

### 5. 大数据与流处理（如 Flink、Spark Streaming）
- **算子并行度与背压控制**  
  虽然常称为 `parallelism`，但有时也会出现 `maxConcurrency` 来限制某个算子的最大并发实例数，**防止下游被冲垮**。

---

### 为什么需要 `max_concurrency`？常见动机总结：
| 如果没有限制 | 设置合适 max_concurrency 后 |
|-------------|---------------------------|
| 瞬间发起海量请求，打垮目标服务 | 请求平缓发送，下游稳定 |
| 本地 CPU/内存/文件描述符被耗尽 | 资源占用平稳可控 |
| 任务全部抢到资源但都超时失败 | 成功率上升，总耗时可能更短 |
| 数据库连接池耗尽，所有操作报错 | 排队等待连接，系统仍有响应 |

### 如何选择合理的值？
- **I/O 密集型任务**（网络请求、磁盘读写）：可以设得较高（如 50～200），受限于带宽、文件描述符和目标服务承受能力。
- **CPU 密集型任务**：建议设为 CPU 核心数（或稍多），避免上下文切换开销。
- **受下游限制**：严格按照下游文档或实测结果（如 API 允许 10 QPS，并发约 2～5）。

一句话总结：**`max_concurrency` 是限制“并行工作单元”数量的闸门，用来在吞吐量与稳定性之间取得平衡。**
3. 限流器（rate limiter）是一种用于控制系统处理请求速率的机制。它的核心作用是**防止系统或服务因短时间内接收到过多请求而过载，从而保障稳定性、可用性和公平性**。

可以从以下几个层面来理解它的作用：

### 1. 保护系统资源，防止过载
无论是 Web 服务器、数据库还是微服务，其处理能力（CPU、内存、I/O、连接数）都是有上限的。如果流量瞬间暴增（如突发新闻、秒杀活动或恶意攻击），系统可能因资源耗尽而响应变慢、崩溃或级联故障。
- **作用示例**：限制每个用户每分钟最多请求 100 次 API。当超过限制时，直接返回 `429 Too Many Requests`，避免后台服务被冲垮。

### 2. 防御恶意攻击和滥用
公共 API 或登录接口常常是恶意行为的目标，例如暴力破解密码、DDoS 攻击、爬虫抓取数据或刷单。
- **作用示例**：限制单个 IP 对登录接口的尝试次数（如 5 分钟内最多 5 次），可有效阻止暴力破解。
- **防止数据爬取**：限制单个账户或 IP 每天可调用的数据导出次数，防止批量窃取信息。

### 3. 保障服务质量与公平性（QoS）
在多租户系统或平台型产品中，某些用户可能会占用过多资源，影响其他用户的正常使用。限流器可以确保资源被公平分配。
- **作用示例**：免费 API 用户每秒 10 次请求，付费用户每秒 1000 次请求。这既实现了商业化隔离，又保证了基础用户体验。
- **隔离故障**：当下游某个服务变慢时，可以对调用该下游的请求进行限流，防止线程池被耗尽，这是一种熔断降级的补充手段（常与熔断器结合使用）。

### 4. 控制成本与第三方依赖
当系统依赖付费的外部服务（如短信发送、人脸识别、云存储接口）时，这些服务通常本身也有调用频率限制或按量计费。本地限流可以避免意外的高额账单。
- **作用示例**：应用内限制短信验证码的发送频率（如同号码 60 秒内只能发送一次，每天上限 5 条），既符合服务商要求，也控制了成本。

### 5. 平滑流量，削峰填谷
当流量呈脉冲式到达时，限流器可以结合队列，将请求以较平稳的速率释放给后端处理，避免后端压力剧烈波动。
- **作用示例**：消息队列消费端使用限流器，匀速拉取并处理消息，防止数据库写入压力瞬间飙升。

---

### 常见限流算法与位置
理解作用后，通常会选择以下算法来实现：

- **固定窗口**：简单计数，但边界处可能产生流量突刺。
- **滑动窗口**：更精细地平滑边界问题，避免突发。
- **漏桶（Leaky Bucket）**：严格平滑输出速率，强制请求以恒定速度被处理，超出则丢弃/排队。
- **令牌桶（Token Bucket）**：允许一定程度的突发流量，同时限制平均速率，是最常用的算法（如 Guava RateLimiter）。
- **分布式限流**：在集群环境中，通常需要借助 Redis + Lua 脚本或专门的网关组件（如 Sentinel、Kong）实现全局统一限流。

### 实施层面
限流器可以部署在多个层级：
- **网关层**：对进入系统的所有流量进行全局限流。
- **应用层/中间件**：对特定服务或接口进行细粒度限流。
- **基础设施层**：通过负载均衡器或容器编排的 ingress 控制器实现。

总而言之，**rate_limiter 是系统稳定性的第一道防护网**，它通过“拒绝一部分请求”来确保“大部分（甚至全部）系统”能够持续正常运行，是构建高可用分布式系统的必备组件。
```

**代码说明：**

* 该脚本演示 `LangChain` 中模型的运行时可配置能力，通过 `init_chat_model()` 创建一个未固定具体模型的 `configurable_model`。
* `configurable_fields=("model", "model_provider", "temperature", "max_tokens")` 表示这些字段可以在每次调用时通过 `config["configurable"]` 动态指定。
* `invoke()` 示例中通过 `model="deepseek-v4-pro"` 和 `model_provider="deepseek"` 指定本次调用使用 `DeepSeek` 模型，而不是在初始化阶段写死模型。
* `InMemoryRateLimiter` 用于限制模型请求速率，避免短时间内触发 provider 的限流策略。
* `batch()` 用于批量处理多个输入，`max_concurrency=2` 控制最多同时执行 2 个模型请求，适合在吞吐量和限流风险之间做平衡。
* `text_of()` 对不同 provider 返回的消息对象做文本提取，提升脚本在多模型场景下的兼容性。

### 示例 3：基于 `@wrap_model_call` 的动态模型路由与结构化输出

models_dynamic_routing_demo.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author : nanzet
# Description : 演示在 Agent 中使用动态模型路由和结构化输出
# requirements : pip install -U langchain-google-genai pydantic

import os
import sys

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

BASIC_MODEL_NAME = "gemini-2.5-flash"
ADVANCED_MODEL_NAME = "gemini-3.5-flash"


class ContentAnalysis(BaseModel):
    """内容分析结果。"""

    sentiment: str = Field(description="情感倾向，例如积极、消极或中性")
    key_entities: list[str] = Field(description="关键实体列表")
    summary: str = Field(description="简短中文摘要")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量：{name}。请设置后重新运行脚本。")
    return value


def main() -> int:
    try:
        require_env("GOOGLE_API_KEY")

        basic_model = init_chat_model(
            BASIC_MODEL_NAME, model_provider="google_genai", temperature=0
        )
        advanced_model = init_chat_model(
            ADVANCED_MODEL_NAME, model_provider="google_genai", temperature=0
        )

        @wrap_model_call
        def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
            """根据消息数量选择模型。"""
            message_count = len(request.state["messages"])
            if message_count > 3:
                selected_model = advanced_model
                selected_model_name = ADVANCED_MODEL_NAME
            else:
                selected_model = basic_model
                selected_model_name = BASIC_MODEL_NAME

            print(
                f"动态路由：当前 messages 数量={message_count}，"
                f"选择模型={selected_model_name}"
            )
            return handler(request.override(model=selected_model))

        agent = create_agent(
            model=basic_model,
            tools=[],
            middleware=[dynamic_model_selection],
            response_format=ContentAnalysis,
            system_prompt="你是专业内容分析助手，请严格按照结构化 schema 输出中文结果。",
        )

        def run_analysis_case(title: str, messages: list[dict[str, str]]) -> None:
            print(f"\n{title}")
            result = agent.invoke({"messages": messages})
            structured_response = result["structured_response"]
            print("结构化分析结果：")
            print(structured_response.model_dump_json(indent=2))

        run_analysis_case(
            "场景一：短上下文，预期使用基础模型",
            [
                {
                    "role": "user",
                    "content": "这款旗舰手机续航优秀，但夜景算法仍需优化。请给出结构化分析。",
                }
            ],
        )

        run_analysis_case(
            "场景二：长上下文，预期使用高级模型",
            [
                {"role": "user", "content": "我们正在评估一款旗舰手机。"},
                {"role": "assistant", "content": "请继续提供评价信息。"},
                {"role": "user", "content": "它的屏幕色彩准确，性能稳定。"},
                {"role": "assistant", "content": "已记录屏幕和性能信息。"},
                {
                    "role": "user",
                    "content": "但夜景算法偏慢，机身发热明显。请给出结构化分析。",
                },
            ],
        )
        return 0

    except ImportError as exc:
        print(f"依赖导入失败：{exc}")
        print("请执行：pip install -U langchain-google-genai pydantic")
        return 1
    except Exception as exc:
        print(f"脚本执行失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

```

**输出结果：**

```powershell
场景一：短上下文，预期使用基础模型
动态路由：当前 messages 数量=1，选择模型=gemini-2.5-flash
结构化分析结果：
{
  "sentiment": "中性",
  "key_entities": [
    "旗舰手机",
    "续航",
    "夜景算法"
  ],
  "summary": "这款旗舰手机电池续航表现出色，但夜景拍摄的算法有待改进。"
}

场景二：长上下文，预期使用高级模型
动态路由：当前 messages 数量=5，选择模型=gemini-3.5-flash
结构化分析结果：
{
  "sentiment": "中性",
  "key_entities": [
    "旗舰手机",
    "屏幕",
    "性能",
    "夜景算法",
    "机身"
  ],
  "summary": "该旗舰手机屏幕色彩准确、性能稳定，但存在夜景算法偏慢和机身发热明显的问题。"
}
```

**代码说明：**

* 该脚本演示在 `Agent` 内通过 `@wrap_model_call` 实现动态模型路由，根据当前 `messages` 数量在不同模型之间切换。
* `BASIC_MODEL_NAME="gemini-2.5-flash"` 作为基础模型，适合短上下文、低复杂度任务；`ADVANCED_MODEL_NAME="gemini-3.5-flash"` 作为高级模型，适合长上下文或更复杂任务。
* `ContentAnalysis` 使用 `Pydantic BaseModel` 定义结构化输出 schema，约束模型返回 `sentiment`、`key_entities` 和 `summary` 三个字段。
* `create_agent()` 通过 `response_format=ContentAnalysis` 启用结构化输出，让最终结果可以从 `result["structured_response"]` 中读取。
* `dynamic_model_selection()` 是核心路由逻辑：读取 `request.state["messages"]` 计算消息数量，若 `message_count > 3` 则切换到高级模型，否则使用基础模型。
* `request.override(model=selected_model)` 用于在当前模型调用前替换实际执行的模型，这是动态模型路由的关键 API。
* 脚本设计了两个测试场景：短上下文触发 `gemini-2.5-flash`，长上下文触发 `gemini-3.5-flash`，并打印实际选择的模型，方便观察路由效果。

## 常见踩坑与高频面试点

### 常见踩坑

#### 踩坑 1：把 `init_chat_model()` 当成固定模型白名单

* 原因：LangChain 的 provider package 会把模型名直接传给 provider API，新模型通常不需要等待 LangChain 主包更新。
* 修复方式：优先使用 `provider:model` 格式，例如 `google_genai:gemini-3.5-flash`；如果模型能力数据缺失，再结合 `model.profile`、provider 文档或运行时探测补齐判断。

#### 踩坑 2：混淆 `batch()` 和 provider 原生 batch API

* 原因：`batch()` 是 LangChain 客户端并发调用，和 `OpenAI`、`Anthropic` 的 provider 原生 batch API 不是一回事。
* 修复方式：小批量独立请求使用 `batch()`；大规模离线任务优先评估 provider 原生 batch API。

#### 踩坑 3：流式输出只读取 `chunk.text`，漏掉 `tool_call_chunk` 和 `reasoning`

* 原因：`stream()` 返回 `AIMessageChunk`，其中可能包含 `content_blocks`、`tool_call_chunks` 和 `reasoning`。
* 修复方式：生产 UI 应按 `content_blocks` 类型分流处理，将推理块、正文块和工具调用块分别渲染。

#### 踩坑 4：手动工具调用时没有把 `ToolMessage` 放回消息历史

* 原因：独立使用 `bind_tools()` 时，模型只生成工具调用请求，不会自动执行工具。
* 修复方式：执行工具后把 `ToolMessage` 追加到 `messages`，再调用模型生成最终回答；如果不想手写执行循环，使用 `create_agent()`。

#### 踩坑 5：结构化输出只依赖 prompt，不做 schema 约束和校验

* 原因：`json_mode` 只能提高合法 JSON 概率，不能严格保证字段、类型和嵌套结构。
* 修复方式：优先使用 `with_structured_output()`；强校验场景使用 `Pydantic BaseModel`；排查问题时开启 `include_raw=True`。

#### 踩坑 6：动态模型选择时传入已经 `bind_tools()` 的 pre-bound model

* 原因：官方文档明确说明，动态模型选择结合结构化输出时不支持 pre-bound model，容易导致 schema 或工具绑定冲突。
* 修复方式：在 `@wrap_model_call` 中传入未预绑定的模型实例，让 `create_agent()` 或 `Harness` 统一处理工具绑定与结构化输出。

#### 踩坑 7：生产环境只设置 `max_retries`，忽略 `timeout`、`rate_limiter` 和 `max_concurrency`

* 原因：`max_retries` 只能缓解瞬时失败，不能控制请求长时间挂起、并发请求堆积、`token` 成本暴涨和 provider 限流。
* 修复方式：模型初始化时设置 `timeout`、`max_retries` 和 `rate_limiter`；批处理或并发调用时，通过 `config={"max_concurrency": n}` 控制最大并发数。

#### 踩坑 8：生产关键链路缺少可观测性，只看最终回答

* 原因：模型问题往往发生在工具选择、`token` 成本、重试、超时、结构化解析和流式事件中；只看最终回答，难以定位问题发生在哪一段链路。
* 修复方式：对生产关键链路、复杂 `Agent`、高成本模型调用或频繁失败的场景，建议接入 `LangSmith tracing`，并通过 `run_name`、`tags`、`metadata` 标记业务上下文；如果系统已有成熟的日志、指标和链路追踪平台，也可以先与现有可观测体系集成，不必所有场景都强制使用 `LangSmith`。

---

### 高频面试点

#### Q1：`LangChain` 的 `Models` 抽象解决了什么核心问题？

**答：** 它解决的是多 provider、多模型能力差异下的统一调用问题。底层通过 provider integration package 把 `OpenAI`、`Anthropic`、`Google Gemini`、`AWS Bedrock`、`HuggingFace`、`OpenRouter` 等模型适配到同一套 `ChatModel` 接口，上层统一使用 `invoke()`、`stream()`、`batch()`、`bind_tools()`、`with_structured_output()`。相比直接调用各 provider SDK，LangChain 的价值在于让模型替换、Agent 集成、工具调用、结构化输出、追踪和批处理控制保持一致。

#### Q2：`init_chat_model()` 和直接实例化 `ChatOpenAI`、`ChatAnthropic` 有什么区别？

**答：** `init_chat_model()` 是统一工厂入口，适合用 `provider:model` 字符串做配置化和运行时切换；直接实例化模型类适合需要 provider 专属参数和类型提示的场景，例如 `ChatOpenAI(use_responses_api=...)` 或 `AzureChatOpenAI(azure_deployment=...)`。工程上，通用模型路由优先使用 `init_chat_model()`，深度使用 provider 能力时使用具体模型类。

#### Q3：为什么说 `model` 是 `Agent` 的推理引擎？

**答：** `Agent` 循环的本质是模型读取当前 `messages` 和状态，判断是否需要调用工具；如果需要，就生成 `tool_calls`，工具结果返回后模型继续推理，直到不再请求工具并输出最终结果。`Harness` 负责上下文、工具、中间件、检查点和执行控制，而 `model` 决定“下一步做什么”。因此模型能力直接决定工具选择质量、结构化输出稳定性、长上下文处理能力和任务完成率。

#### Q4：`invoke()`、`stream()`、`astream_events()` 的区别是什么？

**答：** `invoke()` 返回完整 `AIMessage`，适合短任务和后端批处理；`stream()` 返回 `AIMessageChunk`，适合实时 UI 和长文本输出；`astream_events()` 返回模型或链路运行过程中的异步语义事件，例如 `on_chat_model_start`、`on_chat_model_stream`、`on_chat_model_end`，适合调试、观测和事件级过滤。对比来看，`stream()` 关注内容增量，`astream_events()` 关注运行过程。

#### Q5：`bind_tools()` 和 `create_agent()` 自动工具执行有什么区别？

**答：** `bind_tools()` 只是把工具 schema 暴露给模型，模型返回的是工具调用请求；独立模型调用时，开发者必须执行工具、生成 `ToolMessage` 并传回模型。`create_agent()` 则封装了这个循环，自动处理工具执行、消息追加和终止判断。底层差异是：前者是模型能力，后者是 `Harness` 编排能力。

#### Q6：如何理解 client-side tool calling 和 server-side tool use？

**答：** client-side tool calling 中，模型生成 `tool_calls`，工具由应用侧执行，并通过 `ToolMessage` 返回结果；server-side tool use 中，工具如 `web_search` 由 provider 在服务端执行，结果以 `server_tool_call` 和 `server_tool_result` 出现在 `content_blocks` 中，不需要本地执行工具。前者可控性更强，适合业务系统；后者集成简单，适合 provider 内置能力。

#### Q7：结构化输出为什么不能只靠 prompt？

**答：** prompt 只能软约束模型，不能保证字段完整、类型正确和嵌套结构稳定。`with_structured_output()` 通过 provider 原生 schema、tool calling 或 `json_mode` 提高输出可解析性；`Pydantic BaseModel` 还提供运行时验证。对比来看，`Pydantic` 最适合强校验，`TypedDict` 更轻量，`JSON Schema` 更适合跨语言和系统集成。

#### Q8：`ProviderStrategy` 和 `ToolStrategy` 如何区分？

**答：** `ProviderStrategy` 是 Provider 原生结构化输出策略，依赖模型服务商自身的 structured output 能力，通常更可靠；`ToolStrategy` 是工具调用结构化输出策略，通过强制模型调用一个结构化工具来得到符合 schema 的结果。`create_agent(response_format=Schema)` 可根据 `model.profile` 自动选择策略；如果 `profile` 数据缺失或模型能力特殊，可以手动指定。

#### Q9：`model.profile` 在工程中有什么价值？

**答：** `model.profile` 提供模型能力元数据，例如上下文窗口、多模态输入、推理输出、工具调用、结构化输出支持。它让系统可以动态做模型能力 gating、自动选择结构化输出策略、根据上下文窗口触发摘要、在模型选择器中展示能力标签。相比硬编码模型能力表，`profile` 更适合多 provider、多模型快速演进的环境。

#### Q10：如何做生产级模型容错？

**答：**

* 第一层在模型初始化时设置 `timeout`、`max_retries`，利用指数退避处理网络错误、`429` 和 `5xx`；
* 第二层用 `rate_limiter` 和 `max_concurrency` 控制请求速率和并发；
* 第三层在 `Agent` 中用 `ModelRetryMiddleware`、`ModelFallbackMiddleware`、`ToolRetryMiddleware`、`ToolFallbackMiddleware` 做模型侧和工具侧容错；
* 第四层用持久化 `checkpointer` 保存长任务进度、图状态和中断点，必要时结合 `store` 保存跨会话长期记忆。这样才能同时控制可靠性、成本和恢复能力。

#### Q11：为什么需要 `RunnableConfig`？

**答：** `RunnableConfig`(运行时控制平面）用来控制“本次调用怎么运行”，不改变模型本身定义。模型初始化参数决定 `model`、`temperature`、`timeout` 等默认行为；`RunnableConfig` 则在 `invoke()`、`stream()`、`batch()` 调用时传入，用于设置 `run_name`、`tags`、`metadata`、`callbacks`、`max_concurrency`、`recursion_limit` 等运行时控制项。它的价值是把模型定义和运行控制分离，便于 `LangSmith` 追踪、成本归因、并发控制和线上问题排查。

示例：

```python
responses = model.batch(
    [
        "请解释 invoke()。",
        "请解释 stream()。",
        "请解释 batch()。",
    ],
    config={
        "run_name": "批量解释模型接口",
        "tags": ["models", "batch"],
        "metadata": {"user_id": "user-123"},
        "max_concurrency": 2,
    },
)
```

> * `model` 本身没有变。
> * `config` 只控制这一次运行。
> * `run_name`、`tags`、`metadata` 用于追踪和归因。
> * `max_concurrency` 用于控制 `batch()` 并发。

#### Q12：动态模型选择适合什么场景？

**答：** 动态模型选择适合成本优化、复杂度路由、租户分层和故障降级。例如短请求用 `gpt-5.4-mini`，复杂长对话切到 `gpt-5.5`，高价值用户使用更强模型。底层通过 `@wrap_model_call` 拦截模型调用，根据 `request.state` 和上下文选择模型，再用 `request.override(model=model)` 传给后续 handler。它比在业务代码中到处写 if/else 更可组合、更可测试，更贴近 Agent 生命周期。

#### Q13：如何处理深度推理模型的 `reasoning` 与正文混合输出？

**答：** LangChain 用 `content_blocks` 统一承载不同 provider 的输出块。开发者可以遍历 `AIMessage` 或 `AIMessageChunk` 的 `content_blocks`，通过 `block["type"] == "reasoning"` 提取推理过程，通过 `block["type"] == "text"` 提取最终正文。相比正则拆分字符串，这种方式更稳定，也更适合前端实现“推理过程折叠区”和“最终回答区”的双通道渲染。

#### Q14：如何用 prompt caching 和 batch 优化成本与吞吐？

**答：** 对共享大量系统指令、工具描述或 RAG 上下文的任务，应优先利用 prompt caching，减少重复输入 token 成本；对彼此独立的请求，应使用 `batch()` 或 `batch_as_completed()` 并配合 `max_concurrency` 控制并发。二者解决的问题不同：prompt caching 降低重复上下文成本，batch 提升独立请求吞吐。生产环境还需要结合 `rate_limiter`、token 预算和 provider quota 监控。
