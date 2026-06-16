---
title: "构建带自我纠错机制的 LangGraph 混合 RAG 智能体"
date: 2026-06-10T17:11:21+08:00
slug: "build-langgraph-hybrid-rag-with-self-correction"
image: ""
categories:
    - 技术
tags:
    - LangGraph
    - Hybrid RAG
    - 状态机
draft: false
---

> [Build a custom RAG agent with LangGraph - Docs by LangChain](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
>

<strong>一句话总结：</strong>**LangGraph 提供细粒度控制能力，允许开发者通过定义状态机（节点与条件边）构建混合检索增强生成（Hybrid RAG）智能体，实现大模型自主决定检索时机、动态评估文档质量并自我纠错重写查询的闭环工作流。**

---

## 核心概念与常用 API 解析

在构建复杂的 Agentic RAG 时，LangGraph 将业务逻辑解耦为<strong>状态</strong>（State）、<strong>节点</strong>（Nodes）和<strong>边</strong>（Edges）的设计模式。

### <strong>`MessagesState`</strong>**：图的共享状态**

LangGraph 提供的<strong>标准图状态定义</strong>，内部维护一个 `messages` 列表。它是所有节点之间数据流转的全局上下文，每次节点的输出都会以 <strong>Reducer</strong>（聚合器）追加的形式更新该状态。

```python
from langgraph.graph import MessagesState

# 每个节点函数签名均为：输入 state，返回 state 的更新字典
def some_node(state: MessagesState):
    last_msg = state["messages"][-1]
    ...
    return {"messages": [new_message]}
```

### <strong>`.with_structured_output()`</strong>**：强制结构化输出**

<strong>绑定结构化输出方法</strong>。它强制大语言模型绕过自由文本生成，严格按照传入的 Pydantic Schema（如本例中的`GradeDocuments`）输出 JSON 结构数据。这在状态机中极其关键，因为<u>条件路由（Conditional Edges）要高度确定的输出（如 </u><u>`yes`</u><u> 或 </u><u>`no`</u><u>）来决定下一跳路径</u>。

文档相关性评分用 Pydantic 模型约束 LLM 输出格式：

```python
from pydantic import BaseModel, Field

class GradeDocuments(BaseModel):
    binary_score: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )

grader_model = init_chat_model("gpt-5.4", temperature=0)
response = grader_model.with_structured_output(GradeDocuments).invoke([...])
score = response.binary_score  # "yes" or "no"
```

### <strong>`ToolNode`</strong>**：工具执行引擎**

LangGraph 预构建的<strong>工具执行节点</strong>。它会自动读取当前状态 `messages` 中最后一条 `AIMessage`，解析其中的 `tool_calls` 列表，执行本地 Python 工具函数（并行/串行），最后将执行结果封装为 `ToolMessage` 自动写回图状态中。

```python
from langgraph.prebuilt import ToolNode

workflow.add_node("retrieve", ToolNode([retriever_tool]))
```

### <strong>`.add_conditional_edges()`</strong>**：路由决策核心**

<strong>条件边路由 API</strong>。它接受一个上游节点名、一个路由判断函数以及一个路由映射字典。根据路由函数的返回值（如 `tools` 或 `END`），动态将控制权流转至不同的下游节点，是实现智能体自主决策分支的核心机制。

```python
# 路由一：有 tool_calls 去检索，没有直接结束
def route_on_tool_calls(state: MessagesState):
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END

workflow.add_conditional_edges(
    "generate_query_or_respond",
    route_on_tool_calls,
    {"tools": "retrieve", END: END},
)

# 路由二：文档相关去生成答案，不相关去改写问题
workflow.add_conditional_edges("retrieve", grade_documents)
```

---

## 周边与扩展 API 梳理

结合官方文档与超链接引用内容，以下概念构成了该 Hybrid RAG 架构的完整生态：

### **Retrieval 检索流拼图**

文档开篇的检索摄取管道依赖于底层抽象：

+ `WebBaseLoader` 负责非结构化网页的 DOM 树抓取；
+ `RecursveCharacterTextSplitter` 实现上下文感知的递归文本分块；
+ `OpenAIEmbeddings` 将文本稠密化为高维向量；
+ 最终由 `InMemoryVectorStore` 提供近似最近邻（ANN）检索。

### **Agent Messages 消息协议**

在图状态中流转的是强类型的消息对象。智能体的思考与工具调用参数封装在 `AIMessage` 中；本地检索函数返回的内容封装在 `ToolMessage` 中；用户重写的查询内容则通过显式实例化 `HumanMessage` 重新注入状态，从而欺骗模型开启新一轮的独立思考。

### **LangSmith Trace 监控**

由于多节点图流转存在自我循环（如重写问题后再次触发检索），开发者极难通过终端日志掌握执行全貌。集成 LangSmith 可视化 Trace 可以精准捕获每个 Node 的进入/退出耗时、输入状态以及 `grade_documents` 判别节点的具体结构化输出结果。

---

## 工程化代码落地示例

以下代码将官方文档中的代码片段重组为完全可独立运行的工程化脚本。该脚本实现了从文档解析、工具定义到图状态机构建与执行的全流程。

```python {title="agentic_rag_langgraph.py"}
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 基于 LangGraph 构建带“自我纠错”与“最大重试降级”机制的 Agentic RAG（结构优化版）
# requirements   : pip install -U langgraph langchain langchain-community langchain-huggingface langchain-text-splitters langchain-deepseek pydantic

import os
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.messages import HumanMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field


# ==========================================
# 1. 全局数据结构定义 (State & Schema)
# ==========================================
class AgentState(MessagesState):
    """继承自带的 MessagesState，并追加 retry_count 字段用于记录重写次数。"""

    retry_count: int


class GradeDocuments(BaseModel):
    """裁判模型的结构化输出定义 (Pydantic)"""

    binary_score: str = Field(
        description="文档是否相关: 相关输出 'yes', 不相关输出 'no'"
    )


# ==========================================
# 2. 核心工厂函数：构建并编译图状态机
# ==========================================
def build_agentic_rag_graph():
    """
    工厂函数：封装 ETL 流程、模型初始化与图编译，避免全局变量污染。
    利用闭包（Closure）特性，使内部节点函数可以安全访问本地的 llm 和 retriever 实例。
    """

    # ----------------------------------
    # 2.1 离线数据准备 (ETL)
    # ----------------------------------
    print("[System] 正在加载和向量化数据...")

    # 这里我们使用 Lilian Weng 博客中关于强化学习的文章作为知识库，实际应用中可以替换为更大规模的文档集合。
    docs = WebBaseLoader(
        "https://lilianweng.github.io/posts/2024-11-28-reward-hacking/"
    ).load()

    # 将文档切分成更小的片段，便于向量化和检索
    doc_splits = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50
    ).split_documents(docs)

    # 使用 HuggingFaceEmbeddings 将文本转换为向量，选择一个适合的模型（如 BGE-M3）并启用归一化以提升检索效果
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={"device": "mps"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # 构建内存向量数据库并创建检索器
    vectorstore = InMemoryVectorStore.from_documents(
        documents=doc_splits, embedding=embeddings
    )
    retriever = vectorstore.as_retriever()

    # ----------------------------------
    # 2.2 定义工具 (Tools)
    # ----------------------------------
    @tool
    def retriever_tool(query: str) -> str:
        """当需要获取 Lilian Weng 博客关于强化学习、大模型相关的背景知识时使用此工具。"""
        retrieved_docs = retriever.invoke(query)
        return "\n\n".join([doc.page_content for doc in retrieved_docs])

    # ----------------------------------
    # 2.3 初始化大模型
    # ----------------------------------
    llm = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)
    llm_with_tools = llm.bind_tools([retriever_tool])

    # ----------------------------------
    # 2.4 定义图节点 (Nodes)
    # ----------------------------------
    def generate_query_or_respond(state: AgentState):
        """节点1: 决定是直接回复用户，还是调用检索工具"""
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def rewrite_question(state: AgentState):
        """节点2: 当检索结果不佳时，重写用户的 Query"""
        question = state["messages"][0].content
        prompt = f"分析以下问题并挖掘其深层语义，重写一个更好的搜索关键词:\n{question}"
        response = llm.invoke([{"role": "user", "content": prompt}])

        current_retry = state.get("retry_count", 0)
        print(f"[Log] 执行检索重写: 当前重试次数增加至 {current_retry + 1}")
        return {
            "messages": [
                HumanMessage(content=response.content)
            ],  # 将重写后的问题放回 messages 中，供下一轮使用
            "retry_count": current_retry + 1,
        }

    def generate_answer(state: AgentState):
        """节点3: 最终整合上下文生成回答"""
        question = state["messages"][0].content
        context = state["messages"][-1].content
        prompt = f"请基于以下上下文回答问题。若不知晓或上下文中未提及，请直接说“很抱歉，在知识库中未能找到相关解答”。\n问题:{question}\n上下文:{context}"
        response = llm.invoke([{"role": "user", "content": prompt}])
        return {"messages": [response]}

    # ----------------------------------
    # 2.5 定义路由边 (Conditional Edges)
    # ----------------------------------
    def grade_documents(
        state: AgentState,
    ) -> Literal["generate_answer", "rewrite_question"]:
        """条件边: LLM 作为裁判评估检索质量"""
        current_retry = state.get("retry_count", 0)

        # 降级保护
        if current_retry >= 3:
            print(
                f"[Log] 触发降级保护: 重试次数已达 {current_retry} 次，直接生成降级回答。"
            )
            return "generate_answer"

        question = state["messages"][0].content
        context = state["messages"][-1].content
        prompt = f"你是一个打分员。评估以下文档是否与问题相关。\n问题: {question}\n文档: {context}"

        grader = llm.with_structured_output(GradeDocuments)
        score = grader.invoke([{"role": "user", "content": prompt}]).binary_score
        print(f"[Log] 裁判系统打分: {score}")

        return "generate_answer" if score == "yes" else "rewrite_question"

    def route_on_tool_calls(state: AgentState):
        """条件边: 判断大模型是否下发了工具调用指令"""
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    # ----------------------------------
    # 2.6 组装与编译图 (Compile Graph)
    # ----------------------------------
    workflow = StateGraph(AgentState)

    workflow.add_node("generate_query_or_respond", generate_query_or_respond)
    workflow.add_node("tools", ToolNode([retriever_tool]))
    workflow.add_node("rewrite_question", rewrite_question)
    workflow.add_node("generate_answer", generate_answer)

    workflow.add_edge(START, "generate_query_or_respond")
    workflow.add_conditional_edges("generate_query_or_respond", route_on_tool_calls)
    workflow.add_conditional_edges("tools", grade_documents)
    workflow.add_edge("rewrite_question", "generate_query_or_respond")
    workflow.add_edge("generate_answer", END)

    return workflow.compile()


# ==========================================
# 3. 程序执行入口
# ==========================================
def main():
    # 注入 API Key (生产环境通常在 .env 文件中维护)
    os.environ["DEEPSEEK_API_KEY"] = os.getenv(
        "DEEPSEEK_API_KEY", "sk-your-deepseek-api-key"
    )

    # 获取编译好的图引擎
    graph = build_agentic_rag_graph()

    inputs = {
        "messages": [{"role": "user", "content": "What is reward hacking?"}],
        "retry_count": 0,
    }

    print("\n--- 开始流式输出节点轨迹 ---")
    for chunk in graph.stream(inputs):
        for node_name, update_data in chunk.items():
            print(f"--- 节点执行完毕: {node_name} ---")
            if "messages" in update_data:
                print(f"--- 节点输出信息：{update_data["messages"][-1].content + "\n\n"}")
                # print(f"最终生成的结果: {update_data['messages'][-1].content}\n")


if __name__ == "__main__":
    main()


```

**输出结果：**

```powershell
[System] 正在加载和向量化数据...
Loading weights: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 391/391 [00:00<00:00, 66872.16it/s]

--- 开始流式输出节点轨迹 ---
--- 节点执行完毕: generate_query_or_respond ---
--- 节点输出信息：Let me search for information about reward hacking.


[Log] 裁判系统打分: yes
--- 节点执行完毕: tools ---
--- 节点输出信息：Detecting Reward Hacking#

In-Context Reward Hacking#

Reward hacking occurs when a reinforcement learning (RL) agent exploits flaws or ambiguities in the reward function to achieve high rewards, without genuinely learning or completing the intended task. Reward hacking exists because RL environments are often imperfect, and it is fundamentally challenging to accurately specify a reward function.

Let’s Define Reward Hacking#
Reward shaping in RL is challenging. Reward hacking occurs when an RL agent exploits flaws or ambiguities in the reward function to obtain high rewards without genuinely learning the intended behaviors or completing the task as designed. In recent years, several related concepts have been proposed, all referring to some form of reward hacking:


--- 节点执行完毕: generate_answer ---
--- 节点输出信息：根据上下文，reward hacking（奖励黑客行为）是指强化学习（RL）代理利用奖励函数中的缺陷或模糊性来获得高额奖励，而没有真正学习或完成预期任务的行为。


```

**代码执行流程图：**

{{< mermaid >}}
graph TD
    %% 定义节点样式
    classDef state fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff
    classDef agent fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff
    classDef tool fill:#065f46,stroke:#10b981,stroke-width:2px,color:#fff
    classDef condition fill:#7c2d12,stroke:#f97316,stroke-width:2px,color:#fff

    %% 提前定义首尾节点
    START((START<br>初始输入)):::state
    END_NODE((END<br>执行结束)):::state

    START --> Node_GenQuery
    
    subgraph loop_block [LangGraph 引擎流转区域]
        Node_GenQuery["节点：generate_query_or_respond<br>(大模型意图识别：直接回复或调工具)"]:::agent
        
        Cond_ToolCalls{"条件路由：route_on_tool_calls<br>(判断是否下发 tool_calls 指令)"}:::condition
        
        Node_Tools["节点：tools<br>(底层执行 retriever_tool 检索本地库)"]:::tool
        
        Cond_Grade{"条件路由：grade_documents<br>(前置检查 retry_count 并打分)"}:::condition
        
        Node_Rewrite["节点：rewrite_question<br>(重写 Query 并将 retry_count 增加)"]:::agent
        
        Node_Answer["节点：generate_answer<br>(基于最终上下文生成回答)"]:::agent
        
        %% 核心执行流转
        Node_GenQuery --> Cond_ToolCalls
        Cond_ToolCalls -- "无 tool_calls (无需查库)" --> END_NODE
        Cond_ToolCalls -- "有 tool_calls (触发检索)" --> Node_Tools
        
        Node_Tools --> Cond_Grade
        
        Cond_Grade -- "评分：no (不相关且次数未达标)" --> Node_Rewrite
        Node_Rewrite -- "带着新问题重试" --> Node_GenQuery
        
        Cond_Grade -- "评分：yes (相关)" --> Node_Answer
        Cond_Grade -- "触发降级 (达到重试上限)" --> Node_Answer
    end
    
    Node_Answer --> END_NODE
{{< /mermaid >}}

---

## 常见踩坑与高频面试点

### 常见踩坑

#### **踩坑一：<strong>`with_structured_output`</strong>解析失败导致图崩溃**

裁判节点的模型指令遵循能力弱或 Prompt 不严谨时，结构化输出可能抛出异常。需在 `grade_documents` 内加 `try-except`，解析失败时默认走 `generate_answer` 熔断路径。

#### **踩坑二：查询重写无限循环**

检索质量始终不达标时，Agent 会在"重写 → 检索 → 再重写"中死循环。必须在自定义 State 中加 `retry_count: int`，超过阈值强制出图。

---

### 高频面试点

#### **Q1：<strong>`with_structured_output()`</strong>底层怎么实现的？**

<strong>答：</strong>两条路：支持 `tool_calls` 的模型（如 GPT-4o）将 Pydantic Schema 转为 Function Calling Schema；不支持的走 Prompt 约束 + 输出解析。前者可靠，后者有 JSON 解析失败风险。

#### **Q2：<strong>`StateGraph`</strong>相比 LCEL 链的优势？**

<strong>答：</strong>LCEL 是线性管道，适合单次固定流程；`StateGraph` 是有向图，天然支持循环、条件分支和持久化检查点（`MemorySaver`）。Agent 的"思考—行动—观察"多轮循环是 `StateGraph` 的核心优势。

#### **Q3：为什么需要把 RAG 升级为 Agentic RAG？**

<strong>答：</strong>普通 RAG 是固定管道，面对模糊意图时检索信噪比低，容易产生幻觉。Agentic RAG 引入评分节点（`GradeDocuments`）和改写节点（`rewrite_question`），检索质量差时自动截断并二次召回，用略高的延迟换取召回质量的大幅提升。

#### **Q4：跨节点传递消息时如何防止上下文污染？**

**答：**`MessagesState` 底层用 `add_messages` Reducer 实现追加语义，各节点输出的消息是原子追加到全局消息列表，而不是覆盖。这保证了无论图的分支多复杂，最终生成节点拿到的消息历史始终是准确有序的。

#### **Q5：子图（Subgraph）的流式输出如何防止串台？**

<strong>答：</strong>使用 `version="v3"` 的事件流并拦截 `stream.subgraphs`，通过 `create_agent` 时设置的 `name` 属性过滤不同子图的消息，防止多个子图的输出混流。
