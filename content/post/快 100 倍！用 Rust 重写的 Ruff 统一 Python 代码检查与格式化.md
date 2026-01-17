---
title: "快 100 倍！用 Rust 重写的 Ruff 统一 Python 代码检查与格式化"
date: 2026-01-17T15:04:42+08:00
slug: "vscode-ruff-configuration"
image: ""
categories:
    - 技术
tags:
    - vscode
    - ruff
draft: false
---
## 前言：受够了 Python 工具链的“战国时代"

<img src="/image/快100倍！用Rust重写的Ruff统一Python代码检查与格式化/1768633780904.png" class="about-img">

作为一个多年 Python 开发者，我的项目里通常需要安装一大堆工具：

* **Black** 用来格式化；
* **Isort** 用来给 Import 排序；
* **Flake8** 用来检查代码错误；
* **Pylint** 用来......给我添堵（比如无休止的 `Missing docstring`）。

这就导致一个问题：**慢，且配置繁琐**。很烦😣...直到我遇见了  **Ruff** 。

## 什么是 Ruff？为什么它能快 100 倍？

简单说，Ruff 是一个用 **Rust** 编写的 Python 代码检查器和格式化工具。
它的核心卖点就两个：

1. **极速** ：比传统的 Python 实现（如 Flake8）快 10-100 倍。
2. **All-in-One** ：一个工具直接替代 Flake8、Pylint、Isort、Black、Pyupgrade 等十几个工具。

## 实战配置：告别繁琐，一份 `pyproject.toml` 走天下

Ruff 完美支持现代 Python 的 `pyproject.toml` 配置。这是我目前在用的“舒适区”配置，兼顾了代码规范和开发体验（拒绝死板的 79 字符限制，拒绝强制文档注释）。

我的 `pyproject.toml` 推荐配置：（把 Flake8/Pylint 禁用掉）

```toml
[tool.ruff]
# 1. 宽屏时代，把行宽放宽到 120
line-length = 120

# 2. 排除不需要检查的目录
exclude = [".git", "__pycache__", "build", "dist"]

[tool.ruff.lint]
# 3. 启用规则集：这是 Ruff 的精华
# E, W: 基础错误/警告 (替代 Flake8)
# F: 核心语法检查 (替代 Flake8)
# I: 自动导入排序 (替代 Isort)
# UP: 语法自动升级 (例如自动把 format() 转为 f-string)
select = ["E", "W", "F", "I", "UP"]

# 4. 忽略规则：打造无干扰开发环境
ignore = [
    "E501", # 虽然设了 120，但偶尔超一点不要报错，交给 Formatter 自动折行就好
    "F401", # 忽略未使用的导入（如 import models 只为建表）
]

# 重点：我不开启 "D" (pydocstyle) 规则集，
# 所以再也不会有 "Missing docstring" 这种烦人的提示了！

[tool.ruff.format]
# 格式化风格（类似 Black）
quote-style = "double"
```

## VS Code 终极集成：保存即重构+Jupyter Notebook 单元格格式化

光有配置不行，必须配合 VS Code 实现“无感优化”。这是我的 `settings.json` 配置，它的神奇之处在于：**当你按下 `Ctrl+S` 时，它不仅格式化代码，还会自动把你的 `import` 整理得整整齐齐。**

```json
"[python]": {
        // 设置 Ruff 为默认格式化工具
        "editor.defaultFormatter": "charliermarsh.ruff",
        // 保存时自动格式化
        "editor.formatOnSave": true,
        // 保存时触发的代码动作（这是 Ruff 的杀手锏）
        "editor.codeActionsOnSave": {
            // 自动排序和清理 import (替代 isort)
            "source.organizeImports": "explicit",
            // 自动修复可自动修复的 Lint 错误 (如升级语法、删除未使用变量)
            "source.fixAll": "explicit"
        }
    },
    // 开启 Notebook 保存时自动格式化
    "notebook.formatOnSave.enabled": true,
    // 针对 Notebook 的保存动作
    "notebook.codeActionsOnSave": {
        // 保存 Notebook 时自动整理每个 Cell 的 import
        "source.organizeImports": "explicit",
        // 保存时自动修复 Notebook 中的 Lint 错误
        "source.fixAll": "explicit"
    },
```

## 效果演示

**Before:**

```python
import sys, os # 顺序乱了
x = "这是一个...非常长的字符串..." # 以前会报 E501
print("Hello {}".format(name)) # 老式写法
```

**After (按下保存键后):**
Ruff 瞬间完成了以下操作：

1. `import` 自动分行并排序。
2. 老式 `.format()` 自动升级为 f-string (得益于 `UP` 规则)。
3. 长字符串保留（因为忽略了 E501），代码逻辑保持清晰。

## 避坑小贴士

如果你发现配置没生效，可以在终端运行 `ruff check --show-settings`，它会告诉你当前到底读取了哪个配置文件，这招在排查问题时非常管用。

`pip install ruff`
