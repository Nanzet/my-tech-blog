#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author         : nanzet
# Description    : 语雀 Markdown 笔记清洗脚本，已兼容处理中文大写编号(如"一、")及多余空格 (适配 Hugo 博客工作流)
# 使用方法: python scripts/clean_yuque.py content/post/your_post_name.md

import os
import re
import sys


def clean_markdown_content(content: str) -> str:
    """
    底层数据清洗逻辑（复用之前的正则方案并升级标题编号处理）
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

    # 4. 清洗标题编号 (如：## **1.1 标题** -> ## 标题, ## 一、 标题 -> ## 标题)
    # 核心优化：支持阿拉伯数字 (1., 1.1, 1、) 和中文大写数字 (一、, 二、, 十、)
    number_pattern = r"(?:\d+(?:\.\d+)*(?:[.、])?|[一二三四五六七八九十百千万]+、)"

    # 组合正则，利用 \s* 贪婪匹配吃掉所有冗余空格
    header_pattern = (
        rf"^(#{{1,6}})\s*(<[^>]+>)?\s*(?:\*\*|__)?\s*{number_pattern}\s*(?:\*\*|__)?\s*"
    )

    def replace_header(m):
        """
        自定义替换回调函数，确保替换后的前缀格式规整，不会残留双空格
        """
        h_level = m.group(1)
        html_tag = m.group(2) if m.group(2) else ""
        # 组合 #号 和可能的标签，去除两端杂余空格后加上唯一标准空格
        return f"{h_level} {html_tag}".strip() + " "

    content = re.sub(header_pattern, replace_header, content, flags=re.MULTILINE)

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
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue

        if not in_code_block:
            m = re.match(r"^(#+)\s+", line)
            if m:
                has_header = True
                level = len(m.group(1))
                if level < min_level:
                    min_level = level

    if not has_header or min_level == 2:
        return content

    # 2. 计算偏移量 (目标是让最高级别变成 2)
    offset = 2 - min_level

    new_lines = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue

        if not in_code_block:
            m = re.match(r"^(#+)(\s+.*)", line)
            if m:
                current_level = len(m.group(1))
                new_level = max(1, current_level + offset)
                new_lines.append("#" * new_level + m.group(2))
                continue

        new_lines.append(line)

    return "\n".join(new_lines)


def process_file(filepath: str):
    """
    处理单个 Hugo Markdown 文件
    """
    if not os.path.exists(filepath):
        print(f"[Error] 文件不存在: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # --- 1. 分离 Hugo 的 Frontmatter 和 正文 ---
    match = re.match(r"^\s*(---\r?\n.*?\r?\n---\r?\n)(.*)", text, flags=re.DOTALL)

    if match:
        frontmatter = match.group(1)
        body = match.group(2)
        print("[Success] 成功提取 Hugo Frontmatter (头信息保护)")
    else:
        frontmatter = ""
        body = text
        print("[Warning] 未检测到 Hugo Frontmatter，将处理全文")

    # --- 2. 标题级别调整 (+#) ---
    body = adjust_header_levels(body)
    print("[Success] 标题层级校验与调整完毕")

    # --- 3. 语法清洗与编号去除 ---
    body = clean_markdown_content(body)
    print("[Success] Markdown 杂乱标签与各类编号清洗完毕")

    # --- 4. 重新组合并保存 ---
    final_text = frontmatter + body

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"[Success] 处理完成! 干净的数据已保存至: {filepath}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用说明: python scripts/clean_yuque.py <markdown文件路径>")
        sys.exit(1)

    target_file = sys.argv[1]
    process_file(target_file)
