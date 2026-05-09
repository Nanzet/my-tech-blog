#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 语雀 Markdown 笔记清洗脚本 (适配 Hugo 博客工作流)
# 使用方法: python scripts/clean_yuque.py content/post/your_post_name.md


import os
import re
import sys


def clean_markdown_content(content: str) -> str:
    """
    底层数据清洗逻辑（复用之前的正则方案）
    """

    # 1. 终极剥洋葱：提取单反引号内的 HTML 和加粗标记
    def fix_code_block(match):
        inner = match.group(1)
        m = re.match(
            r"^((?:<[^>]+>|\*\*|__|\s)*)(.*?)((?:<[^>]+>|\*\*|__|\s)*)$",
            inner,
            flags=re.DOTALL,
        )
        if m:
            prefix, core, suffix = m.group(1), m.group(2), m.group(3)
            if not core.strip():
                return f"`{inner}`"
            return f"{prefix}`{core}`{suffix}"
        return f"`{inner}`"

    content = re.sub(r"(?<!`)`([^`]+?)`(?!`)", fix_code_block, content)

    # 2. 修复加粗语法包裹 HTML 标签导致失效
    content = re.sub(
        r"\*\*(<[^>]+>[^\*\n]*?</[^>]+>)\*\*", r"<strong>\1</strong>", content
    )

    # 3. 修复全角标点导致边界失效
    content = re.sub(
        r"\*\*([^\s\*][^\*\n]*?[^\s\*]|[^\s\*])\*\*(?=[^\s`<])",
        r"<strong>\1</strong>",
        content,
    )

    # 4. 清洗标题编号 (如：## **1.1 标题** -> ## 标题)
    # 注意：这里会处理 H1 到 H6 的所有编号
    header_pattern = r"^(#{1,6})\s*(<[^>]+>)?\s*(?:\*\*|__)?\s*\d+(?:\.\d+)*(?:[.、])?\s*(?:\*\*|__)?\s*"
    content = re.sub(header_pattern, r"\1 \2", content, flags=re.MULTILINE)

    return content


def adjust_header_levels(content: str) -> str:
    """
    检测最大级别的标题是否为二级标题。如果不是，则整体升降级。
    （双重防护版：正则 \s+ 强制要求空格 + 自动跳过 Markdown 代码块）
    """
    lines = content.split("\n")

    # 1. 扫描寻找最高级别的标题
    min_level = 7  # 初始化一个不可能的级别
    has_header = False
    in_code_block = False

    for line in lines:
        # 检测是否进入或离开代码块
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue

        # 只有在非代码块区域，才去识别标题
        if not in_code_block:
            # 严格规范：# 后面必须有空白字符 \s+
            m = re.match(r"^(#+)\s+", line)
            if m:
                has_header = True
                level = len(m.group(1))
                if level < min_level:
                    min_level = level

    # 如果没有标题，或者最高级别已经是 H2 (##)，则无需调整
    if not has_header or min_level == 2:
        return content

    # 2. 计算偏移量 (目标是让最高级别变成 2)
    offset = 2 - min_level

    new_lines = []
    in_code_block = False  # 替换时重新重置状态

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue

        if not in_code_block:
            # 捕获 # 号部分(group 1) 和 后面的空格+文字部分(group 2)
            m = re.match(r"^(#+)(\s+.*)", line)
            if m:
                current_level = len(m.group(1))
                # 计算新级别，同时防止越界变成 0 级标题（即没有 #）
                new_level = max(1, current_level + offset)
                new_lines.append("#" * new_level + m.group(2))
                continue

        # 非标题行或代码块内的行，原样保留
        new_lines.append(line)

    return "\n".join(new_lines)


def process_file(filepath: str):
    """
    处理单个 Hugo Markdown 文件
    """
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # --- 1. 分离 Hugo 的 Frontmatter 和 正文 ---
    # 使用正则严格匹配文件开头的 --- yaml --- 区块
    match = re.match(r"^\s*(---\r?\n.*?\r?\n---\r?\n)(.*)", text, flags=re.DOTALL)

    if match:
        frontmatter = match.group(1)
        body = match.group(2)
        print("✅ 成功提取 Hugo Frontmatter (头信息保护)")
    else:
        # 如果没有 Frontmatter，则全是正文
        frontmatter = ""
        body = text
        print("⚠️ 未检测到 Hugo Frontmatter，将处理全文")

    # --- 2. 标题级别调整 (+#) ---
    body = adjust_header_levels(body)
    print("✅ 标题层级校验与调整完毕")

    # --- 3. 语法清洗与编号去除 ---
    body = clean_markdown_content(body)
    print("✅ Markdown 杂乱标签与编号清洗完毕")

    # --- 4. 重新组合并保存 ---
    final_text = frontmatter + body

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"🎉 处理完成! 干净的数据已保存至: {filepath}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用说明: python scripts/clean_yuque.py <markdown文件路径>")
        sys.exit(1)

    target_file = sys.argv[1]
    process_file(target_file)
