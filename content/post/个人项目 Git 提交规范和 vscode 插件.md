---
title: "个人独立项目 Git 提交规范指南"
date: 2026-01-27T22:17:13+08:00
slug: "personal-project-git-commit"
image: ""
categories:
    - 技术
tags:
    - Git 规范
draft: false
---
考虑到这是**个人独立项目-答题系统**，这套规范在保持“行业标准（Conventional Commits）”专业性的同时，去掉了企业级开发中繁琐的流程（如必须关联 Jira ID 等），专注于清晰和实用 。

建议将此内容保存在项目根目录的 `CONTRIBUTING.md `或 `docs/GUIDE.md` 中，作为备忘。

---

## ReviewOS 项目 Git 提交规范

### 提交格式公式

每次提交（Commit）请遵循以下标准格式：

```plain
<type>(<scope>): <subject>
```

* **type (必填)** ：本次提交的类型（如新增功能、修复 Bug）。
* **scope (选填)** ：本次修改影响的范围（如 backend, etl, frontend）。
* **subject (必填)** ：简短的中文描述（不超过 50 字）。

 **示例** **：**`feat(etl): 增加语雀图片自动转存功能`

---

### Type 类型对照表 (保留英文关键词)

为了兼容主流 IDE 插件和图标显示，我们保留英文 Type ，但描述部分使用中文。

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

### Scope 范围定义 (ReviewOS 专用)

针对项目结构，建议使用以下标准 Scope，方便快速定位修改位置：

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

### 💡实用工具推荐

如果觉得每次手打这些前缀很麻烦，强烈推荐在 VS Code 中安装插件： Conventional Commits 。

安装后，只需要按流程选择：

1. 选 `feat`
2. 填 `etl`
3. 填 `增加图片上传功能` ......

插件会自动帮你生成标准的：`feat(etl): 增加图片上传功能`。

![1769525248381](image/个人独立项目Git提交规范指南/1769525248381.png)

## VSCode **Conventional Commits 插件配置说明**

### 第一步：VS Code 配置 (`settings.json`)

`settings.json` 主要用来配置“范围 (Scopes)”和“交互行为”，请用下面的内容替换之前的错误配置：

```json
{
  // --- vivaxy.vscode-conventional-commits 修正版配置 ---

  // 1. 关闭自动提交，让你有机会最后检查一遍
  "conventionalCommits.autoCommit": false,

  // 2. 常用 Scope (范围)，对应你的项目结构
  "conventionalCommits.scopes": [
    "backend",
    "etl",
    "docs",
    "infra",
    "global",
    "db"
  ],

  // 3. 开启 Gitmoji (在类型和范围后，多一步选择表情的环节)
  "conventionalCommits.gitmoji": true,

  // 4. 表情格式：使用 "emoji" (✨) 而不是 "code" (:sparkles:)
  // 注意：如果提示 emoji 选项无效，请删除此行，使用默认即可
  "conventionalCommits.emojiFormat": "emoji"
}
```

### 第二步：项目根目录新建 `commitlint.config.js`

这是 **Conventional Commits** 插件读取“自定义类型”的地方。请在 `reviewos` 根目录下新建这个文件，并粘贴以下内容。这能完美实现你想要的 **中文菜单** **。**

```javascript
// commitlint.config.js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  // 这里定义的 prompt 就是 VS Code 插件弹出的菜单内容
  prompt: {
    questions: {
      type: {
        description: "选择你要提交的更改类型",
        enum: {
          feat: {
            description: '✨ 新功能 (Feature)',
            title: 'Features',
            emoji: '✨',
          },
          fix: {
            description: '🐛 修复 Bug (Fix)',
            title: 'Bug Fixes',
            emoji: '🐛',
          },
          docs: {
            description: '📚 文档 (Documentation)',
            title: 'Documentation',
            emoji: '📚',
          },
          style: {
            description: '💎 格式变动 (不影响代码运行)',
            title: 'Styles',
            emoji: '💎',
          },
          refactor: {
            description: '♻️ 代码重构 (无新功能/无Bug修复)',
            title: 'Code Refactoring',
            emoji: '♻️',
          },
          perf: {
            description: '🚀 性能优化 (Performance)',
            title: 'Performance Improvements',
            emoji: '🚀',
          },
          test: {
            description: '🧪 增加测试 (Tests)',
            title: 'Tests',
            emoji: '🧪',
          },
          chore: {
            description: '🔧 构建/依赖/工具变动 (Chores)',
            title: 'Chores',
            emoji: '🔧',
          },
          revert: {
            description: '⏪ 回退代码 (Reverts)',
            title: 'Reverts',
            emoji: '⏪',
          },
        },
      },
    },
  },
};
```

---

### 💡 效果说明

配置完成后，当你再次使用 `Conventional Commits` 命令时：

1. **Scope 菜单**：会直接读取 `settings.json` 里的 `backend`, `etl` 等选项。
2. **Type 菜单**：插件会自动读取 `commitlint.config.js`，显示如果你定义的  “ ✨ 新功能 (Feature)” 这样的中文选项。
3. **最终结果**：生成的提交信息会非常规范，例如 `feat(etl): ✨ 完成数据清洗脚本`（取决于你是否开启了 `gitmoji` 选项）。

这个方案虽然多了一个文件，但它是该插件官方支持的“正道”，且能保证团队协作时规范的一致性。

这里有一个视频教程，详细介绍了如何在 VSCode 中轻松使用 Conventional Commits 插件进行规范化提交： [Easy Conventional Commits in VSCode](https://www.youtube.com/watch?v=lwGcnDgwmFc)
