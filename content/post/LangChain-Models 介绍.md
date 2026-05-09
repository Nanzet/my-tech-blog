---
title: "LangChain Models 介绍"
date: 2026-05-08T22:11:17+08:00
slug: "angchain-models-introduction"
image: ""
categories:
    - 技术
tags:
    - LangChain
draft: false
---

## 💡 一句话核心概念

LangChain 的 `Models` 模块本质上是一个<strong>“标准适配器（Adapter）与接口防腐层”</strong>。它抹平了底层各大模型厂商（OpenAI、Anthropic、本地部署等）的 API 差异，让你能用一套标准代码实现模型路由、无缝切换、工具绑定和强制结构化输出，彻底解决“厂商锁定（Vendor Lock-in）”痛点，并为 Agent 奠定了标准契约。

---

## 常用核心 API 及核心参数

### <font style="color:#DF2A3F;">`init_chat_model()`</font>

+ <strong>作用</strong>：标准的<strong>工厂方法</strong>。在企业级工程中，我们极少在业务代码里硬编码 `ChatOpenAI()` 等具体实现类，而是通过它配合配置中心，实现运行时的<strong>模型动态路由</strong>和热切换。
+ <strong>核心参数</strong>：
  + <strong>`model`</strong>: 模型名称（如 `"gpt-4o"` 或 `"openai:gpt-4o"`）。
  + <strong>`temperature`</strong>: 控制输出的随机性（0为确定性输出，业务逻辑常用 0；创意生成用 0.7+）。
  + <strong>`max_retries`</strong>: 遇到网络超时或 API 限流（HTTP 429）时的自动重试次数（默认 6，采用指数退避机制，<strong>高可用设计必备</strong>）。
  + <strong>`max_tokens`</strong>：限制模型最多能输出多少个 token，用来控制回答的长度。
  + <strong>`timeout`</strong>：设置网络请求的最大等待时间（秒）。

```python
import os
from langchain.chat_models import init_chat_model

if __name__ == "__main__":
    # 替换为真实的 API Key
    os.environ["OPENAI_API_KEY"] = "sk-xxx"

    # 后端规范：参数化初始化，方便平滑迁移或降级
    model = init_chat_model(
        "gpt-4o-mini",
        model_provider="openai",
        # 传递给模型的具体参数：
        temperature=0.7,
        timeout=30,
        max_tokens=1000,
        max_retries=6,  # 默认值；如果网络不稳定可以适当调大
    )

    print("模型工厂初始化成功:", type(model))
    response = model.invoke("Ping, 测试连接请回复 Pong")
    print("模型响应:", response.content)
```

### <font style="color:#DF2A3F;">`bind_tools()`</font>

+ <strong>作用</strong>：Agent 架构的“手脚”。将后端的 Python 函数（工具）注册给模型，让 LLM 在推理时知道自己可以调用哪些外部接口。这是从“纯文本聊天”跨越到“智能体执行任务”的最关键一步。
+ <strong>核心参数</strong>：传入一个包含工具函数、Pydantic 类或 JSON Schema 的列表。

```python
import os
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

@tool
def get_user_balance(user_id: str) -> float:
    """查询用户账户余额"""
    # 模拟真实查库操作
    return 100.00 

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx"
    model = init_chat_model("gpt-4o-mini", model_provider="openai", temperature=0)

    # 挂载工具能力：把 Python 函数转为 JSON Schema 塞入大模型大脑
    agent_model = model.bind_tools([get_user_balance])

    # 触发调用：大模型判断出需要查数据，不会瞎编，而是生成调用指令
    response = agent_model.invoke("帮我查一下用户 9527 的余额")
    
    if response.tool_calls:
        print("【命中工具调用】")
        print(f"目标函数名: {response.tool_calls[0]['name']}")
        print(f"提取的参数字典: {response.tool_calls[0]['args']}")
```

### <font style="color:#DF2A3F;">`with_structured_output()`</font>

+ <strong>作用</strong>：数据交互的“强类型约束”。强迫模型放弃自然语言闲聊，必须返回严格符合 Schema（通常是 Pydantic）的对象。这是做后端业务集成、ETL 数据清洗和信息抽取时必不可少的利器。

```python
import os
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

# 定义严格的数据结构
class UserProfile(BaseModel):
    name: str = Field(description="用户的姓名")
    age: int = Field(description="用户的年龄")

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx"
    model = init_chat_model("gpt-4o-mini", model_provider="openai", temperature=0)

    # 强约束输出格式：模型返回的将直接是 Pydantic 对象
    structured_model = model.with_structured_output(UserProfile)
    
    result = structured_model.invoke("提取信息：张三今年25岁，老家是东北的。")
    
    print("返回的底层类型:", type(result))
    print("提取出的姓名 (自动映射):", result.name) 
    print("提取出的年龄 (自动转换类型):", result.age)
```

### <font style="color:#DF2A3F;">`invoke()`</font><font style="color:#DF2A3F;"> 与 </font><font style="color:#DF2A3F;">`stream()`</font>

+ <strong>作用</strong>：模型的执行引擎。
  + `invoke()` 是同步阻塞调用，返回单一的 `AIMessage`。
  + `stream()` 返回迭代器，产生 `AIMessageChunk`。这是后端结合 **SSE (Server-Sent Events)** 解决大模型响应慢、防止微服务网关（如 Nginx）超时的核心 API。

---

## 文档中提到的其他高级 API

### `astream_events()`

+ <strong>作用</strong>：细粒度的异步事件流 API。除了输出文本 Token，它还能让你监听到“模型开始思考”、“开始调用工具”、“生成结束”等具体事件（如 `on_chat_model_start`）。
+ <strong>场景</strong>：适合通过 WebSocket 给前端做复杂的中间状态追踪展示（比如：Agent 正在搜索网页...）。

### `InMemoryRateLimiter`

+ <strong>作用</strong>：内存级客户端限流器。配置在模型初始化时，用于控制向云端发起的 QPS，避免被大模型厂商临时封禁 API Key。
+ <strong>场景</strong>：高并发批处理任务时的自我保护。

### `UsageMetadataCallbackHandler` / `get_usage_metadata_callback()`

+ <strong>作用</strong>：Token 消耗拦截器/上下文管理器。用于在后台无侵入地统计某次请求或整个调用链路消耗了多少 Input/Output Token。
+ <strong>场景</strong>：企业内部的成本核算与计费计费埋点。

```python
import os
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx"
    model = init_chat_model("gpt-4o-mini", model_provider="openai")

    # 优雅的上下文管理器计费模式
    with get_usage_metadata_callback() as cb:
        model.invoke("讲个程序员的冷笑话")
        
        print("--- API 计费埋点统计 ---")
        # 拦截到的 Token 消耗将被完整记录
        print(f"输入消耗: {cb.usage_metadata['input_tokens']} tokens")
        print(f"输出消耗: {cb.usage_metadata['output_tokens']} tokens")
        print(f"总计费数: {cb.usage_metadata['total_tokens']} tokens")
```

### `RunnableConfig` (作为 `config` 参数传入)

+ <strong>作用</strong>：运行时上下文配置。可以在调用模型时动态传入元数据。
+ <strong>场景</strong>：传入 `tags` 和 `run_name` 用于 LangSmith 的链路追踪；传入 `max_concurrency` 限制批量处理（`batch`）的并发数。

---

## 极简代码脚手架

这段代码剥离了边缘配置，展示了后端接入大模型最核心的“<strong>工厂初始化 -> 绑定工具 -> 意图拦截</strong>”逻辑流。

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 模型工具调用示例

import os
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

# 统一初始化 (实际工程中，参数均来自配置中心)
os.environ["OPENAI_API_KEY"] = "sk-xxx" # 可替换为兼容的 DeepSeek 配置
model = init_chat_model("gpt-4o-mini", model_provider="openai", temperature=0)

# 定义后端业务逻辑 (挂载点)
@tool
def check_inventory(sku_id: str) -> str:
    """查询指定商品的当前库存量"""
    # 真实场景：执行 MySQL/Redis 查询
    return f"SKU:{sku_id} 库存充足，剩余 100 件"

if __name__ == "__main__":
    # 3. 将工具能力“绑定”到模型上
    agent_model = model.bind_tools([check_inventory])

    # 4. 执行调用 (模拟前端请求)
    response = agent_model.invoke("帮我看看 SKU-9988 还有货吗？")

    # 5. 后端路由：拦截并解析模型的意图
    if response.tool_calls:
        print(f"【路由至工具】模型决定调用函数: {response.tool_calls[0]['name']}")
        print(f"【解析参数】提取出的业务参数: {response.tool_calls[0]['args']}")
        # 下一步真实场景：实际执行 check_inventory 并把结果包装进 ToolMessage 再发给模型
    else:
        print(f"【直接响应】模型直接回复了文本: {response.content}")
```

---

## 常见踩坑与高频面试点（高级研发视角）

针对资深后端转型 Agent 开发，面试官通常会跳过基础语法，直接考察你对系统鲁棒性和模型能力边界的理解：

### 结构化输出的底层陷阱（高频考点）

+ <strong>面试官可能会问</strong>：“`with_structured_output` 真的能保证 100% 输出符合格式的 JSON 吗？解析失败导致线上抛出 Exception 怎么处理？”
+ <strong>工程视角</strong>：没有任何模型能保证 100% 格式完美。该方法的底层实现（无论是 `json_mode` 还是伪造 `tool_calling`）都存在概率失败。<font style="background-color:#FBDE28;">在生产环境中，</font><strong><font style="background-color:#FBDE28;">严禁信任模型的原生输出</font></strong><font style="background-color:#FBDE28;">。必须配合 Pydantic 进行异常捕获，一旦引发 </font><font style="background-color:#FBDE28;">`ValidationError`</font><font style="background-color:#FBDE28;">，不能直接给前端返回 500，而是需要实施</font><strong><font style="background-color:#FBDE28;">重试修正机制（Retry-and-Correct Pipeline）</font></strong><font style="background-color:#FBDE28;">，将报错信息连同历史记录再喂回给大模型，让其进行自我修复</font>。

### 工具调用（Tool Calling）的能力边界与幻觉（实战踩坑）

+ <strong>踩坑点</strong>：在实际开发中，尤其是使用本地小模型（如 7B/14B）或某些开源模型时，执行 `bind_tools` 极易翻车。模型经常会<strong>虚构（幻觉）</strong>一个不存在的参数传给你的函数，或者干脆忽略设定的工具开始用自然语言瞎编。
+ <strong>对策</strong>：如果模型能力不足，不能过度依赖高级的封装 API。往往需要退一步，通过极度详尽的 System Prompt 进行严格的输入输出格式约束，或者改用更底层的 ReAct 提示词模板手动引导其思考和输出，并在后端对 `args` 字典进行严格的类型断言。

### 流式响应的长连接维护（架构设计考点）

+ <strong>面试官可能会问</strong>：“大模型推理含有多次工具调用时，耗时极长，如何防止 Nginx/网关出现 504 Timeout？”
+ <strong>工程视角</strong>：坚决不能只用同步阻塞的 `.invoke()`。必须使用 `.stream()` 或 `.astream()`。后端需要利用 Python 的生成器（Generators）配合 <font style="color:#DF2A3F;">SSE 协议</font>建立长连接，将生成的 Token 逐块（Chunks）推流给前端。
+ <strong>踩坑点</strong>：流式返回的对象是 `AIMessageChunk`。如果业务需要落库保存完整的聊天记录供后续查询，后端必须在内存或 Redis 中手动重载加法操作（`chunk1 + chunk2`）来拼接这些状态分片，最终还原为完整的 `AIMessage` 落盘。
