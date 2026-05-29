---
title: "LangChain 三大核心切分策略与高频考点"
date: 2026-05-29T16:43:45+08:00
slug: "langchain-3-core-text-splitters-and-interview-points"
image: ""
categories:
    - 技术
tags:
    - LangChain
    - 文本切分
draft: false
---

> [Text splitter integrations - Docs by LangChain](https://docs.langchain.com/oss/python/integrations/splitters)
>

**一句话总结：文本切分器（Text Splitter）是 RAG 系统中用于解决模型上下文窗口受限的核心组件，它通过基于文本自然结构、物理长度或特定文档格式语义树（Markdown/JSON/HTML/代码）的三大核心策略，将超长语料安全截断为易于向量化和高信噪比检索的小文本块。**

---

## 三大核心切分策略与 API 解析

官方文档明确指出了切分文档的三种核心策略，它们分别对应了不同的业务场景与数据容错级别：

### 策略一：基于文本结构切分 (Text structure-based)

+ <strong>核心理念</strong>：利用人类自然语言固有的层级结构（段落 -> 句子 -> 单词）来指导切分，尽最大努力保持局部语义的连贯性。
+ <strong>代表 API</strong>：`RecursiveCharacterTextSplitter`（递归字符切分器）
  + 它是 LangChain 官方<strong>最推荐的默认策略</strong>。底层默认按 ["\n\n", "\n", " ", ""] 顺序尝试。
  + 如果一个段落（\n\n 分隔）小于目标尺寸，就整体保留；一旦超标，才会递归降级到按句子甚至单词切分，从而避免将完整的句子生硬拦腰截断。

### 策略二：基于长度切分 (Length-based)

+ <strong>核心理念</strong>：简单粗暴的硬性截断，确保每个产出的文本块绝对不会超出设定的物理长度限制。它不关心自然语言的段落完整性，只关注底层数据的吞吐合规性。
+ <strong>子分类与代表 API</strong>：
  + <strong>基于字符长度</strong>：使用 `CharacterTextSplitter`，通过设定特定的分隔符（默认是双换行）和严格的字符数量进行截断。
  + <strong>基于 Token 长度</strong>：由于大模型（LLM）的底层计费和输入限制均基于 Token，通常配合 tiktoken 编码器使用（调用 `CharacterTextSplitter.from_tiktoken_encoder`）。它能精准算出 Token 消耗并以此为边界进行切割。

### 策略三：基于文档结构切分 (Document structure-based)

+ <strong>核心理念</strong>：针对具备天然语法树或层级结构的半结构化文件（如 HTML、Markdown、JSON、代码），单纯按换行或长度切分会破坏其原有的逻辑组装。此策略能够感知文件结构，并在切分时保留父子层级关系，提取为元数据（Metadata）。
+ <strong>代表 API</strong>：

1. <strong>MarkdownHeaderTextSplitter（Markdown 标题切分器）</strong>：通过识别 #, ## 等标题，切分 Markdown，并将标题提取为上下文字段。
2. <strong>RecursiveJsonSplitter（递归 JSON 切分器）</strong>：智能识别 JSON 的 Object 或 Array 边界，保证切分出的块依然具备合法的 JSON 子结构特征。
3. <strong>Code Splitter（语言感知切分器）</strong>：通过例如 `RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON)` 初始化。底层内置了对特定编程语言（如 Python、Go、JS 等）的抽象语法树（AST）规则。优先保证<strong>函数</strong>、<strong>类</strong>等代码逻辑块的完整性，避免代码被生硬切断。
4. <strong>HTML Splitter（HTML 切分器）</strong>：
    + <strong>HTMLHeaderTextSplitter（HTML 标题文本切分器）</strong>：基于 HTML 的标题标签（`<h1>` 到 `<h6>`）来切分文本。它的核心逻辑和 Markdown 里的标题切分一样，主要用来提取并保留文章的“层级目录”作为元数据（Metadata）。
    + <strong>HTMLSectionSplitter（HTML 区块切分器）</strong>：基于 HTML 的布局结构（如 `<section>`、`<div>`）或视觉特征（如字体大小）来切分文本。它更适合处理那些大段大段排版、没有明显 h1/h2 标签，但是通过 div 块进行视觉隔离的现代网页。
    + <strong>HTMLSemanticPreservingSplitter（HTML 语义保持切分器）</strong>：“Semantic Preserving” 意为“保持语义完整”。它的核心是为了防止暴力切分把原本一体的结构（比如一个完整的 `<table>` 数据表、一段 `<ul>` 列表、甚至一段 `<code>` 代码块）从中间拦腰斩断，导致大模型读取时上下文错乱。

**注意：**

在构建生产级别的 RAG（检索增强生成）系统时，单一的切分策略往往无法兼顾“语义完整性”和“长度安全性”。业界最标准、最经典的最佳实践，就是将 **“基于文档结构”** 作为第一阶段（粗排提取），将 **“基于文本结构与长度”** 作为第二阶段（精细兜底）。

---

## 周边与核心参数梳理

在执行上述三大策略时，LangChain 提供了两个极其核心的参数来控制切分质量（这不仅是 API 参数，更是 RAG 调优的灵魂）：

+ <strong>chunk_size</strong>：<u>切分块的物理容量上限</u>。在基于长度的策略中，它可能是字符数，也可能是 Token 数；它直接决定了最终入库时每个向量（Embedding）所能承载的信息密度。
+ <strong>chunk_overlap</strong>：<u>相邻文本块之间的重叠容量</u>。它采用了类似数据流处理中的<strong>“滑动窗口”</strong>思想。在物理切断文本时，强制保留一部分上一块的尾部数据，从而防止上下文语义在切割边界处发生断裂。

---

## 工程化代码落地示例

在面试或实际编写数据管道时，建议展示出对 `chunk_size`（分块大小）和 `chunk_overlap`（重叠区域）的控制。重叠区域是为了防止切分动作刚好把一个核心概念从中间斩断，导致上下文丢失。

### 示例 1：一个处理本地高隐私知识库的标准切分范例

```python {title="rag_chunking_pipeline.py"}
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 演示如何在 RAG 系统中使用两阶段文本切分策略，结合 `MarkdownHeaderTextSplitter` 和 `RecursiveCharacterTextSplitter`，实现既保留文档结构又控制块大小的高效文本预处理流程。

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# 模拟一篇本地知识库中，带有层级结构的 Markdown 长文本
markdown_doc = """
# RAG 系统重构指南

## Local-First 本地化架构设计
为了保障核心技术文档的绝对隐私，我们需要构建本地化的知识库基础设施。
(这里假设有 2000 字的详细架构图文字描述...)

## 向量检索的痛点
在传统的文本匹配中，我们经常遇到以下问题：
第一，语义鸿沟...
第二，多语言对齐...
"""

# ==========================================
# 阶段 1：文档结构切分 (MarkdownHeaderTextSplitter)
# 目标：保持章节完整，并将标题层级提取为高价值的 Metadata
# ==========================================
headers_to_split_on = [
    ("#", "H1_Title"),
    ("##", "H2_Title"),
]
md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

# 切分后，你会得到按标题划分的块，并且每个块都携带了诸如 {"H2_Title": "1. Local-First 本地化架构设计"} 这样的元数据
md_header_splits = md_splitter.split_text(markdown_doc)


# ==========================================
# 阶段 2：长度兜底切分 (RecursiveCharacterTextSplitter)
# 目标：防止阶段 1 切出的块过长导致 OOM 或 Token 溢出，进行安全的二级截断
# ==========================================
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,  # 设定 LLM 能够舒服吞下的分块大小
    chunk_overlap=50,  # 截断处的语义缓冲区域
)

# 核心工程思维：将阶段 1 的输出对象 (包含 metadata 的 Document 列表)
# 直接透传给阶段 2 的 split_documents 方法
final_splits = text_splitter.split_documents(md_header_splits)

print(f"最终经过两级管道切分出的 Chunk 数量: {len(final_splits)}")
# final_splits 中的每个 chunk 现在既有完美的大小控制，又完整继承了它的祖先标题 Metadata！
print("示例 Chunk Metadata:", final_splits[0].metadata)
print(
    "示例 Chunk 内容:", final_splits[0].page_content[:200], "..."
)  # 只展示前 200 字以示例

```

**输出结果：**

```powershell
最终经过两级管道切分出的 Chunk 数量: 2
示例 Chunk Metadata: {'H1_Title': 'RAG 系统重构指南', 'H2_Title': '1. Local-First 本地化架构设计'}
示例 Chunk 内容: 为了保障核心技术文档的绝对隐私，我们需要构建本地化的知识库基础设施。
(这里假设有 2000 字的详细架构图文字描述...) ...
```

### 示例 2：日常开发中最常用的三种切分器

```python {title="text_chunking_strategies.py"}
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author         : nanzet
# Description    : RAG数据流：三种核心文本切分策略的最佳实践（Recursive, Token-based, Markdown-based）
# requirements   : pip install langchain-text-splitters tiktoken

import tiktoken
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


def demonstrate_recursive_splitter() -> None:
    """
    演示 RecursiveCharacterTextSplitter（递归字符文本切分器）的使用。

    该切分器是 LangChain 官方推荐的默认选择。它通过递归地尝试不同的分隔符
    （段落 -> 句子 -> 单词），在满足 chunk_size 限制的前提下，尽最大努力保持自然语言的语义完整性。
    """
    print("=== 1. 默认首选：RecursiveCharacterTextSplitter (递归语义切分) ===")
    document = "这是第一段话，非常重要。\n\n这是第二段话，包含了长句子。下周天气不错，我打算和几个朋友开车去湖边露营。\n\n下午我得把特斯拉开去楼下充下电，不然晚上回家就没电了。"

    # 这里的大小指的是“字符数”
    splitter = RecursiveCharacterTextSplitter(chunk_size=30, chunk_overlap=10)
    chunks = splitter.split_text(document)

    print(f"切分结果数量: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1} 内容: {chunk}")
        print(f"Chunk {i + 1} 长度: {len(chunk)} 字符\n")


def demonstrate_token_based_splitter() -> None:
    """
    演示基于 Token 的生产级切分策略。

    【最佳实践】：使用 RecursiveCharacterTextSplitter 配合 tiktoken_encoder。
    既能严格保证产出的 Chunk Token 数量不超过阈值，又能在切分时尽量保持句子的语义完整，避免出现生硬的截断。
    """
    print("=== 2. 精准控制：基于 Token 的降级切分 (Recursive + tiktoken) ===")
    document = "这是第一段话，非常重要。\n\n这是第二段话，包含了长句子。下周天气不错，我打算和几个朋友开车去湖边露营。\n\n下午我得把特斯拉开去楼下充下电，不然晚上回家就没电了。"

    encoding_name = "cl100k_base"
    encoder = tiktoken.get_encoding(encoding_name)

    # 【核心调整】：弃用死板的 CharacterTextSplitter，换用带递归降级能力的 Recursive
    # 这里的 chunk_size=20 和 chunk_overlap=5，指的都是 Token 数量，而非字符！
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=encoding_name, chunk_size=20, chunk_overlap=5
    )

    chunks = splitter.split_text(document)
    print(f"切分结果数量: {len(chunks)}\n")

    for i, chunk in enumerate(chunks):
        tokens = encoder.encode(chunk)
        print(f"Chunk {i + 1} 内容: {chunk}")
        print(f"Chunk {i + 1} 长度: {len(chunk)} 字符 | Token 数量: {len(tokens)}\n")


def demonstrate_markdown_splitter() -> None:
    """
    演示基于 Markdown 文档结构的感知切分策略。

    此策略不仅会将文本按结构块切分，还会自动提取 Markdown 的层级标题（Header），
    并将其作为 Metadata（元数据）注入到每个 Chunk 中，极大增强向量检索的准确度溯源能力。
    """
    print("=== 3. 结构化感知：MarkdownHeaderTextSplitter ===")
    md_document = """
# 部门规章制度
## 考勤管理
早上 9 点打卡。
迟到扣钱。
## 财务报销
每月 10 号前提交发票。
    """
    headers_to_split_on = [
        ("#", "一级标题"),
        ("##", "二级标题"),
    ]

    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    splits = splitter.split_text(md_document)

    print(f"切分结果数量: {len(splits)}")
    for i, split in enumerate(splits):
        print(f"Chunk {i + 1} 内容: {split.page_content}")
        print(f"Chunk {i + 1} Metadata: {split.metadata}\n")


if __name__ == "__main__":
    demonstrate_recursive_splitter()
    demonstrate_token_based_splitter()
    demonstrate_markdown_splitter()

```

<strong>输出结果</strong>：

```powershell
=== 1. 默认首选：RecursiveCharacterTextSplitter (递归语义切分) ===
切分结果数量: 4
Chunk 1 内容: 这是第一段话，非常重要。
Chunk 1 长度: 12 字符

Chunk 2 内容: 这是第二段话，包含了长句子。下周天气不错，我打算和几个朋友
Chunk 2 长度: 29 字符

Chunk 3 内容: 错，我打算和几个朋友开车去湖边露营。
Chunk 3 长度: 18 字符

Chunk 4 内容: 下午我得把特斯拉开去楼下充下电，不然晚上回家就没电了。
Chunk 4 长度: 27 字符

=== 2. 精准控制：基于 Token 的降级切分 (Recursive + tiktoken) ===
切分结果数量: 6

Chunk 1 内容: 这是第一段话，非常重要。
Chunk 1 长度: 12 字符 | Token 数量: 12

Chunk 2 内容: 这是第二段话，包含了长句子。下周天
Chunk 2 长度: 17 字符 | Token 数量: 18

Chunk 3 内容: 子。下周天气不错，我打算和几个朋友
Chunk 3 长度: 17 字符 | Token 数量: 20

Chunk 4 内容: 个朋友开车去湖边露营。
Chunk 4 长度: 11 字符 | Token 数量: 16

Chunk 5 内容: 下午我得把特斯拉开去楼下充下电
Chunk 5 长度: 15 字符 | Token 数量: 19

Chunk 6 内容: 下充下电，不然晚上回家就没电了。
Chunk 6 长度: 16 字符 | Token 数量: 18

=== 3. 结构化感知：MarkdownHeaderTextSplitter ===
切分结果数量: 2
Chunk 1 内容: 早上 9 点打卡。
迟到扣钱。
Chunk 1 Metadata: {'一级标题': '部门规章制度', '二级标题': '考勤管理'}

Chunk 2 内容: 每月 10 号前提交发票。
Chunk 2 Metadata: {'一级标题': '部门规章制度', '二级标题': '财务报销'}
```

---

## 常见踩坑与高频面试点

在 RAG 系统的开发实践中，深入理解这三大策略的局限性并做出正确架构选型，是高级研发岗位的必考内容。

### 高频面试点 1：为何必须进行文本切分？如何设定合理的 Chunk Size 与 Overlap？

+ <strong>考察点</strong>：对向量空间特征密度及上下文边界处理的理解。
+ <strong>满分回答</strong>：切分的根本目的不仅是为了规避大模型上下文窗口的上限，更关键的是提升检索的信噪比（Precision/Recall）。长文本被压缩进单一稠密向量后，局部的关键语义特征会被稀释，导致向量相似度匹配精度大幅下降。设置 `chunk_overlap`（滑动窗口重叠，业内推荐占比通常为 15% 到 25%）是为了防止自然语义在切片物理边界处发生硬性断裂，确保模型接收到的上下文能够平滑衔接，避免断章取义。

### 常见踩坑 1：基于 Length-based 策略控制 Token 时的失效陷阱

+ <strong>痛点场景</strong>：开发者为严格限制 Token 数，使用 `CharacterTextSplitter.from_tiktoken_encoder` 处理大段无换行的密集文本，结果控制台抛出 Created a chunk of size X, which is longer than the specified Y 的警告，并且重叠区（Overlap）完全失效。
+ <strong>工程对策</strong>：`CharacterTextSplitter` 采用单一分隔符（如 \n\n）的硬性逻辑，当遇到无分段的超长句子时，它不具备降级能力，只能强行输出超标块。在生产环境中，需要严格对齐 Token 时，最佳实践是改用 `RecursiveCharacterTextSplitter.from_tiktoken_encoder`。它既具备精确的 Token 计量能力，又保留了向下递归（按句子、单词）的灵活性，彻底杜绝该问题。

### 常见踩坑 2：多语言语料库的 Token 膨胀现象

+ <strong>痛点场景</strong>：处理中文文档时，将 chunk_size 设为 500，预期切出约 500 个汉字，但在调用云端计费接口时发现消耗了超 1000 个 Token。
+ <strong>工程对策</strong>：在底层 BPE（字节对编码）算法下，英文单词与 Token 大致是 1 比 1.3 的关系；但对于中文字符，因 UTF-8 编码机制，一个汉字往往会被切分为 2 到 3 个 Token。因此，在基于长度切分（Length-based）处理纯中文语料时，绝对不能将字符长度等同于 Token 数量，必须显式调用相应的 Tokenizer（如 tiktoken 或开源模型的专属编码器）进行强校验计算。

### 常见踩坑 3：Document structure-based 数据降级时的“范围幻觉”

+ <strong>痛点场景</strong>：使用基础的文本结构策略（Recursive）处理包含多级标题的长 Markdown 文档。切分后，位于末尾的文本块彻底丢失了所属的章节大标题上下文，导致大模型读取该片段时出现严重的回答范围错误（幻觉）。
+ <strong>工程对策</strong>：不能用通用的纯文本切分策略去破坏结构化文件。必须引入 MarkdownHeaderTextSplitter 等文档结构感知组件。它会在物理切分的同时，向上溯源并提取各级标题信息，将其注入到输出 Document 的 Metadata（元数据字典）中。这不仅防止了上下文遗失，更为下游向量数据库的元数据过滤（Metadata Filtering）提供了关键架构支撑。
