---
title: "LangChain Structured Output 深入解析：强类型数据转换与实战"
date: 2026-05-11T18:29:07+08:00
slug: "langchain-structured-output-introduction"
image: ""
categories:
    - 技术
tags:
    - LangChain
draft: false
---

## <font style="color:rgb(31, 31, 31);">💡</font><font style="color:rgb(31, 31, 31);"> 一句话核心概念</font>

<font style="color:rgb(31, 31, 31);">Structured Output 模块是 LLM 与传统软件系统之间的</font><strong><font style="color:rgb(31, 31, 31);">强类型数据转换器（DTO/Serializer）</font></strong><font style="color:rgb(31, 31, 31);">。它强制大模型收起“自然语言的废话”，直接返回严格符合 Pydantic/JSON Schema 规范的对象，彻底解决了用正则表达式从不可控文本中硬抠数据的噩梦。</font>

---

## <font style="color:rgb(31, 31, 31);">常用核心 API 及类名</font>

### <font style="color:rgb(31, 31, 31);"></font><font style="color:#DF2A3F;">`response_format`</font><font style="color:rgb(31, 31, 31);"> (在 </font><font style="color:#DF2A3F;">`create_agent`</font><font style="color:rgb(31, 31, 31);"> 中的核心参数)</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：接口的“返回类型声明”。你可以直接传入一个 Pydantic </font><font style="color:rgb(68, 71, 70);">`BaseModel`</font><font style="color:rgb(31, 31, 31);"> 类，Agent 在底层会自动拦截大模型的输出，并将其反序列化为该类的实例。</font>
+ <strong><font style="color:rgb(31, 31, 31);">工程视角</font></strong><font style="color:rgb(31, 31, 31);">：这和 FastAPI 中使用 Pydantic 校验 </font><font style="color:rgb(68, 71, 70);">`Response Model`</font><font style="color:rgb(31, 31, 31);"> 的体验完全一致。</font>

<font style="color:rgb(31, 31, 31);"></font>

### <font style="color:rgb(31, 31, 31);"></font><font style="color:#DF2A3F;">`ProviderStrategy`</font><font style="color:rgb(31, 31, 31);"> (原生策略)</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：利用模型厂商（如 OpenAI、Anthropic）API 底层原生提供的结构化输出能力（如 OpenAI 的 </font><font style="color:rgb(68, 71, 70);">`response_format: {type: "json_schema"}`</font><font style="color:rgb(31, 31, 31);">）。</font>
+ <strong><font style="color:rgb(31, 31, 31);">特点</font></strong><font style="color:rgb(31, 31, 31);">：可靠性最高，解析速度最快。如果大模型原生支持，LangChain 会</font><strong><font style="color:rgb(31, 31, 31);">默认</font></strong><font style="color:rgb(31, 31, 31);">使用此策略。</font>

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 测试 ProviderStrategy 的使用，展示如何让 Agent 直接输出强类型的 Python 对象，避免了传统的字符串解析步骤。

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field


# 定义严格的输出结构 (DTO)
class UserProfile(BaseModel):
    name: str = Field(description="用户姓名")
    age: int = Field(description="用户年龄")


if __name__ == "__main__":
    # 在项目根目录下的.env文件中配置好你的 api key，或者直接在环境变量里设置
    model = init_chat_model(
        "gemini-2.5-flash", model_provider="google_genai", temperature=0
    )

    # 2. 强制 Agent 按 ProviderStrategy (原生能力) 输出
    agent = create_agent(
        model=model,
        tools=[],  # 即使没有工具也可以做结构化提取
        response_format=ProviderStrategy(UserProfile),
    )

    # 3. 触发调用
    result = agent.invoke({"messages": [("user", "南泽今年刚满28岁")]})

    # 4. 拿到的直接是强类型的 Python 对象
    parsed_data = result["structured_response"]
    print(f"解析成功 -> 姓名: {parsed_data.name}, 年龄: {parsed_data.age}")
    # 解析成功 -> 姓名: 南泽, 年龄: 28

```

### <font style="color:rgb(31, 31, 31);"></font><font style="color:#DF2A3F;">`ToolStrategy`</font><font style="color:rgb(31, 31, 31);"> (工具策略/降级策略)</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：如果使用的开源小模型或某些厂商不支持原生的 JSON 输出，</font><font style="color:rgb(68, 71, 70);">`ToolStrategy`</font><font style="color:rgb(31, 31, 31);"> 会使用一种“Hack”手段：</font><strong><font style="color:rgb(31, 31, 31);">伪造一个必须填参数的工具（Tool）</font></strong><font style="color:rgb(31, 31, 31);">，欺骗大模型去调用这个工具，从而变相拿到结构化的参数字典。</font>
+ <strong><font style="color:rgb(31, 31, 31);">核心参数</font></strong><font style="color:rgb(31, 31, 31);">：</font><font style="color:rgb(68, 71, 70);">`handle_errors=True`</font><font style="color:rgb(31, 31, 31);">。大模型填错参数时，是否开启内部重试。</font>

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 测试 ToolStrategy 的使用，展示如何在不支持 ProviderStrategy 的模型上使用降级策略来输出强类型的 Python 对象，虽然会有额外的字符串解析步骤，但依然能保证输出的结构化和类型安全。
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field


# 定义严格的输出结构 (DTO)
class UserProfile(BaseModel):
    name: str = Field(description="用户姓名")
    age: int = Field(description="用户年龄")


if __name__ == "__main__":
    # 在项目根目录下的.env文件中配置好你的 api key，或者直接在环境变量里设置
    model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)

    # 2. 强制 Agent 按 ToolStrategy (降级/工具策略) 输出
    agent = create_agent(
        model=model,
        tools=[],  # 即使没有工具也可以做结构化提取
        response_format=ToolStrategy(UserProfile),
    )

    # 3. 触发调用
    result = agent.invoke({"messages": [("user", "南泽今年刚满28岁")]})

    # 4. 拿到的直接是强类型的 Python 对象
    parsed_data = result["structured_response"]
    print(f"解析成功 -> 姓名: {parsed_data.name}, 年龄: {parsed_data.age}")
    # 解析成功 -> 姓名: 南泽, 年龄: 28

```

<font style="color:rgb(31, 31, 31);"></font>

---

## <font style="color:rgb(31, 31, 31);">文档中提到的其他高级 API / 类名</font>

### <font style="color:rgb(31, 31, 31);"></font><font style="color:rgb(68, 71, 70);">`handle_errors`</font><font style="color:rgb(31, 31, 31);"> (在 </font><font style="color:rgb(68, 71, 70);">`ToolStrategy`</font><font style="color:rgb(31, 31, 31);"> 中的重试机制)</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：大模型偶尔会产生幻觉，输出的 JSON 少了必填字段或类型不对。开启此机制后，LangChain 会在底层捕获 </font><font style="color:rgb(68, 71, 70);">`ValidationError`</font><font style="color:rgb(31, 31, 31);">，并把报错堆栈（Stack Trace）当成 Prompt 重新喂给大模型，让它自己修 Bug，而不是直接向上层抛出 500 错误。</font>
+ <strong><font style="color:rgb(31, 31, 31);">场景</font></strong><font style="color:rgb(31, 31, 31);">：极其关键的高可用防御机制。</font>

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 演示 LangChain 结构化输出工具策略（ToolStrategy），通过 Pydantic 模型验证和错误重试机制，实现模型输出的自动纠正。

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field


class Rating(BaseModel):
    score: int = Field(description="必须是 1 到 5 之间的整数", ge=1, le=5)


if __name__ == "__main__":
    model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)

    # 开启精准的异常捕获与自我修复循环
    agent = create_agent(
        model=model,
        tools=[],
        response_format=ToolStrategy(
            schema=Rating,
            handle_errors=ValueError,  # 只拦截 ValueError 并让模型重试
        ),
    )

    # 故意诱导模型犯错
    result = agent.invoke({"messages": [("user", "给这个商品打 10 分！")]})
    print("最终纠正后的结果:", result["structured_response"])
    # 最终纠正后的结果: score=5

```

### <font style="color:rgb(31, 31, 31);"></font><font style="color:rgb(68, 71, 70);">`Union`</font><font style="color:rgb(31, 31, 31);"> 联合类型解析（配合 </font><font style="color:rgb(31, 31, 31);">`ToolStrategy`</font>使用<font style="color:rgb(31, 31, 31);">）</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：支持让模型根据上下文，“智能”决定返回哪种数据结构。这在后端实现</font><u><font style="color:rgb(31, 31, 31);">复杂意图路由</font></u><font style="color:rgb(31, 31, 31);">（Intent Routing）时非常有用。</font>

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 演示 LangChain 结构化输出中使用 Union 类型进行多意图解析，自动区分订单查询和退款申请并返回对应 Pydantic 对象。

from typing import Union

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field


# 定义意图 A 的数据结构：查询订单
class OrderQuery(BaseModel):
    """当用户想要查询订单、物流状态时使用此结构"""

    order_id: str = Field(description="订单号，通常以 ORD 开头")


# 定义意图 B 的数据结构：售后退款
class RefundRequest(BaseModel):
    """当用户抱怨商品质量、要求退货退款时使用此结构"""

    order_id: str = Field(description="需要退款的订单号")
    reason: str = Field(description="用户描述的退款原因，需精简概括")


if __name__ == "__main__":
    # 由于涉及到复杂的函数选择，推荐使用 GPT-4o-mini 或 DeepSeek-Chat
    model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)

    # 3. 核心：使用 Union 联合类型进行强约束
    agent = create_agent(
        model=model,
        tools=[],
        # 强制模型在 OrderQuery 和 RefundRequest 中二选一
        response_format=ToolStrategy(Union[OrderQuery, RefundRequest]),
    )

    print("======================================")
    print(">>> 场景 1：用户意图为【查询】")
    res1 = agent.invoke({"messages": [("user", "帮我查一下订单 ORD-9988 到哪了？")]})

    parsed1 = res1["structured_response"]
    # 你会发现返回的对象严格变成了 OrderQuery 类的实例
    print(f"[底层对象类型]: {type(parsed1).__name__}")
    if isinstance(parsed1, OrderQuery):
        print(f"[业务路由]: 进入查库逻辑 -> 目标订单: {parsed1.order_id}")

    print("\n======================================")
    print(">>> 场景 2：用户意图为【退款】")
    res2 = agent.invoke(
        {
            "messages": [
                (
                    "user",
                    "我昨天买的那个玻璃杯，今天收到货发现全碎了，订单号是 ORD-1122，赶紧给我退钱！",
                )
            ]
        }
    )

    parsed2 = res2["structured_response"]
    # 你会发现返回的对象严格变成了 RefundRequest 类的实例
    print(f"[底层对象类型]: {type(parsed2).__name__}")
    if isinstance(parsed2, RefundRequest):
        print(f"[业务路由]: 进入售后工单逻辑 -> 目标订单: {parsed2.order_id}")
        print(f"[提取原因]: {parsed2.reason}")


# 输出：
# ======================================
# >>> 场景 1：用户意图为【查询】
# [底层对象类型]: OrderQuery
# [业务路由]: 进入查库逻辑 -> 目标订单: ORD-9988

# ======================================
# >>> 场景 2：用户意图为【退款】
# [底层对象类型]: RefundRequest
# [业务路由]: 进入售后工单逻辑 -> 目标订单: ORD-1122
# [提取原因]: 收到的玻璃杯全碎了，商品破损

```

---

## <font style="color:rgb(31, 31, 31);">极简代码脚手架</font>

<font style="color:rgb(31, 31, 31);">这是将自然语言转化为后端结构化业务数据最干净的闭环。</font>

<strong><font style="color:rgb(31, 31, 31);">structured_meeting_notes_extraction.py：</font></strong>

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 演示使用 LangChain 结构化输出直接将非结构化会议纪要提取为 Pydantic 模型，并将结果用于后续业务处理。
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field


# 定义期望的数据提取 Schema
class MeetingAction(BaseModel):
    """从会议记录中提取的待办事项"""

    task: str = Field(description="具体的任务描述")
    assignee: str = Field(description="任务负责人")
    priority: str = Field(description="优先级：高、中、低")


if __name__ == "__main__":
    # 2. 初始化模型
    model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)

    # 3. 创建 Agent，直接传入 Pydantic 类（底层会自动选择 ProviderStrategy）
    agent = create_agent(model=model, tools=[], response_format=MeetingAction)

    # 4. 喂入非结构化的“脏数据”
    raw_text = "今天的周会总结一下：小李你需要尽快把那个并发超时的Bug修掉，这个很紧急。然后文档的事情就不着急了。"
    print(f"输入文本: {raw_text}\n")

    response = agent.invoke({"messages": [("user", raw_text)]})

    # 5. 提取强类型结果，直接对接到后续业务逻辑
    action_item = response["structured_response"]
    print(">>> 结构化提取成功 <<<")
    print(f"负责人: {action_item.assignee}")
    print(f"任务项: {action_item.task}")
    print(f"优先级: {action_item.priority}")
    # 接下来可以直接 ORM 入库： db.session.add(Task(**action_item.model_dump()))

```

**输出结果：**

```powershell
输入文本: 今天的周会总结一下：小李你需要尽快把那个并发超时的Bug修掉，这个很紧急。然后文档的事情就不着急了。

>>> 结构化提取成功 <<<
负责人: 小李
任务项: 修复并发超时的Bug
优先级: 高
```

---

## <font style="color:rgb(31, 31, 31);">常见踩坑与高频面试点（后端视角）</font>

<font style="color:rgb(31, 31, 31);">如果在面试中聊到结构化提取，掌握以下几点能极大展现你的工程深度：</font>

### <font style="color:rgb(31, 31, 31);">高频面试点：</font><font style="color:#DF2A3F;">`ProviderStrategy`</font><font style="color:#DF2A3F;"> vs </font><font style="color:#DF2A3F;">`ToolStrategy`</font><font style="color:#DF2A3F;"> 的底层区别是什么？</font>

+ <strong><font style="color:rgb(31, 31, 31);">考察点</font></strong><font style="color:rgb(31, 31, 31);">：对模型 API 底层协议的理解。</font>
+ <strong><font style="color:rgb(31, 31, 31);">高分回答</font></strong><font style="color:rgb(31, 31, 31);">：</font><font style="color:rgb(68, 71, 70);">`ProviderStrategy`</font><font style="color:rgb(31, 31, 31);"> 调用的是厂商提供的原生 JSON Schema 强制约束模式（如 OpenAI 的 </font><font style="color:rgb(68, 71, 70);">`strict: true`</font><font style="color:rgb(31, 31, 31);">），解析是在模型推理层完成的，Token 生成阶段就不会产生非法字符；而 </font><font style="color:rgb(68, 71, 70);">`ToolStrategy`</font><font style="color:rgb(31, 31, 31);"> 是一种妥协方案，它实际上是在 Prompt 里塞入了一个虚拟的函数定义，让模型生成一段包含 JSON 参数的 </font><font style="color:rgb(68, 71, 70);">`Function Call`</font><font style="color:rgb(31, 31, 31);"> 文本，然后再由 LangChain 拦截解析。原生策略速度更快、准度更高、Token 开销更小。</font>

<font style="color:rgb(31, 31, 31);"></font>

### <font style="color:rgb(31, 31, 31);">实战踩坑点：Schema 过于复杂导致的幻觉崩塌</font>

+ <strong><font style="color:rgb(31, 31, 31);">现象</font></strong><font style="color:rgb(31, 31, 31);">：为了省事，直接把一个包含十几层嵌套、几十个字段的庞大 </font><font style="color:rgb(68, 71, 70);">`BaseModel`</font><font style="color:rgb(31, 31, 31);"> 塞给 </font><font style="color:rgb(68, 71, 70);">`response_format`</font><font style="color:rgb(31, 31, 31);">。结果大模型频繁报 </font><font style="color:rgb(68, 71, 70);">`ValidationError`</font><font style="color:rgb(31, 31, 31);">，甚至死循环。</font>
+ <strong><font style="color:rgb(31, 31, 31);">对策</font></strong><font style="color:rgb(31, 31, 31);">：大模型不是全能的解析器。嵌套越深，大模型的注意力（Attention）越容易分散。</font><strong><font style="color:rgb(31, 31, 31);">最佳实践是拆分解耦</font></strong><font style="color:rgb(31, 31, 31);">：先用一个 Agent 提取顶层意图，再将具体的复杂字段交给下游更垂直的 Agent 去提取。Schema 定义必须保持“扁平”且字段描述（</font><font style="color:rgb(68, 71, 70);">`description`</font><font style="color:rgb(31, 31, 31);">）务必清晰。</font>

<font style="color:rgb(31, 31, 31);"></font>

### <font style="color:rgb(31, 31, 31);">架构设计考点：</font><font style="color:#DF2A3F;">陷入重试死循环（Infinite Retry Loop）</font>

+ <strong><font style="color:rgb(31, 31, 31);">现象</font></strong><font style="color:rgb(31, 31, 31);">：开启了 </font><font style="color:rgb(68, 71, 70);">`handle_errors=True`</font><font style="color:rgb(31, 31, 31);">，大模型遇到 </font><font style="color:rgb(68, 71, 70);">`ValidationError`</font><font style="color:rgb(31, 31, 31);"> 开始自我修复，但因为它的逻辑推理能力较弱，连续修了 10 次还是错的，导致接口长时间阻塞。</font>
+ <strong><font style="color:rgb(31, 31, 31);">对策</font></strong><font style="color:rgb(31, 31, 31);">：绝不能放任框架无限重试。在生产环境中，必须在构建 LangGraph 的配置中设置严格的 </font><font style="color:#DF2A3F;">`recursion_limit`</font><font style="color:rgb(31, 31, 31);">（比如最多重试 3 次）。达到阈值后，抛出特定的 </font><font style="color:rgb(68, 71, 70);">`MultipleStructuredOutputsError`</font><font style="color:rgb(31, 31, 31);">（多重结构化输出错误） 异常，并在后端接入人工客服接管或返回默认的兜底配置。</font>
