---
title: "LangChain 混合流式机制与大模型推理块拦截"
date: 2026-06-04T17:16:04+08:00
slug: "langchain-mixed-streaming-and-reasoning-interception"
image: ""
categories:
    - 技术
tags:
    - LangChain
    - Streaming
draft: false
---

> [Streaming - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/streaming)
>

**一句话总结：LangChain 的 Streaming 机制通过提供多模式（如 Token 增量、状态更新、自定义事件）的流式生成器，实现了大模型推理、思维链（CoT）、工具执行生命周期以及多智能体流转的极低延迟实时输出，是构建具备高响应性与卓越交互体验的 AI Agent 前端应用的核心基础。**

---

## 核心概念与常用 API 解析

在 Agent 的执行过程中，计算与网络请求往往耗时较长。LangGraph 底层实现了一套事件驱动的流式系统，允许开发者精准订阅不同粒度的运行时状态。

+ <strong>`stream()`</strong><strong>与</strong>**`astream()`**  
执行图编译后状态机（Agent）的流式调用方法。支持同步与异步两种模式。
+ **参数 **<strong>`stream_mode`</strong>** (流模式)**  
控制底层引擎向外派发事件的维度，可通过列表形式传入多个模式以实现复合流订阅：
  + <strong>"messages"</strong>：<u>Token 级别消息流</u>。实时产出 `AIMessageChunk`，包含大模型逐字生成的<strong>文本增量</strong>、<strong>工具调用参数增量</strong>以及<strong>高级模型的推理增量</strong>。
  + <strong>"updates"</strong>：<u>Agent 步进式状态流</u>。在状态机的每一个 Node（如 llm 节点或 tools 节点）执行完毕后，发出完整的状态变更快照。
  + <strong>"custom"</strong>：<u>自定义事件流</u>。允许在业务代码（如长耗时 Tool 内部）向外部通道抛出进度标识。
+ <strong>参数</strong>**`version="v2"`**  
LangGraph 推荐的新版流式输出协议。启用后，底层产出的每一个事件都会被包裹为统一的 `StreamPart` 字典，严格包含 `type`（流模式）、`ns`（命名空间）和 `data`（实际负载数据），极大简化了下游对不同数据流的解析逻辑。
+ **`get_stream_writer()`**  
用于在工具（Tool）函数内部获取底层数据流的写入句柄。<u>使得工具能够在</u><strong><u>执行期间实时</u></strong><u>向调用方发送中间状态。</u>

---

## 周边与扩展 API 梳理

结合文档内提及的超链接及相关进阶特性，以下组件在复杂的流式工作流中具有关键作用：

+ **Event Streaming (stream_events, version="v3")**  
文档开篇作为最佳实践推荐的高级 API。相比底层裸调 `stream()`，它提供了强类型的<strong>数据投影</strong>（Typed Projections）。对于独立消费 messages、tool_calls 或 subgraphs 等事件，提供更为细粒度且类型安全的迭代器，<u>避免手动解析混合流数据块</u>。
+ **内容块解析 (content_blocks)**  
无论模型提供商的底层 API 如何各异，<u>LangChain 会将流式返回的特征统一格式化为标准内容块</u>。例如在处理包含深思能力的模型时，流经的 `AIMessageChunk` 内部会将普通文本标记为 `{"type": "text"}`，将思维链标记为 `{"type": "reasoning"}`。
+ <strong>多智能体流式追踪 (</strong><strong>`subgraphs=True`</strong>**)**  
当主 Agent 内部通过工具嵌套调用了其他子 Agent 时，通过开启此参数并结合 `create_agent` 时赋予的 `name` 属性（反映在元数据 lc_agent_name 中），可以在全局流中区分并捕获具体是由哪一个智能体产生的输出。
+ **人机协同流式挂起 (Human-in-the-loop 与 Command)**  
当图状态机在流式输出中遭遇中断配置（如等待用户审批工具调用）时，会在 updates 模式中暴露出 __`interrupt`__ 事件。开发者处理完审批决策后，通过传入 `Command(resume=...)` 至 `stream()` 中即可直接恢复执行流。
+ <strong>禁用特定流输出 (</strong><strong>`streaming=False`</strong>**)**  
在实例化具体 ChatModel 时可配置。<u>用于多 Agent 架构中屏蔽非直接交互模型的输出流</u>，控制最终发送给前端事件通道的噪音。

---

## 工程化代码落地示例

以下代码展示了如何开启 `version="v2"` 的混合流模式，提取模型的打字机 Token，剥离思维链（Reasoning）信息，同时捕捉长耗时工具中发出的自定义进度信号。

```python {title="agent_streaming_pipeline.py"}
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 演示混合模式的 Agent 流式输出，通过状态机优化 Token、Reasoning 及工具事件的终端排版
# requirements   : pip install -U langchain langchain-deepseek langgraph

import time

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessageChunk, ToolMessage
from langchain_core.tools import tool
from langgraph.config import get_stream_writer


@tool
def process_data(target: str) -> str:
    """处理并分析目标数据。"""
    writer = get_stream_writer()

    writer(f"开始连接目标数据库提取 [{target}]...")
    time.sleep(1)  # 模拟网络 IO
    writer(f"成功提取 [{target}]，正在进行数据清洗...")
    time.sleep(1)  # 模拟数据处理

    return f"针对 {target} 的数据处理完成，状态为：正常。"


def main() -> None:

    model = init_chat_model(
        "deepseek-reasoner", model_provider="deepseek", temperature=0
    )

    agent = create_agent(
        model=model,
        tools=[process_data],
    )

    print("--- 启动多模式混合流式订阅 ---\n")

    stream_iterator = agent.stream(
        {
            "messages": [
                {"role": "user", "content": "请分析一下 '2026年Q1报表' 的数据。"}
            ]
        },
        stream_mode=["messages", "updates", "custom"],
        version="v2",
    )

    # ==========================================
    # 核心优化：引入渲染状态指针，优雅处理多通道流的交织
    # ==========================================
    current_phase = None  # 可选值: "reasoning", "text", None

    for chunk in stream_iterator:
        chunk_type = chunk["type"]
        chunk_data = chunk["data"]

        if chunk_type == "messages":
            token, metadata = chunk_data
            if isinstance(token, AIMessageChunk):
                for block in token.content_blocks:
                    if block["type"] == "reasoning":
                        # 状态切换检测：如果刚刚不在推理状态，则打印表头并切换状态
                        if current_phase != "reasoning":
                            if current_phase == "text":
                                print("\n")  # 换行收尾之前的文本
                            print("\033[90m[AI 思考过程]:\n", end="", flush=True)
                            current_phase = "reasoning"

                        # 纯净输出推理过程
                        print(block["reasoning"], end="", flush=True)

                    elif block["type"] == "text":
                        # 状态切换检测：如果刚刚在推理状态，先关闭灰色控制符
                        if current_phase != "text":
                            if current_phase == "reasoning":
                                print("\033[0m\n", end="", flush=True)
                            print("\n[最终回复]:\n", end="", flush=True)
                            current_phase = "text"

                        # 纯净输出正文内容
                        print(block["text"], end="", flush=True)

        elif chunk_type == "custom":
            # 遇到工具插入时，强行中断当前的渲染状态
            if current_phase == "reasoning":
                print("\033[0m\n")
            elif current_phase == "text":
                print("\n")
            current_phase = None

            print(f"[自定义工具进度] {chunk_data}")

        elif chunk_type == "updates":
            for source, update in chunk_data.items():
                if source == "tools":
                    # 遇到状态更新时，强行中断当前的渲染状态
                    if current_phase == "reasoning":
                        print("\033[0m\n")
                    elif current_phase == "text":
                        print("\n")
                    current_phase = None

                    last_msg = update["messages"][-1]
                    if isinstance(last_msg, ToolMessage):
                        print(
                            f"\n[节点状态] 工具调用完毕，原始响应: {last_msg.content}\n"
                        )

    # 循环彻底结束后，兜底关闭可能遗留的颜色控制符
    if current_phase == "reasoning":
        print("\033[0m")

    print("\n\n--- 交互结束 ---")


if __name__ == "__main__":
    main()

```

**输出结果：**

```powershell
--- 启动多模式混合流式订阅 ---

[AI 思考过程]:
用户要求分析 '2026年Q1报表' 的数据，我需要调用 process_data 工具来处理这个目标数据。

[最终回复]:
好的，我来为您分析 '2026年Q1报表' 的数据。

[自定义工具进度] 开始连接目标数据库提取 [2026年Q1报表]...
[自定义工具进度] 成功提取 [2026年Q1报表]，正在进行数据清洗...

[节点状态] 工具调用完毕，原始响应: 针对 2026年Q1报表 的数据处理完成，状态为：正常。

[AI 思考过程]:
The process_data function was called with the target "2026年Q1报表" and it returned a status of "正常" (normal/ok). However, it didn't return any actual data or detailed analysis results. Let me provide a response based on what I know.

Actually, looking at the function description, it says "处理并分析目标数据" (process and analyze target data), and it returned that the status is "正常". This means the data processing was completed successfully. But I don't have the actual content of the report to provide detailed analysis. Let me provide a general response.

[最终回复]:
## 年Q1报表 数据分析报告

### 📊 处理结果概览

| 项目 | 状态 |
|------|------|
| 数据目标 | `2026年Q1报表` |
| 处理状态 | ✅ **正常** |
| 数据分析 | 已完成 |

### ✅ 分析结论

经过系统处理，<strong>2026年Q1报表</strong>的数据分析已顺利完成，整体状态显示为 <strong>正常</strong>。

### 📋 建议

如果您需要进一步查看具体的数据明细、图表趋势或关键指标的详细对比（如营收、利润、增长率等），请提供以下补充信息，我可以帮助您进行更深入的分析：

1. <strong>报表的具体字段</strong>（如收入、成本、利润等）
2. <strong>对比基准</strong>（如与2025年Q4环比 / 与2025年Q1同比）
3. <strong>关注的业务维度</strong>（地区、产品线、部门等）

请随时告诉我您的具体需求！

--- 交互结束 ---
```

**说明：**

这段代码通过维护一个全局的 `current_phase` 变量，完美解决了<strong>“流式数据到达的随机性”与“UI 展示的一致性”</strong>之间的矛盾。

在企业级 AI Agent 前端对接中（例如使用 Vue/React 接收 SSE 流），这种 **State Machine Rendering（状态机驱动渲染）** 思想是必考的架构能力。大模型随时可能思考，工具随时可能吐出进度条，后端或消费端必须通过状态变量将这些“事件碎片”平滑地包裹进不同的 UI 容器（如“折叠思考框”、“工具进度组件”、“Markdown 渲染区”）中。

---

## 常见踩坑与高频面试点

在复杂 Agent 系统的监控与流式前端对接中，Streaming 机制是考察候选人对大模型底层协议理解深度的绝佳切入点。

### 高频考点 1：如何同时实现高响应的 Token 逐字显示与高可靠的结构化工具解析？

+ <strong>面试官提问</strong>：“前端要求<u>打字机效果</u>，所以我们必须<u>截获 Token 块</u>；但大模型吐出的工具调用参数（JSON）经常是<u>碎片化</u>的。如何兼顾流式展示与稳定的工具参数提取？”
+ <strong>满分回答</strong>：单纯依靠解析 `stream_mode="messages"` 中的 `tool_call_chunks` 进行字符串拼接是非常容易出错的。最佳的工程实践是<strong>同时挂载多模式流</strong>：即 `stream_mode=["messages", "updates"]`。在 `messages` 流中提取 `AIMessageChunk.text` 发送给前端实现打字机效果；而对于工具调用，直接忽略碎片的解析，转而监听 `updates` 流。当大模型的推理 Node 执行完毕并触发状态收敛时，updates 流会提供一个完整的 `AIMessage`，其中包含了经过底层强校验并组装完毕的 `tool_calls` 对象，确保业务逻辑读取 100% 可靠。

### 高频考点 2：包含深度思考（CoT）模型的异构流解析

+ <strong>面试官提问</strong>：“随着带有深度思考能力的模型普及，如果在流式通道中不加干预，模型的内心独白和最终回答混杂在一起。如何在数据管道层将它们分离展示？”
+ <strong>满分回答</strong>：应当基于统一的 `content_blocks` 规范进行分离。在迭代 `AIMessageChunk` 时，拦截并解析其中的块结构类型。过滤 `block["type"] == "reasoning"` 将其独立分发至前端的<u>“思考链”组</u>件通道；过滤 `block["type"] == "text"` 分发至<u>最终回复通道</u>。这种面向<u>块类型</u>（Block-Type）的解耦解析，彻底消除了对正则匹配或特定厂商 JSON Schema 的依赖。

### 常见踩坑 1：工具内部上下文执行作用域脱离

+ <strong>现象与痛点</strong>：为了优化体验，开发者在 Tool 中加入了 `get_stream_writer()` <u>推送进度</u>。但在编写单元测试直接调用该工具函数，或在非 LangGraph 引擎接管的环境中运行该函数时，程序抛出异常，提示上下文缺失或找不到执行树。
+ <strong>对策</strong>：`get_stream_writer` <u>深度依赖底层图计算的状态机运行上下文</u>。在脱离图执行环境时，必须<u>加入错误捕获降级逻辑</u>，或通过专门的 Mock 上下文执行单元测试。

### 常见踩坑 2：不同版本流式协议导致的类型拆包错误

+ <strong>现象与痛点</strong>：在重构流式解析管道时，原有的 for mode, chunk in agent.stream(...) 循环突然抛出 `ValueError`。
+ <strong>对策</strong>：必须<u>明确版本约束</u>。在旧版本默认行为中，使用多个 stream_mode 会产出 (mode, data) 的元组；而在推荐的生产级规范中，应强制声明 `version="v2"`，这会改变底层迭代器的<u>产出格式</u>，使其统一返回带有 <u>type 鉴别键</u>的字典，从根源上消除动态解包带来的隐式类型报错。

---

## Streaming (v2) 与 Event Streaming (v3) 的区别与应用场景

在 LangChain/LangGraph 的生态演进中，开发者最容易混淆的就是底层的 `stream()` API 与高层的 `stream_events()` API。理解两者的设计初衷与边界，是高频的架构面试考点。

### 核心区别对比

| **维度** | <strong>stream()</strong>******(Streaming)** | <strong>stream_events()</strong>******(Event Streaming)** |
| :---: | --- | --- |
| **官方推荐版本** | `version="v2"` | `version="v3"` |
| **定位** | <strong>底层基础设施</strong>。暴露的是图状态机最原始的执行快照与 LLM 生成的 Token 碎片。 | <strong>前端/应用层首选</strong>。对底层碎片进行了聚合抽象，专门为大模型的多通道通信打造的强类型投影。 |
| **数据结构** | 混合流。开发者需要根据 `chunk["type"]` (如 `messages`, `updates`, `custom`) 手动编写大量 `if-else` 解包数据。 | 投影流。框架剥离出了 `.messages`, `.tool_calls`, `.subgraphs` 等独立通道，可通过 `interleave` 交织消费，支持面向对象属性访问。 |
| **多模态/推理块支持** | 需要从 `AIMessageChunk` 中手动遍历 `content_blocks` 拆分 `Reasoning` 和 `Text`。 | 同样利用 `content_blocks`，但在事件包裹和生命周期管理上更为清晰。 |
| **多智能体 (Multi-Agent) 追踪** | <strong>极难</strong>。所有子 Agent 的事件全部混入主 Agent，只能通过深度解包 `metadata.get("lc_agent_name")` 肉眼区分。 | <strong>开箱即用</strong>。通过独立的 `stream.subgraphs` 通道，可以像遍历树一样精准拦截并追踪任意子 Agent 的生命周期。 |

### 架构选型与应用场景

+ **场景 1：构建纯后端的数据处理流（选择 Streaming v2）**  
如果你的 Agent 只是一个后台异步任务（例如：定时生成财报摘要存入数据库，中间调了几个爬虫工具），不需要向用户展示酷炫的“打字机”和“正在思考” UI，那么直接调用 `stream(stream_mode="updates")` 获取节点执行完毕后的状态快照是最轻量、性能最好的做法。
+ **场景 2：构建现代化 AI 前端界面（选择 Event Streaming v3）**  
这是 <strong>90% 以上交互式 Agent 的首选</strong>。如果你的系统需要对接 Web/App 前端（如基于 React 的 SSE 通道），并且前端要求展示独立的“深度思考折叠面板”、“正在查询数据库的 Loading 状态”，以及“多 Agent 协作时显示哪位专家正在发言”，那么必须使用 `stream_events(version="v3")`，利用它提供的解耦通道进行独立分发。

**面试金句总结：**  
“streaming.md (v2) 是底层的泥瓦匠，揭示了状态机快照与 Token 碎片的生成原理；event-streaming.md (v3) 是高层的精装修，它利用强类型投影彻底解耦了模型推理、工具执行与子图流转，是我们构建企业级响应式 AI 客户端的唯一标配 API。”
