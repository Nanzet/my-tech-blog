---
title: "个人项目-答题系统 Git 提交规范指南"
date: 2026-01-27T22:17:13+08:00
slug: "personal-project-git-commit"
image: ""
categories:
    - 技术
tags:
    - Git 规范
draft: false
---
在日常开发过程中，每个人都有自己的代码开发和提交风格。为了方便管理和问题追溯，建立一套标准的 Git 提交规范是非常重要的。

考虑到这是**个人独立项目-答题系统**，这套规范在保持“行业标准（Conventional Commits）”专业性的同时，去掉了企业级开发中繁琐的流程（如必须关联 Jira ID 等），专注于清晰和实用 。

建议将此内容保存在项目根目录的 `CONTRIBUTING.md`或 `docs/GUIDE.md` 中，作为备忘。

---

## ReviewOS 项目 Git 提交规范

### 提交格式公式

每次提交（Commit）建议遵循以下标准格式：

```plain
<type>(<scope>): <subject>
```

* **type (必填)** ：本次提交的类型（如新增功能、修复 Bug）。
* **scope (选填)** ：本次修改影响的范围（如 backend, etl, frontend）。
* **subject (必填)** ：简短的中文描述（不超过 50 字）。

 **示例** **：**`feat(etl): 增加语雀图片自动转存功能`

---

### Type 类型对照表 (保留英文关键词)

兼容主流 IDE 插件和图标显示。

|   **Type**   | **中文含义** | **适用场景**                                    |
| :----------------: | :----------------- | ----------------------------------------------------- |
|   **feat**   | ✨ 新功能          | 开发了新的功能模块 (Feature)                          |
|   **fix**   | 🐛 修补 Bug        | 修复了代码中的错误                                    |
|   **docs**   | 📚 文档            | 仅修改了文档 (README, 注释, Wiki)                     |
|  **style**  | 💄 格式            | 代码格式化、空格、分号等 (不影响代码运行)             |
| **refactor** | ♻️ 重构         | 代码重构 (既不是新增功能，也不是修 Bug)               |
|   **perf**   | 🚀 性能            | 提升性能的代码更改                                    |
|   **test**   | 🧪 测试            | 增加测试代码或修正现有测试                            |
|  **chore**  | 🔧 杂务            | 构建过程、依赖库更新、配置文件修改 (.gitignore, .env) |
|  **revert**  | ⏪ 回滚            | 撤销上一次的 Commit                                   |

---

### Scope 范围定义

针对项目结构，建议定义标准 Scope，方便快速定位修改位置。例如，ReviewOS 使用的 scope：

* **backend** ：FastAPI 后端核心代码 (main.py, routers)
* **db** ：数据库模型 (models.py) 或 迁移变动
* **etl** ：数据清洗脚本 (scripts/etl.py)
* **infra** ：基础设施配置 (docker-compose, Dockerfile, MinIO)
* **frontend** ：(未来阶段) 前端 Vue 代码
* **global** ：影响整个项目的变动 (如 .gitignore, README)

---

### Subject 书写建议

1. **使用中文** ：简单、直接。
2. **动词开头** ：推荐使用“新增”、“修改”、“修复”、“删除”、“优化”等词汇。
3. **结尾无句号** ：保持简洁。
4. **客观描述** ：说明“做了什么”，而不是“怎么做的”。

---

### 提交示例 (Copy & Paste)

  可以参考以下针对 ReviewOS 开发过程的真实示例：

**场景一：ETL 脚本**

`feat(etl): 完成语雀 Markdown 解析与图片私有化逻辑`

**场景二：把密码改成环境变量**

`refactor(backend): 将 MinIO 配置改为读取 .env 环境变量`

**场景三：修正了一个正则匹配的 Bug**

`fix(etl): 修复标题正则无法匹配带空格的数字编号`

**场景四：更新忽略文件**

`chore(global): 更新 .gitignore 以忽略日志和数据目录`

**场景五：添加新的 Python 依赖**

`chore(backend): 安装 python-dotenv 并更新 requirements.txt`

---

### 实用工具推荐

如果觉得每次手打这些前缀很麻烦，强烈推荐在 VS Code 中安装插件： Conventional Commits 。

安装后，只需要按流程选择：

1. 选 `feat`
2. 填 `etl`
3. 填 `增加图片上传功能` ......

插件会自动帮你生成标准的：`feat(etl): 增加图片上传功能`。

<img src="/image/个人项目Git提交规范和vscode插件/1769525248381.png" class="about-img">

## VSCode **Conventional Commits 插件配置说明**

VS Code `settings.json` 配置如下：主要用来配置“范围 (Scopes)”和“交互行为”：

```json
{
    // ------ vivaxy.vscode-conventional-commits 修正版配置 ------
    // 关闭自动提交，让你有机会最后检查一遍
    "conventionalCommits.autoCommit": false,
    // 是否弹出“选择/输入作用域 (Scope)”的提示。如果你的项目不需要精细到区分模块，可以设为 false。
    "conventionalCommits.promptScopes":true,
    // 预设你的作用域列表。比如填入 ["backend", "frontend", "docs"]，这样你每次只需点击选择，不用手动敲字。
    "conventionalCommits.scopes": [
        "backend",
        "etl",
        "docs",
        "infra",
        "global",
        "db"
    ],
    // 是否提示输入详细描述 (Body)。
    "conventionalCommits.promptBody":false,
    // 是否提示输入页脚 (Footer)，通常用来关联 Issue 号（比如 Fixes #123）。
    "conventionalCommits.promptFooter":false,
    // 是否提示跳过 CI 构建（比如自动在提交信息里加上 [ci skip]）。
    "conventionalCommits.promptCI":false,
    // 开启 Gitmoji (在类型和范围后，多一步选择表情的环节)，默认为 true，嫌麻烦可以关掉
    "conventionalCommits.gitmoji": true,
    // 表情格式：使用 "emoji" (✨) 而不是 "code" (:sparkles:)
    "conventionalCommits.emojiFormat": "emoji",

    // 终极预览模式：如果你觉得在顶部的一个小输入框里写长篇大论的详细描述（Body）很难受，开启这个选项。
    // 当需要输入详细描述时，它会新开一个独立的文本编辑器标签页，
    // 让你像写普通文本一样自由编辑多行提交信息，保存关闭标签页后才会执行提交。
    "conventionalCommits.showEditor":false,
    // --------------------------------------------------------
}
```

---

### 效果说明

配置完成后，当你再次使用 `Conventional Commits` 命令时：

1. **Scope 菜单**：会直接读取 `settings.json` 里的 `backend`, `etl` 等选项。
2. **最终结果**：生成的提交信息会非常规范，例如 `feat(etl): ✨ 完成数据清洗脚本`（取决于你是否开启了 `gitmoji` 选项）。

### 使用方法

1. 在 vscode 中使用组合键 command + shift + p 呼出命令面板，选择”约定式提交“
2. 第 1 步，选择类型（如选择 fix 错误修复）

<img src="/image/个人项目Git提交规范和vscode插件/1776417317431.png" class="about-img">

3. 第 2 步，选择作用域（如选择后端）

<img src="/image/个人项目Git提交规范和vscode插件/1776417349009.png" class="about-img">

4. 第 3 步，填写提交信息内容--描述

<img src="/image/个人项目Git提交规范和vscode插件/1776417613620.png" class="about-img">


该方案能保证团队协作时规范的一致性，相关视频教程 👉🏻 [Easy Conventional Commits in VSCode](https://www.youtube.com/watch?v=lwGcnDgwmFc)（详细介绍了如何在 VSCode 中轻松使用 Conventional Commits 插件进行规范化提交）。
