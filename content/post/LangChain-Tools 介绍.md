---
title: "LangChain Tools 深度解析：工具模块与实战应用"
date: 2026-05-11T18:13:24+08:00
slug: "langchain-tools-introduction"
image: ""
categories:
    - 技术
tags:
    - LangChain
draft: false
---

## <font style="color:rgb(31, 31, 31);">💡</font><font style="color:rgb(31, 31, 31);"> 一句话核心概念</font>

<strong><font style="color:rgb(31, 31, 31);">Tools 模块是连接大模型“大脑”和外部世界“手脚”的标准化网关。</font></strong><font style="color:rgb(31, 31, 31);"> 它本质上是一套强类型的接口定义与封装规范，将后端的 Python 函数连同其参数类型、注释自动转换为大模型能看懂的 JSON Schema，解决了大模型无法获取实时数据、无法执行系统操作（如查库、调用 API）的核心痛点。</font>

---

## <font style="color:rgb(31, 31, 31);">常用核心 API 及类名</font>

### <font style="color:rgb(31, 31, 31);"></font><font style="color:#DF2A3F;">`@tool`</font><font style="color:rgb(31, 31, 31);"> (装饰器)</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：最基础、最常用的 API。它通过</font><u><font style="color:rgb(31, 31, 31);">反射（Reflection）机制</font></u><font style="color:rgb(31, 31, 31);">，提取 Python 函数的 </font><strong><font style="color:rgb(31, 31, 31);">类型注解 (Type Hints)</font></strong><font style="color:rgb(31, 31, 31);"> 和 </font><strong><font style="color:rgb(31, 31, 31);">Docstring</font></strong><font style="color:rgb(31, 31, 31);">，自动生成大模型所需的接口文档 Schema。</font>
+ <strong><font style="color:rgb(31, 31, 31);">工程视角</font></strong><font style="color:rgb(31, 31, 31);">：这就像是你写后端 Controller 时加的 </font><font style="color:rgb(68, 71, 70);">`@RequestMapping`</font><font style="color:rgb(31, 31, 31);"> 或 Swagger 注解。</font>

```python
import os
from langchain.chat_models import init_chat_model
from langchain.tools import tool

# 函数名、类型注解和注释，缺一不可，这些都会被解析为 JSON Schema 发给大模型
@tool
def get_user_balance(user_id: str) -> str:
    """查询指定用户的账户余额。"""
    # 模拟真实的查库逻辑
    return f"用户 {user_id} 余额为 100 元"

# 独立运行测试
if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx" # 替换为真实 Key 即可运行
    model = init_chat_model("gpt-4o-mini", model_provider="openai")
    
    # 绑定工具
    agent_model = model.bind_tools([get_user_balance])
    
    # 触发调用：大模型不会直接回答，而是返回一个工具调用指令
    response = agent_model.invoke("帮我查一下用户 9527 的余额")
    print("模型生成的工具调用指令:", response.tool_calls)
    # 输出示例: [{'name': 'get_user_balance', 'args': {'user_id': '9527'}, 'id': 'call_xxx', 'type': 'tool_call'}]
```

### <font style="color:rgb(31, 31, 31);"></font><font style="color:#DF2A3F;">`ToolNode`</font><font style="color:rgb(31, 31, 31);"> (属于 LangGraph 预置组件)</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：它是 LangGraph 状态机中专门负责“执行工具”的节点。当大模型下发了一堆</font><u><font style="color:rgb(31, 31, 31);">并发的工具调用</font></u><font style="color:rgb(31, 31, 31);">指令时，</font><font style="color:rgb(68, 71, 70);">`ToolNode`</font><font style="color:rgb(31, 31, 31);"> 会</font><u><font style="color:rgb(31, 31, 31);">负责批量调度执行你的 Python 函数，并自动将结果包装回 </font></u><u><font style="color:rgb(68, 71, 70);">`ToolMessage`</font></u><u><font style="color:rgb(31, 31, 31);"> 喂给模型</font></u><font style="color:rgb(31, 31, 31);">。</font>
+ <strong><font style="color:rgb(31, 31, 31);">参数</font></strong><font style="color:rgb(31, 31, 31);">：</font><font style="color:#DF2A3F;">`handle_tool_errors=True`</font><font style="color:rgb(31, 31, 31);"> (非常核心，，开启后遇到报错不崩溃，而是把报错信息返给大模型让其纠错)。</font>

```python
from langchain_core.messages import AIMessage
from langgraph.prebuilt import ToolNode
from langchain.tools import tool

@tool
def get_user_balance(user_id: str) -> str:
    """查询余额"""
    return "100元"

@tool
def send_email(to: str, content: str) -> str:
    """发送邮件"""
    return f"已向 {to} 发送邮件"

# 初始化 ToolNode，开启全局异常拦截
tool_node = ToolNode([get_user_balance, send_email], handle_tool_errors=True)

# 独立运行测试：手动伪造一个大模型下发的“并发工具调用”指令
mock_ai_message = AIMessage(
    content="",
    tool_calls=[
        {"name": "get_user_balance", "args": {"user_id": "999"}, "id": "call_1"},
        {"name": "send_email", "args": {"to": "admin@test.com", "content": "告警"}, "id": "call_2"}
    ]
)

# 直接运行 ToolNode (它会自动遍历 tool_calls 并执行对应的 Python 函数)
if __name__ == "__main__":
    result = tool_node.invoke({"messages": [mock_ai_message]})
    for msg in result["messages"]:
        print(f"ToolNode 自动封装的回调结果: {msg.content} (对应调用ID: {msg.tool_call_id})")
```

### <font style="color:rgb(31, 31, 31);"></font><font style="color:#DF2A3F;">`ToolRuntime`</font><font style="color:rgb(31, 31, 31);"> (类型提示符)</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：</font><font style="color:#DF2A3F;">工具的</font><strong><font style="color:#DF2A3F;">“运行时上下文”</font></strong><font style="color:rgb(31, 31, 31);">。如果你的工具仅仅是一个纯函数，它无法知道当前的会话 ID 或全局变量。</font><u><font style="color:rgb(31, 31, 31);">将 </font></u><u><font style="color:rgb(68, 71, 70);">`ToolRuntime`</font></u><u><font style="color:rgb(31, 31, 31);"> 作为参数注入，工具就能像中间件一样，读取全局状态（State）、长效记忆（Store）甚至是执行环境（Session Info）</font></u><font style="color:rgb(31, 31, 31);">。</font>
+ <strong><font style="color:rgb(31, 31, 31);">注意</font></strong><font style="color:rgb(31, 31, 31);">：这个参数对大模型是</font><strong><font style="color:rgb(31, 31, 31);">隐藏的</font></strong><font style="color:rgb(31, 31, 31);">，只有你的后端代码能看见。</font>

```python
from typing import Annotated, TypedDict
from langchain.tools import tool, ToolRuntime
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages

# 定义图的全局状态
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_preference: str  # 假设这是存放在会话级别的一个偏好设置

# 定义工具，注入 ToolRuntime 读取图的全局状态
@tool
def check_preference(feature: str, runtime: ToolRuntime) -> str:
    """检查系统的某项功能偏好设置"""
    # 核心：通过 runtime.state 跨越函数作用域，拿到整个对话链路的上下文
    current_pref = runtime.state.get("user_preference", "未设置")
    print(f"[后端拦截日志] 当前读取到的底层状态为: {current_pref}")
    return f"功能 {feature} 的当前偏好是 {current_pref}"

# 独立运行测试
if __name__ == "__main__":
    tool_node = ToolNode([check_preference])
    # 模拟大模型调用该工具
    mock_call = AIMessage(content="", tool_calls=[{"name": "check_preference", "args": {"feature": "UI主题"}, "id": "1"}])
    
    # 将包含全局状态的 dict 传给 ToolNode 触发执行
    result = tool_node.invoke({
        "messages": [mock_call],
        "user_preference": "暗黑模式" # 注入状态
    })
    print("工具执行结果:", result["messages"][0].content)
```

---

## <font style="color:rgb(31, 31, 31);">文档中提到的其他 API 和类名</font>

### <font style="color:rgb(31, 31, 31);"></font><font style="color:rgb(68, 71, 70);">`tools_condition`</font><font style="color:rgb(31, 31, 31);"> (预置路由函数)</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：用在 LangGraph 的条件边（Conditional Edge）中。它本质上是一个 IF 语句：“如果大模型的回复中包含了工具调用指令，就走到 </font><font style="color:rgb(68, 71, 70);">`ToolNode`</font><font style="color:rgb(31, 31, 31);"> 节点；如果只是普通的聊天回复，就走到 </font><font style="color:rgb(68, 71, 70);">`END`</font><font style="color:rgb(31, 31, 31);"> 结束节点”。</font>

```python
import os
from typing import Annotated, TypedDict
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

class State(TypedDict):
    messages: Annotated[list, add_messages]

@tool
def get_server_time() -> str:
    """获取后端服务器时间"""
    return "2026-04-28 12:00:00"

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = "sk-xxx" 
    model = init_chat_model("gpt-4o-mini").bind_tools([get_server_time])

    # 定义大模型节点逻辑
    def call_model(state: State):
        return {"messages": [model.invoke(state["messages"])]}

    # 构建 LangGraph 状态机
    builder = StateGraph(State)
    builder.add_node("llm_node", call_model)
    builder.add_node("tools_node", ToolNode([get_server_time]))

    builder.add_edge(START, "llm_node")
    
    # 核心：使用 tools_condition 自动进行路由分支判断
    builder.add_conditional_edges("llm_node", tools_condition)
    builder.add_edge("tools_node", "llm_node")

    graph = builder.compile()

    # 独立运行：观察执行链路
    for event in graph.stream({"messages": [("user", "服务器现在几点了？")]}):
        print("当前执行的节点:", event.keys())
```

### <font style="color:rgb(31, 31, 31);"></font><font style="color:rgb(68, 71, 70);">`Command`</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：</font><u><font style="color:rgb(31, 31, 31);">状态修改指令</font></u><font style="color:rgb(31, 31, 31);">。传统上，工具返回的是字符串（给大模型看的）。如果你希望工具在后端偷偷修改整个系统的状态（比如把当前语言切换为英语，或者直接中断会话），工具可以返回一个 </font><font style="color:rgb(68, 71, 70);">`Command`</font><font style="color:rgb(31, 31, 31);"> 对象。</font>

```python
from typing import TypedDict
from langchain.tools import tool
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage

class State(TypedDict):
    language: str
    messages: list

@tool
def change_language(lang: str) -> Command:
    """修改系统语言设置"""
    print(f"[后端执行] 正在将底层系统语言切换为: {lang}")
    # 核心：返回 Command 对象，利用 update 字典直接覆写 Graph 的全局 State
    return Command(update={"language": lang})

if __name__ == "__main__":
    tool_node = ToolNode([change_language])
    mock_call = AIMessage(content="", tool_calls=[{"name": "change_language", "args": {"lang": "en-US"}, "id": "1"}])

    # 初始状态为 zh-CN，触发工具节点
    result = tool_node.invoke({"messages": [mock_call], "language": "zh-CN"})
    
    # 查看最终被修改的状态
    print("触发的 State 状态更新为:", result)
```

### <font style="color:rgb(31, 31, 31);"></font><font style="color:rgb(68, 71, 70);">`args_schema`</font><font style="color:rgb(31, 31, 31);"> (使用 Pydantic BaseModel)</font>

+ <strong><font style="color:rgb(31, 31, 31);">作用</font></strong><font style="color:rgb(31, 31, 31);">：对于复杂的后端接口，普通的类型注解不够用。你可以</font><u><font style="color:rgb(31, 31, 31);">传入 Pydantic 模型来做极其严格的入参校验</font></u><font style="color:rgb(31, 31, 31);">（比如限制字符串长度、枚举值）。</font>

---

## <font style="color:rgb(31, 31, 31);">极简代码脚手架</font>

<font style="color:rgb(31, 31, 31);">这段代码展示了如何严谨地定义一个工具，并将其绑定到模型上。这是后端工程师写 Agent 最核心的日常操作。</font>

<strong><font style="color:rgb(31, 31, 31);">tool_definition_and_usage.py：</font></strong>

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 工具定义与调用示例

from langchain.chat_models import init_chat_model
from langchain.tools import tool
from pydantic import BaseModel, Field


# (进阶) 使用 Pydantic 定义严格的输入 Schema
class WeatherInput(BaseModel):
    location: str = Field(description="城市名称，例如：北京")
    days: int = Field(default=1, description="查询未来几天的天气，最多 3 天")


# 定义工具，并绑定 Schema
@tool(args_schema=WeatherInput)
def get_weather(location: str, days: int = 1) -> str:
    """查询指定城市的天气预报。只有当用户明确问天气时才使用此工具。"""
    # TODO: 你的 requests / aiohttp 查天气 API 逻辑
    return f"{location} 未来 {days} 天都是晴天"


# 初始化模型并挂载工具
# os.environ["DEEPSEEK_API_KEY"] = "你的_deepseek_api_key"
model = init_chat_model("deepseek-chat")
# bind_tools 的底层原理：把 Python 函数翻译成 JSON Schema 注入到 API 请求体中
agent_model = model.bind_tools([get_weather])

# 模拟运行
response = agent_model.invoke("北京这三天气温咋样？")
print(response.tool_calls)

```

**输出结果：**

```powershell
[{'name': 'get_weather', 'args': {'location': '北京', 'days': 3}, 'id': 'call_00_ilYab1QAmLljN9n45yTM3889', 'type': 'tool_call'}]
```

---

## <font style="color:rgb(31, 31, 31);">常见踩坑与高频面试点（高级研发视角）</font>

<font style="color:rgb(31, 31, 31);">针对多年经验的后端，面试官在 Tool 这一块一定会深挖</font><strong><font style="color:#DF2A3F;">异常处理、安全性和稳定性</font></strong><font style="color:rgb(31, 31, 31);">：</font>

### <font style="color:rgb(31, 31, 31);">高频踩坑：大模型瞎传参数（幻觉）引发后端 Crash</font>

+ <strong><font style="color:rgb(31, 31, 31);">现象</font></strong><font style="color:rgb(31, 31, 31);">：大模型偶尔会无视你的类型提示，比如你要求传 </font><font style="color:rgb(68, 71, 70);">`int`</font><font style="color:rgb(31, 31, 31);">，它偏偏传个 </font><font style="color:rgb(68, 71, 70);">`"three"`</font><font style="color:rgb(31, 31, 31);">；或者传了你根本没定义的参数。如果不做处理，你的 Python 函数直接抛出 Exception，整个 Agent 进程崩溃。</font>
+ <strong><font style="color:rgb(31, 31, 31);">面试官问</font></strong><font style="color:rgb(31, 31, 31);">：“</font><font style="color:#DF2A3F;">如何保证大模型调用工具时的稳定性？</font><font style="color:rgb(31, 31, 31);">”</font>
+ <strong><font style="color:rgb(31, 31, 31);">工程对策</font></strong><font style="color:rgb(31, 31, 31);">：</font>
    1. <font style="color:rgb(31, 31, 31);">必须使用 Pydantic (</font><font style="color:rgb(68, 71, 70);">`args_schema`</font><font style="color:rgb(31, 31, 31);">) 做强制拦截。</font>
    2. <font style="color:rgb(31, 31, 31);">使用 </font><font style="color:rgb(68, 71, 70);">`ToolNode(tools, handle_tool_errors=True)`</font><font style="color:rgb(31, 31, 31);">。</font><font style="color:rgb(31, 31, 31);background-color:#FBDE28;">当工具抛出异常时，这个参数会将其拦截，并把错误堆栈（Stack Trace）当做字符串包装在 </font><font style="color:rgb(68, 71, 70);background-color:#FBDE28;">`ToolMessage`</font><font style="color:rgb(31, 31, 31);background-color:#FBDE28;"> 里还给大模型，让大模型“知道自己错了，自己换个参数重试”</font><font style="color:rgb(31, 31, 31);">。</font>

<font style="color:rgb(31, 31, 31);"></font>

### <font style="color:rgb(31, 31, 31);">安全与越权（Prompt 注入攻击）</font>

+ <strong><font style="color:rgb(31, 31, 31);">面试官问</font></strong><font style="color:rgb(31, 31, 31);">：“</font><font style="color:#DF2A3F;">如果你写了一个执行 SQL 的 Tool，如何防止用户通过聊天输入进行 Prompt 注入，让大模型执行 </font><font style="color:#DF2A3F;">`DROP TABLE`</font><font style="color:rgb(31, 31, 31);">？”</font>
+ <strong><font style="color:rgb(31, 31, 31);">工程对策</font></strong><font style="color:rgb(31, 31, 31);">：</font>
  + <strong><font style="color:rgb(31, 31, 31);">绝不能信任大模型的输入</font></strong><font style="color:rgb(31, 31, 31);">。Tool 的内部必须像传统的对外 Web API 一样，做严格的权限校验（利用 </font><font style="color:rgb(68, 71, 70);">`ToolRuntime`</font><font style="color:rgb(31, 31, 31);"> 获取当前 </font><font style="color:rgb(68, 71, 70);">`user_id`</font><font style="color:rgb(31, 31, 31);"> 判断权限）。</font>
  + <font style="color:rgb(31, 31, 31);">遵循</font><strong><font style="color:rgb(31, 31, 31);">最小权限原则</font></strong><font style="color:rgb(31, 31, 31);">，数据库查询 Tool 绑定的账号只能有只读权限。</font>
  + <font style="color:rgb(31, 31, 31);">对于敏感操作（如付款、删除），在 Tool 执行前必须引入 Human-in-the-loop（人类确认机制）。</font>

<font style="color:rgb(31, 31, 31);"></font>

### <font style="color:rgb(31, 31, 31);">性能踩坑：Tool 描述写的太随意</font>

+ <strong><font style="color:rgb(31, 31, 31);">痛点</font></strong><font style="color:rgb(31, 31, 31);">：如果不写 Docstring，或者写得很简略，大模型会不知道何时该用这个工具，或者频繁误调用。</font>
+ <strong><font style="color:rgb(31, 31, 31);">对策</font></strong><font style="color:rgb(31, 31, 31);">：Tool 的注释不仅仅是给程序员看的，它是</font><strong><font style="color:rgb(31, 31, 31);">大模型决策的核心依据</font></strong><font style="color:rgb(31, 31, 31);">。遇到复杂的 Tool，需要在 Docstring 中写明 </font><strong><font style="color:rgb(31, 31, 31);">“When to use (何时使用)”</font></strong><font style="color:rgb(31, 31, 31);"> 和 </font><strong><font style="color:rgb(31, 31, 31);">“Do NOT use when (何时禁止使用)”</font></strong><font style="color:rgb(31, 31, 31);">。</font>

<font style="color:rgb(31, 31, 31);"></font>

### <font style="color:rgb(31, 31, 31);">长耗时任务的流式返回</font>

+ <strong><font style="color:rgb(31, 31, 31);">面试官问</font></strong><font style="color:rgb(31, 31, 31);">：“</font><font style="color:#DF2A3F;">如果我的 Tool 是去爬虫，耗时 30 秒，前端用户干等着以为死机了怎么办？</font><font style="color:rgb(31, 31, 31);">”</font>
+ <strong><font style="color:rgb(31, 31, 31);">工程对策</font></strong><font style="color:rgb(31, 31, 31);">：熟悉 </font><font style="color:#DF2A3F;">`ToolRuntime.stream_writer`</font><font style="color:rgb(31, 31, 31);">。在 Tool 执行的过程中，不断通过 </font><font style="color:rgb(68, 71, 70);">`writer("正在分析网页中...")`</font><font style="color:rgb(31, 31, 31);"> 向流中推送中间状态事件，前端 SSE 监听到后就可以展示给用户类似“搜索中...”的动态 UI。</font>

<font style="color:rgb(31, 31, 31);"></font>
