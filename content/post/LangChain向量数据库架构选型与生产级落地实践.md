---
title: "LangChain 向量数据库架构选型与生产级落地实践"
date: 2026-06-03T14:58:47+08:00
slug: "langchain-vector-stores-architecture-and-practices"
image: ""
categories:
    - 技术
tags:
    - LangChain
    - Vector Stores
draft: false
---

> [Vector store integrations - Docs by LangChain](https://docs.langchain.com/oss/python/integrations/vectorstores/)
>

**一句话总结：向量存储（Vector Stores）是专为<strong><strong><u>存储高维稠密向量</u></strong></strong>（Dense Vectors）并<strong><strong><u>执行近似最近邻（ANN）相似度搜索</u></strong></strong>而设计的专用数据库抽象层，它是实现 RAG（检索增强生成）架构中<strong><strong><u>上下文召回（Retrieval）能力</u></strong></strong>的核心数据基建。**

---

## 核心概念与常用 API 解析

向量库是 RAG 系统的<strong>持久化检索层</strong>，承接<strong>嵌入模型</strong>的输出，分两个核心阶段工作：

+ <strong>建索引阶段</strong>：文档 → 嵌入模型 → 向量 → 写入向量库
+ <strong>检索阶段</strong>：用户查询 → 嵌入模型 → 查询向量 → 向量库相似度搜索 → Top-K 文档

LangChain 提取了统一的 VectorStore 接口，以屏蔽底层不同向量数据库（如 FAISS、Milvus、PGVector 等）的驱动差异。

+ **初始化与 Embedding 绑定**  
向量数据库不直接处理原始文本，其内部运算依赖于将文本转化为向量的 Embedding 模型。因此，实例化 Vector Store 的必要条件是注入一个具体的 Embedding 实例。
+ <strong>`add_documents`</strong>**(数据入库)**  
接收标准的 Document 对象列表（包含 page_content 与 metadata），并在底层自动调用挂载的 Embedding 模型将 page_content 向量化，最后连同元数据一起存入向量索引中。支持通过 ids 参数传入主键以实现后续的去重或更新。
+ <strong>`similarity_search`</strong>**(语义相似度检索)**  
核心查询 API。接收用户的自然语言 Query，底层自动将其向量化，并在向量空间中计算距离，返回最相关的 Top-k 个 Document 对象。
  + <strong>注意</strong>：
        1. 全局向量相似度搜索在企业场景里会导致两个问题：幻觉和<strong>权限越界</strong>（不同租户的数据互相检索到）。解决方案是元数据过滤，等同于 SQL 的 `WHERE` 条件。
        2. 不同向量库对 `filter` 的语法支持不同，切换库时要确认。

```python
# 先按 source 硬过滤，再在结果集内做向量相似度计算
# 只在来源为"财务制度"的文档里做语义检索
results = vector_store.similarity_search(
    "报销上限是多少",
    k=3,
    filter={"source": "财务制度"}
)
```

+ <strong>`delete`</strong>**(数据清理与删除)**
  + <strong>核心功能</strong>：通过指定唯一标识符（ID 列表），从底层向量数据库中物理移除已存储的文本切片（Chunks）及其对应的向量特征。
  + <strong>应用场景</strong>：在动态更新的 RAG 知识库中，知识的时效性至关重要。当外部源文件被修改或废弃时，必须调用 delete 清除旧的向量残骸，再通过 add_documents 写入新数据，以防止大模型检索到过期信息产生幻觉。同时，这也是满足企业级数据合规与隐私擦除要求的必备接口。
  + <strong>注意</strong>：根据官方文档末尾的“特性支持矩阵（Compatibility Table）”，<u>并非所有的向量数据库都原生支持“按 ID 删除”</u>。

<strong>基础使用示例</strong>：

```python
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

# 初始化模型与向量存储
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
vector_store = InMemoryVectorStore(embedding=embeddings)

# 传入 Document 对象执行入库
vector_store.add_documents(documents=[doc1, doc2], ids=["id1", "id2"])

# 删除数据
# ids 一定要显式传，不传的话向量库会自动生成随机 ID，后续无法精准删除或更新。
vector_store.delete(ids=["id1"]) 

# 执行相似度检索
similar_docs = vector_store.similarity_search("用户查询文本", k=3)

```

---

## 周边与扩展 API 梳理

除了基础的文本检索，VectorStore 接口还定义了一系列面向复杂检索场景的高级 API 与特性：

+ **带分数的查询 (similarity_search_with_score)**  
返回匹配文档的同时，携带对应的相似度距离分数（Distance Score）。这是执行后置重排（Rerank）或设置硬性相似度截断阈值的关键依赖。
+ <strong>基于向量的查询 (</strong><strong>similarity_search_by_vector</strong>**)**  
跳过内置的文本 Embedding 步骤，直接接收一个 List[float] 格式的预计算向量进行检索。常用于多模态检索（例如用图像生成的向量去检索对应的文本描述）或级联检索体系。
+ <strong>最大边际相关性搜索 (</strong><strong>max_marginal_relevance_search</strong>******/ MMR)**  
一种经典的检索优化算法。它在保证召回结果与 Query 高度相关的同时，主动惩罚结果集合内部的相似度，从而提升返回文档的“多样性（Diversity）”，有效缓解大模型上下文信息冗余的问题。
+ <strong>异步操作 API (</strong><strong>asimilarity_search</strong><strong>,</strong>****<strong>aadd_documents</strong>**)**  
在高并发的 Agent 架构中，向量计算与网络 I/O 是核心阻塞点。LangChain 提供了全面的异步方法支持非阻塞调用。
+ **元数据过滤 (Metadata Filtering)**  
通过 filter 参数，在执行高维向量空间检索的前置或后置阶段，对 Document.metadata（如时间戳、来源、租户 ID）进行精准匹配过滤，以缩小检索空间并提高命中精度。

---

## 向量数据库选型决策树（工程核心区）

在真实的生产落地中，向量数据库的选型本质上是针对基础设施现状与运维成本的权衡：

| **业务场景** | **推荐选型方案** | **架构师选型理由** |
| :---: | --- | --- |
| **本地开发 / 快速原型** | FAISS / InMemoryVectorStore | 零外部依赖、纯本地运行、进程同生命周期，无需部署任何中间件。 |
| **轻量级单机持久化** | Chroma / LanceDB | 自带基于本地文件系统的持久化（SQLite/Parquet），比 FAISS 更易于管理和重启加载。 |
| **已有现成 PostgreSQL** | PGVector | **运维成本最低！** 复用现有 DB 基础设施，支持 ACID 事务，实现关系型数据与向量数据的跨表联合查询。 |
| **已有现成 MongoDB** | MongoDB Atlas | 无需引入新的基建栈，直接利用 Atlas 的 Vector Search 插件。 |
| **十亿级/生产云端托管** | Pinecone / Qdrant Cloud | 免去底层运维烦恼，天然支持分布式水平扩展、读写分离与高可用（HA）。 |
| **私有化高性能集群部署** | Milvus | 针对海量向量深化的云原生架构，支持存储计算分离，适合大型 AI 团队自建。 |

在选型时，<strong>Data Egress（数据出站/出域）合规风险</strong>具有一票否决权。在金融、医疗等强合规行业，即便托管云方案再好，只要数据不能出内网，我们也只能走基于 Milvus 或 PGVector 的私有化部署方案。

---

## 核心能力对比矩阵（选型避坑参考）

不要盲目跟风选用某款数据库，必须提前比对官方的能力矩阵。特别是<strong>多租户架构下，如果选错了不支持 Metadata 过滤的数据库，将是灾难性的</strong>。

_(提取自 LangChain 官方文档特性支持矩阵)_

| **向量数据库** | **按 ID 删除** | **元数据过滤** | **基于向量本身检索** | **异步支持** |
| :---: | :---: | :---: | :---: | :---: |
| **FAISS** | ✅ | ✅ | ✅ | ✅ |
| **Chroma** | ✅ | ✅ | ✅ | ✅ |
| **PGVector** | ✅ | ✅ | ✅ | ✅ |
| **Qdrant** | ✅ | ✅ | ✅ | ✅ |
| **Milvus** | ✅ | ✅ | ✅ | ✅ |
| **Pinecone** | ✅ | ✅ | ✅ | ✅ |
| **InMemoryVectorStore** | ✅ | ✅ | ❌ | ✅ |
| **ElasticsearchStore** | ✅ | ✅ | ✅ | ✅ |

<strong>注意</strong>：

官方的 InMemoryVectorStore，它虽然支持条件过滤，但<strong>不支持直接传入一个生向量（Raw Vector）进行检索</strong>（即 Search by Vector 为 ❌）。如果业务涉及到复杂的跨模态检索（比如先用单独的视觉模型把图片转成向量，再拿着向量去库里搜），就必须避开这类数据库，换用 FAISS 等全功能库。

---

## 利用 FakeEmbedding 实现 RAG 单元测试 (Mock)

在实际的后端工程流中，我们极度反感在自动化测试（Unit Test / CI/CD）环节产生真实的外部网络 I/O 或高昂的计算开销。

+ <strong>业务痛点</strong>：如果在单元测试中真实调用 OpenAIEmbeddings 或加载几十个 GB 的本地大模型，会导致测试流水线极其缓慢、极易因网络波动报错，甚至产生大量无意义的 API 计费。
+ <strong>满分对策</strong>：LangChain 原生提供了 DeterministicFakeEmbedding 类。它完美复刻了传统的 <strong>Mock 测试思想</strong>。它会根据输入的文本确定性地生成假向量（只要文本一致，生成的假向量就一致），不仅运行速度达到了微秒级，更彻底解耦了对底层 GPU 算力和外部大模型 API 的依赖。

**测试代码落地示例：**

```python {title="mock_vector_store_test.py"}
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 演示在 CI/CD 或单元测试环境下，使用 FakeEmbedding 对向量库操作进行 Mock 隔离测试
# requirements   : pip install -U langchain-core

from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document

def test_rag_pipeline_logic():
    print("--- 启动完全离线的 RAG 链路单元测试 ---")
    
    # 1. 核心技巧：使用假嵌入模型进行打桩 (Mock)，指定生成的假向量维度为 1024
    fake_embeddings = DeterministicFakeEmbedding(size=1024)
    
    # 2. 注入假模型，初始化内存向量库
    vector_store = InMemoryVectorStore(embedding=fake_embeddings)
    
    # 3. 正常执行入库测试
    doc = Document(page_content="测试文档，验证系统编排逻辑", metadata={"source": "test"})
    vector_store.add_documents([doc])
    
    # 4. 正常执行检索测试
    results = vector_store.similarity_search("随便搜点什么")
    
    # 断言业务逻辑是否跑通，而不是验证向量数学计算的准确性
    assert len(results) == 1
    assert results[0].metadata["source"] == "test"
    print("单元测试通过！向量存储与检索逻辑流转正常，且无任何外部网络消耗。")

if __name__ == "__main__":
    test_rag_pipeline_logic()
```

---

## 工程化代码落地示例

以下代码展示了如何使用开源本地向量库 FAISS 结合 HuggingFaceEmbeddings，实现包含全生命周期管理（入库、持久化、元数据过滤、MMR 检索）的完整工程流。

```python {title="vector_store_pipeline.py"}
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 演示向量数据库（Vector Store）的核心生命周期：初始化、入库、持久化、元数据过滤与 MMR 检索。
# requirements   : pip install -U langchain-core langchain-community langchain-huggingface faiss-cpu

import os
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

def main():
    # 1. 实例化 Embedding 模型 (使用 BAAI/bge-m3 开源模型)
    print("--- 初始化 Embedding 模型 ---")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        encode_kwargs={"normalize_embeddings": True}
    )

    # 2. 准备带 Metadata 的知识库文档
    docs = [
        Document(page_content="公司的报销流程要求在每月的25号前提交发票。", metadata={"category": "finance", "tenant_id": "T001"}),
        Document(page_content="财务部规定，所有的差旅费用必须附带电子发票记录。", metadata={"category": "finance", "tenant_id": "T001"}),
        Document(page_content="新员工入职培训将在每周一上午10点于一号会议室举行。", metadata={"category": "hr", "tenant_id": "T001"}),
        Document(page_content="The weather in San Francisco is always sunny.", metadata={"category": "weather", "tenant_id": "T002"})
    ]

    # 3. 初始化 Vector Store 并执行入库 (Indexing)
    print("--- 执行向量化与入库 ---")
    vector_store = FAISS.from_documents(documents=docs, embedding=embeddings)
    
    # [工程特性]: 本地向量库持久化
    vector_store.save_local("./faiss_cache")
    print("向量库已持久化至 ./faiss_cache 目录")

    # 4. 执行常规相似度检索与 Metadata Filtering (元数据过滤)
    print("\n--- 执行带 Metadata 过滤的相似度检索 ---")
    query = "报销有什么要求？"
    # 过滤条件：仅检索财务分类，且属于租户 T001 的数据
    results = vector_store.similarity_search_with_score(
        query, 
        k=2, 
        filter={"category": "finance", "tenant_id": "T001"}
    )
    
    for doc, score in results:
        print(f"得分: {score:.4f} | 内容: {doc.page_content}")

    # 5. 执行 MMR (最大边际相关性) 检索，保证结果多样性
    print("\n--- 执行 MMR 多样性检索 ---")
    mmr_results = vector_store.max_marginal_relevance_search(
        query,
        k=2,          # 最终返回的结果数
        fetch_k=10,   # 初始从向量库中召回的候选数量
        lambda_mult=0.5 # 多样性惩罚系数：0表示完全关注多样性，1表示完全关注相关性
    )
    
    for i, doc in enumerate(mmr_results):
        print(f"MMR 结果 {i+1}: {doc.page_content}")

if __name__ == "__main__":
    main()
```

**输出结果：**

```powershell
--- 初始化 Embedding 模型 ---
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 391/391 [00:00<00:00, 64436.48it/s]
--- 执行向量化与入库 ---
向量库已持久化至 ./faiss_cache 目录

--- 执行带 Metadata 过滤的相似度检索 ---
得分: 0.5263 | 内容: 公司的报销流程要求在每月的25号前提交发票。
得分: 0.8094 | 内容: 财务部规定，所有的差旅费用必须附带电子发票记录。

--- 执行 MMR 多样性检索 ---
MMR 结果 1: 公司的报销流程要求在每月的25号前提交发票。
MMR 结果 2: The weather in San Francisco is always sunny.
```

<strong>说明</strong>：

1. FAISS 的原生底层算法默认计算的是 <strong>L2 距离（欧氏距离的平方）</strong>！距离越近，分数越<strong>小</strong>。0.5263 比 0.8094 更接近 0，说明第一句话在几何空间上与 Query 靠得更近。执行带 Metadata 过滤的相似度检索的结果证明了<strong>元数据过滤</strong>的阻断是成功的，这是企业级<strong>权限隔离</strong>的基石。
2. <strong>MMR 出现看似离谱的召回，是因为测试集过小导致的‘多样性惩罚过载’</strong>。在海量真实的生产数据中，MMR 能有效打散高度重复的知识片段（比如 10 段不同人写的关于报销流程的描述），从而拓宽输入给 LLM 的知识广度。  
如果业务上不希望出现这种完全不相关的召回，可以通过调高 lambda_mult（比如设为 0.8，增加相关性权重），或者在最外层加一层<strong>相似度阈值拦截（Similarity Score Threshold）</strong>来做底线防守。

---

## 常见踩坑与高频面试点

在 RAG 系统的架构设计中，Vector Store 的选型与查询策略优化是决定系统扩展性与准确率的关键阵地。

#### 高频考点 1：如何进行 Vector Store 的技术选型？

+ <strong>考察点</strong>：对向量数据库生态生态体系、系统并发量及部署复杂度的权衡能力。
+ <strong>满分回答</strong>：向量库的选型应严格基于系统所处的生命周期与业务规模：
  + <strong>开发测试/单机部署</strong>：首选 InMemoryVectorStore 或 FAISS、Chroma。它们无需前置部署中间件，与进程同生命周期，开发体验极佳。
  + <strong>存量后端基建平滑升级</strong>：推荐使用 PGVector（基于 PostgreSQL）或 Redis / Elasticsearch 的向量插件。这种方案能复用现有的运维体系，且天然支持 ACID 事务与标量/向量混合查询。
  + <strong>十亿级向量/高并发云原生集群</strong>：必须引入 Milvus、Qdrant 或 Pinecone。这类专用向量数据库在底层深度优化了 HNSW（分层可导航小世界）算法，并支持分布式分片（Sharding）、读写分离与高可用（HA）。

#### 高频考点 2：在多租户（Multi-Tenancy）Agent 架构中，如何保证向量检索的安全性？

+ <strong>考察点</strong>：对 RAG 数据权限隔离边界与向量库特性的掌握程度。
+ <strong>满分回答</strong>：在 B 端企业级场景中，数据越权是绝对红线。物理上，不能为每个用户建一个独立的索引实例。工程落地时，必须在文档的 Metadata 中强行注入 tenant_id 或 user_id。检索时，通过 Vector Store 的 filter 参数执行前置过滤（Pre-filtering）。需要注意，在选型时必须审查官方特性支持矩阵（如文档末尾的表格所示），确保选用的库（如 Milvus、Qdrant）原生支持高效的 Metadata Filtering 和多租户物理分区，否则在大基数过滤时极易产生 OOM 或导致 ANN 近似检索失效。

#### 常见踩坑 1：余弦相似度与点积的混用导致的阈值失效

+ <strong>现象与痛点</strong>：通过 similarity_search_with_score 设定了一个相似度阈值（如 >0.8），但在更换底层 Vector Store（如从 FAISS 换到 Chroma）后，发现逻辑全部崩溃，甚至出现了大于 1 的异常分数。
+ <strong>工程对策</strong>：不同向量数据库底层默认的相似度度量（Distance Metrics）标准不同（FAISS 默认输出 L2 欧氏距离的平方，距离越小越相似；而部分库输出余弦相似度，分数越高越相似）。在工业级实现中，强烈建议在 Embedding 阶段配置 normalize_embeddings=True（强制进行 L2 归一化），这样无论底层使用哪种距离算法，点积（Dot Product）与余弦相似度在数学上将完全等价，极大地拉平了底层计算差异与排序一致性。
