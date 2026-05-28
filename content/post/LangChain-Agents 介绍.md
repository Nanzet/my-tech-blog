---
title: "LangChain Agents 介绍"
date: 2026-05-07T22:02:41+08:00
slug: "langchain-agents-introduction"
image: ""
categories:
    -  技术
tags:
    - LangChain
    - Agents
draft: false
---
## 一句话核心概念

`Agents` 模块是一个内置了 **ReAct（推理+行动）死循环逻辑的状态机引擎**。
它解决了大模型只能“纸上谈兵”的痛点：通过框架底层的图（LangGraph）机制，让模型自主思考、调用外部业务 API（工具）、观察结果，并反复纠错，直到得出最终答案。

---

## 常用核心 API 及类名

### `create_agent()`

+ **作用**：Agent 的“核心组装工厂”。它把大脑（模型）、手脚（工具）、规矩（系统提示词）和短期记忆封装成一个可运行的图（Graph）实例。
+ **核心参数**：
  + `model`: 已经初始化好的模型实例（或直接传标识字符串如 `"openai:gpt-4o"`）。
  + `tools`: Agent 可以调用的 Python 函数列表。
  + `system_prompt`: 定义 Agent 人设和行为准则的指令。
  + `middleware`: 中间件列表（资深后端最爱，用于全局拦截和修改状态）。

```python
from langchain.agents import create_agent

# 组装一个最基础的 Agent
agent = create_agent(
    model="openai:gpt-4o", 
    tools=[search_db], # 传入你的后端函数
    system_prompt="你是一个资深的 DBA，请用精炼的语言回答。"
)
```

### `.invoke()`与 `.stream()`

+ **作用**：Agent 的“启动按钮”。每次调用本质上是向 Agent 的内部状态（State）中追加一条新消息，并触发其内部的 ReAct 循环。
+ **说明**：`invoke` 会一直阻塞直到 Agent 彻底完成任务；`stream` 会以流式返回中间的思考过程和工具调用进度。

```python
import os
from langchain.agents import create_agent
from langchain.tools import tool

# 1. 定义后端函数 (工具)
@tool
def search_db(query: str) -> str:
    """模拟查询数据库"""
    print(f"\n[后端执行] 正在查询数据库，关键字: {query}...")
    return "订单 12345 状态为：已发货"

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx" # 替换为真实 Key
  
    # 2. 组装一个最基础的 Agent
    agent = create_agent(
        model="gpt-4o-mini", 
        tools=[search_db], 
        system_prompt="你是一个资深的 DBA，请用精炼的语言回答。"
    )

    print("=== 测试 1: .invoke() 同步阻塞调用 ===")
    # invoke 会在底层默默跑完“思考->调工具->拿到结果->总结”的完整 ReAct 循环
    result = agent.invoke({
        "messages": [{"role": "user", "content": "帮我查一下订单号 12345 的状态"}]
    })
    print(f"\n[最终回复]: {result['messages'][-1].content}")
  
    print("\n\n=== 测试 2: .stream() 流式进度追踪 ===")
    # stream 能够让你看到 Agent 每一步都在干嘛 (适合给前端做实时 Loading 动画)
    for chunk in agent.stream({"messages": [{"role": "user", "content": "再次确认 12345 的状态"}]}):
        latest_msg = chunk["messages"][-1]
        if latest_msg.type == "ai" and latest_msg.tool_calls:
            print(f"[流式进度] 模型决定调用工具: {latest_msg.tool_calls[0]['name']}")
        elif latest_msg.type == "tool":
            print(f"[流式进度] 工具执行完毕，结果: {latest_msg.content}")
```

---

## 文档中提到的其他高级 API / 类名

### `@tool` (装饰器)

+ **作用**：将普通的后端 Python 函数，注册为大模型能够理解和调用的工具。它会自动提取函数的 Docstring 和类型注解（Type Hints）作为给大模型看的 API 文档。

```python
from langchain.tools import tool

@tool
def get_order_status(order_id: str) -> str:
    """根据订单ID查询订单当前状态"""
    return "已发货" # 你的真实业务逻辑
```

### `AgentMiddleware` 与各种 `@wrap_xxx` 装饰器

+ **作用**：强大的扩展点。这和后端的网关拦截器一模一样，让你能在**把请求发给模型前**或**工具报错时**进行“暗箱操作”。

#### `@wrap_model_call`：模型调用拦截器（动态鉴权示例）

**大白话解释**：它拦截的是“把请求发给大模型”的这个动作。在请求发出去之前，或者响应拿回来之后，你可以对数据做手脚。

**后端对标概念**：API 网关拦截器、动态路由（Dynamic Routing）、ACL 权限控制。

**核心应用场景**：

+ **动态路由（降本增效）**：判断当前对话长度，如果很简单，就把请求拦截下来，把目标模型替换成便宜的 `gpt-4o-mini`；如果很复杂，替换成 `gpt-4o`。
+ **动态工具鉴权（AuthZ）**：在发给模型前，检查当前上下文中的用户信息。如果是普通用户，就把 `delete_database` 这个工具从可用列表中剔除，从源头上防止大模型越权。

```python
import os
from typing import TypedDict
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.agents.middleware import wrap_model_call, ModelRequest

# 定义状态：包含权限标识
class AuthState(TypedDict):
    messages: list
    is_authenticated: bool

@tool
def public_search() -> str:
    """公开搜索工具"""
    return "公开数据：今日天气晴朗"

@tool
def delete_database() -> str:
    """高危操作：删除核心数据库"""
    return "数据库已清空！"

@wrap_model_call
def auth_filter(request: ModelRequest, handler):
    """权限拦截器：未登录用户只能用 public 工具"""
    is_auth = request.state.get("is_authenticated", False)
  
    if not is_auth:
        print("\n[网关拦截] 用户未登录，剔除 delete_database 工具！")
        # 核心：动态修改（Override）发给模型的请求，只保留安全工具
        safe_tools = [t for t in request.tools if t.name == "public_search"]
        request = request.override(tools=safe_tools)
    else:
        print("\n[网关放行] 用户已登录 (Admin)，允许使用所有工具。")
    
    return handler(request)

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx"
    agent = create_agent(
        model="gpt-4o-mini",
        tools=[public_search, delete_database],
        middleware=[auth_filter],
        state_schema=AuthState
    )

    print(">>> 模拟黑客攻击 (未登录状态):")
    res1 = agent.invoke({"messages": [("user", "帮我执行 delete_database")], "is_authenticated": False})
    print("模型回复:", res1["messages"][-1].content) # 模型会说不知道这个工具或拒绝执行

    print("\n>>> 模拟管理员操作 (已登录状态):")
    res2 = agent.invoke({"messages": [("user", "帮我执行 delete_database")], "is_authenticated": True})
    print("模型回复:", res2["messages"][-1].content)
```

#### `@wrap_tool_call`：工具执行拦截器（全局异常兜底）

**大白话解释**：它拦截的是“实际执行 Python 函数”的这个动作。当大模型决定调用某个工具时，在代码真正执行前和执行后触发。

**后端对标概念**：全局异常处理（Global Exception Handler）、服务降级（Fallback）、APM 埋点。

**核心应用场景**：

+ **全局错误兜底（最重要）**：生产环境中，后端工具随时可能抛出 `Timeout` 或 `KeyError`。如果没有它，Agent 进程直接崩溃。加上它，你可以 `try-catch` 捕获异常，并伪装成工具正常的返回信息（如“执行失败，错误原因是XXX，请换个参数重试”），将异常“喂”回给大模型，让它触发 ReAct 循环进行**自我纠错**。
+ **日志与审计**：拦截所有的工具入参和出参，打 Log 入库，用于安全审计。

```python
import os
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

@tool
def fetch_remote_data() -> str:
    """拉取远程核心数据"""
    # 模拟真实业务中的网络超时或接口挂掉
    raise TimeoutError("核心接口 504 Gateway Timeout")

@wrap_tool_call
def handle_tool_errors(request, handler):
    """全局工具异常处理器"""
    try:
        # 放行：尝试执行实际的工具函数
        return handler(request)
    except Exception as e:
        print(f"\n[AOP 异常捕获] 捕捉到工具报错: {e}")
        # 拦截异常：不抛出，而是转为一个明确的错误消息返回给大模型
        return ToolMessage(
            content=f"【系统拦截】工具调用失败！请换种方式或向用户致歉。错误详情: {str(e)}",
            tool_call_id=request.tool_call["id"]
        )

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx"
    agent = create_agent(
        model="gpt-4o-mini",
        tools=[fetch_remote_data],
        middleware=[handle_tool_errors]
    )

    # 模型会尝试调用工具 -> 触发异常 -> 被中间件捕获 -> 模型收到报错并优雅回复
    res = agent.invoke({"messages": [("user", "帮我拉取一下最新的远程数据")]})
    print("\n最终模型回复:", res["messages"][-1].content)
```

#### `@dynamic_prompt`：动态提示词注入器

**大白话解释**：它是专门用来在运行时“捏脸”的。在请求发给模型前，动态生成一条专属的 System Prompt（系统提示词）。

**后端对标概念**：上下文感知的配置注入。

**核心应用场景**：

+ **多租户/个性化人设**：电商客服系统中，如果检测到进来的用户是 VIP，动态把 Prompt 加上“你是一个尊贵的专属管家，语气要极度客气”；如果是普通用户，设为“你是一个高效的客服”。
+ **注入时效性上下文**：在 Prompt 中动态拼接上当前的服务器时间、用户的实时地理位置等。

```python
import os
from typing import TypedDict
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.agents.middleware import dynamic_prompt, ModelRequest

class Context(TypedDict):
    user_role: str

@tool
def get_time() -> str:
    """获取时间"""
    return "12:00"

@dynamic_prompt
def role_based_prompt(request: ModelRequest) -> str:
    """根据运行时上下文动态生成人设"""
    user_role = request.runtime.context.get("user_role", "user")
    base_prompt = "你是一个代码助手。"
  
    if user_role == "junior":
        return base_prompt + "请用最简单的大白话解释，不要用专业术语，多鼓励对方。"
    elif user_role == "senior":
        return base_prompt + "请极其严厉、极简，只输出底层原理，不需要废话。"
    return base_prompt

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx"
    agent = create_agent(
        model="gpt-4o-mini",
        tools=[get_time],
        middleware=[role_based_prompt],
        context_schema=Context
    )

    print(">>> 新手模式提问:")
    res_junior = agent.invoke({"messages": [("user", "什么是多线程？")]}, context={"user_role": "junior"})
    print(res_junior["messages"][-1].content)

    print("\n>>> 大佬模式提问:")
    res_senior = agent.invoke({"messages": [("user", "什么是多线程？")]}, context={"user_role": "senior"})
    print(res_senior["messages"][-1].content)
```

---

### `AgentState` 与 `TypedDict`

+ **作用**：Agent 的“内存条”。除了原生的聊天记录（messages），你可以继承 `AgentState` 来存储自定义的会话上下文（比如用户的偏好、当前的权限）。

```python
from langchain.agents import AgentState

# 定义包含额外上下文的状态
class CustomState(AgentState):
    user_role: str

agent = create_agent(model, tools, state_schema=CustomState)
```

#### `TypedDict`是什么？

+ `TypedDict` 就是给 Python 原生字典（`dict`）穿上了一件“静态类型声明”的外衣。解决原生字典“内部结构是黑盒、键名容易拼写错误、IDE 无法代码补全”的痛点。

```python
from typing import TypedDict

# 定义字典的形状（键的名称和对应值的类型）
class UserDict(TypedDict):
    name: str
    age: int

def process_user(user: UserDict):
    # 优势 1：IDE 会自动补全 user["name"]
    # 优势 2：静态类型检查（如果写错键名，IDE 会标红）
    print(f"姓名: {user['name']}, 明年年龄: {user['age'] + 1}")

if __name__ == "__main__":
    # 实例化：本质上还是一个纯粹的 Python 字典，运行时零开销
    my_user: UserDict = {"name": "Alice", "age": 30}
    process_user(my_user)
```

##### **高频面试点：**`TypedDict` **vs** `Pydantic BaseModel`

| **特性**         | **TypedDict**                                                                                                                                                                                                                                               | **Pydantic BaseModel**                                                                                                                                                                        |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **运行时本质**   | **纯粹的 Python 原生字典 (`dict`)**                                                                                                          | 是一个自定义的 Python 对象 (`object`)                                                                    |
| **类型校验时机** | **仅静态检查阶段**  (IDE, mypy)。运行时传错类型 **不会** 报错 | **严格的运行时校验** 。传入错的类型会直接抛出 `ValidationError` |
| **性能消耗**     | **零消耗** （因为运行时就是个 dict）                                                                                                                                                                    | 有实例化和校验开销                                                                                                                                                                                  |
| **序列化**       | 原生兼容 `json.dumps()`                                                                                                                                                                                                  | 需要调用 `.model_dump()`                                                                                                                                   |

### `ToolStrategy` 与 `ProviderStrategy`

+ **作用**：在 `create_agent` 的 `response_format` 参数中使用。用于强制 Agent 在任务最后，不是回答一句自然语言，而是吐出一个严格的 JSON 数据结构。
+ **区别**：`ProviderStrategy` 依赖模型厂商原生支持；`ToolStrategy` 则是通过“伪造”一个工具调用来强迫模型按格式输出（兼容性更强）。

```python
import os
from pydantic import BaseModel
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain.tools import tool

class EmailExtraction(BaseModel):
    subject: str
    recipient: str

@tool
def get_raw_email() -> str:
    """获取原始邮件文本"""
    return "发给 boss@company.com，主题是本周周报"

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx"
  
    # 强制 Agent 最终只准返回 EmailExtraction 的 JSON 格式
    agent = create_agent(
        model="gpt-4o-mini",
        tools=[get_raw_email],
        response_format=ProviderStrategy(EmailExtraction)
    )
  
    result = agent.invoke({"messages": [("user", "提取最新邮件的信息")]})
    print("最终结构化输出:", result["structured_response"])
    # 输出: EmailExtraction(subject='本周周报', recipient='boss@company.com')
```

---

## 极简代码脚手架

这是一个标准后端接入 Agent 的最简闭环。去掉了复杂的中间件，展示了大模型如何自主决定调用后端函数的逻辑。

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Date           : 2026-04-27 17:02:19
# Description    : 极简 Agent 闭环
import os
from langchain.agents import create_agent
from langchain.tools import tool

# 1. 准备你的后端业务工具
@tool
def get_user_email(user_id: str) -> str:
    """获取指定用户的邮箱地址"""
    # 模拟查库
    mock_db = {"1001": "alice@example.com"}
    return mock_db.get(user_id, "未找到该用户")

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx"

    # 2. 实例化 Agent
    agent = create_agent(
        model="gpt-4o-mini",
        tools=[get_user_email],
        system_prompt="你是一个客服助手。需要查询信息时，务必使用工具。",
    )

    # 3. 运行 Agent (阻塞直到获取最终答案)
    print("Agent 开始处理...")
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "请告诉我用户ID 1001 的邮箱"}]}
    )

    # 4. 打印最终 Agent 给出的自然语言回答
    print("最终回答:", response["messages"][-1].content)
    # 输出示例: "用户ID 1001 的邮箱地址是 alice@example.com。"
```

---

## 常见踩坑与高频面试点（后端视角）

对于多年经验的开发者，面试官不会问具体的语法，而会考察你对 Agent 架构**缺陷**的理解以及解决思路上：

### 高频面试点：ReAct 循环的“死循环”与“幻觉”问题

+ **面试官可能会问**：“如果后端工具报错了，或者模型反复调用同一个工具却得不到预期结果，导致进入死循环，你怎么解决？”
+ **工程对策**：
  + **底线防御**：在 `create_agent` 的底层图中设置 `recursion_limit`**``（最大迭代步数）``**，防止烧穿 API 额度。
  + **中间件拦截**：使用 `@wrap_tool_call` 捕获 Exception 。如果工具抛出错误，绝对不能直接崩溃，而是要把错误堆栈包装成 `ToolMessage` 喂给模型，并在提示词中教它“如果报错 A，请尝试策略 B”。

### 实战踩坑点：多工具引发的“注意力稀释”

+ **现象**：当你的业务越来越庞大，你可能给 `create_agent` 塞入了 20 甚至 50 个 `@tool`。这时大模型会开始混乱，调错工具、参数填错，甚至延迟飙升。
+ **解决方案**：引入**动态工具加载（Dynamic tools）**。文档中提到的 `wrap_model_call` 就是解法。你需要根据当前会话的上下文、用户意图或权限树，在运行时把没用的工具剔除，每次仅暴露出 3-5 个高相关性的工具。

### 架构设计考点：Memory 的持久化（状态膨胀）

+ **面试官可能会问**：“随着多轮对话进行，`messages` 列表越来越大，超过了大模型的 Context Window（上下文窗口）上限怎么办？”
+ **工程对策**：Agent 的 `AgentState` 是驻留在内存里的。在生产中：

1. 必须使用 LangGraph 提供的 Checkpointer（如 `PostgresSaver`）``将 State 持久化到 DB 中``，实现 ``基于 `thread_id``` 的会话恢复``。
2. ``引入中间件（Middleware）``，在调用模型前执行“消息裁剪（Message Trimming）”或定期使用小模型把历史长文本浓缩成摘要（Summarization）。
