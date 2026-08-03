---
title: "Git 如何修正错误的历史提交信息"
date: 2026-08-03T15:06:29+08:00
lastmod: 2026-08-03T15:06:29+08:00
slug: ""
image: ""
categories:
    - 技术
tags:
    - Git
draft: false
---

## 前言

在使用 Git 提交代码时，有时会因为复制粘贴或命令输入错误，将整条 Git 命令写进提交信息。

例如，原本想执行：

```bash
git commit -m "feat: 添加 Nuclei JSONL 解析器"
```

但最终的 Git 历史却显示为：

```text
git commit -m "feat: 添加 Nuclei JSONL 解析器"
```

如示例下图：

<img src="/image/Git如何修正错误的历史提交信息/1785740877316.png" width="50%" />

正确的提交信息应该是：

```text
feat: 添加 Nuclei JSONL 解析器
```

本文记录如何根据提交所处位置和是否已经推送，安全修正 Git 提交信息。

## 一、先判断属于哪种情况

修改前先回答两个问题：

1. 写错的是最新一条提交，还是更早的历史提交？
2. 该提交是否已经推送到远程仓库？

查看最近提交：

```bash
git log --oneline -10
```

查看远程仓库：

```bash
git remote -v
```

查看当前分支是否跟踪远程分支：

```bash
git branch -vv
```

常见处理方式如下：

| 场景 | 建议方法 |
| --- | --- |
| 最新提交写错 | `git commit --amend` |
| 本地的历史提交写错 | `git rebase -i` |
| 已推送但尚未与他人共享 | rebase 后 `git push --force-with-lease` |
| 已推送且有多人共享 | 优先保留历史，先与协作者沟通 |

## 二、修改最新一条提交

如果错误提交就是当前 `HEAD`，可以直接执行：

```bash
git commit --amend -m "feat: 添加 Nuclei JSONL 解析器"
```

验证结果：

```bash
git log -1 --oneline
```

`--amend` 会重新生成该提交，因此提交哈希也会变化。

## 三、修改更早的历史提交

如果错误提交后面已经还有多条新提交，不能只使用 `git commit --amend`，而应使用交互式 rebase。

### 1. 确保工作区干净

```bash
git status
```

建议在没有未提交修改时重写历史。如果仍有改动，先提交、暂存或妥善处理。

### 2. 建立备份分支

```bash
git branch backup-before-reword
```

该命令不会复制文件，只会为当前提交增加一个备份引用。即使 rebase 操作失误，也可以从该分支找回修改前的历史。

### 3. 找到错误提交的父提交

查看日志：

```bash
git log --oneline --reverse
```

上图示例中错误提交为：

```text
9d05142 git commit -m "feat: 添加 Nuclei JSONL 解析器"
```

它的父提交为：

```text
bf2673b
```

因此可以执行：

```bash
git rebase -i bf2673b
```

也可以不手动查找父提交，直接使用：

```bash
git rebase -i 9d05142^
```

`^` 表示该提交的父提交。

### 4. 将 `pick` 改为 `reword`

编辑器会显示类似：

```text
pick 9d05142 git commit -m "feat: 添加 Nuclei JSONL 解析器"
pick e2667d1 feat: 标准化 Nuclei CVE 编号并补充 Grafana 样本
pick 56445f2 feat: 添加本地漏洞知识模型与 CVE Repository
```

只修改错误提交所在行：

```text
reword 9d05142 git commit -m "feat: 添加 Nuclei JSONL 解析器"
pick e2667d1 feat: 标准化 Nuclei CVE 编号并补充 Grafana 样本
pick 56445f2 feat: 添加本地漏洞知识模型与 CVE Repository
```

保存并关闭文件。

### 5. 输入正确的提交信息

Git 会再次打开编辑器，将原提交信息替换为：

```text
feat: 添加 Nuclei JSONL 解析器
```

保存并关闭后，Git 会重新应用该提交之后的所有提交。

## 四、在 VS Code 中完成交互式 rebase

如果执行 `git rebase -i` 后没有弹出 VS Code，可以为本次命令指定编辑器：

```bash
GIT_SEQUENCE_EDITOR="code --wait" \
GIT_EDITOR="code --wait" \
git rebase -i 9d05142^
```

其中：

- `GIT_SEQUENCE_EDITOR` 用于编辑 rebase 任务列表。
- `GIT_EDITOR` 用于编辑新的提交信息。
- `code --wait` 表示 Git 会等待 VS Code 文件被关闭后再继续。

如果希望长期使用 VS Code 作为 Git 编辑器：

```bash
git config --global core.editor "code --wait"
```

## 五、遇到冲突怎么处理

修改提交信息通常不会产生文件冲突，但如果后续历史比较复杂，仍可能遇到冲突。

查看当前状态：

```bash
git status
```

解决冲突后暂存文件：

```bash
git add <已解决的文件>
```

继续 rebase：

```bash
git rebase --continue
```

如果不想继续，可以返回 rebase 开始前的状态：

```bash
git rebase --abort
```

## 六、验证修改结果

查看历史：

```bash
git log --oneline --reverse
```

检查工作区：

```bash
git status
```

![1785741217939](image/Git如何修正错误的历史提交信息/1785741217939.png)

如果项目包含测试，建议再运行一次全量回归：

```bash
uv run pytest -v
```

交互式 rebase 会重新生成错误提交及其后的所有提交，因此它们的哈希都会变化，但项目文件内容不应因为仅修改提交信息而变化。

## 七、如果历史已经推送到远程

重写本地历史后，普通 `git push` 会被拒绝，因为本地和远程的提交哈希已不同。

如果确认该分支只由自己使用，可以执行：

```bash
git push --force-with-lease
```

优先使用 `--force-with-lease`，不要直接使用 `--force`。前者会在远程分支已经被其他人更新时拒绝覆盖，能够降低误删他人提交的风险。

如果分支已经与其他人共享，不应自行重写历史。先与协作者沟通，否则其他人本地的提交历史会与远程分支分叉。

## 八、常见误区

### 误区 1：对历史提交直接使用 `--amend`

`git commit --amend` 只会修改最新一条提交，不能直接修改更早的提交。

### 误区 2：修改后发现所有提交哈希都变了

这是正常现象。Git 提交哈希由提交内容、父提交和提交元数据共同决定。一条历史提交被替换后，后续提交的父提交也会变化，因此后续哈希会连锁变化。

### 误区 3：重写共享分支后直接强制推送

这可能覆盖其他人的提交。共享分支必须先协调，并且优先使用 `--force-with-lease`。

## 九、本次场景的完整命令

在仓库未配置远程地址、工作区干净的前提下，可以使用：

```bash
git branch backup-before-reword
git rebase -i 9d05142^
```

在 rebase 列表中将：

```text
pick 9d05142 git commit -m "feat: 添加 Nuclei JSONL 解析器"
```

改为：

```text
reword 9d05142 git commit -m "feat: 添加 Nuclei JSONL 解析器"
```

然后将提交信息替换为：

```text
feat: 添加 Nuclei JSONL 解析器
```

最后验证：

```bash
git log --oneline --reverse
git status
uv run pytest -v
```

## 总结

修正 Git 提交信息的核心原则是：

```text
最新提交
→ git commit --amend

本地历史提交
→ git rebase -i + reword

已推送的私有分支
→ 重写后 git push --force-with-lease

多人共享分支
→ 先沟通，不要擅自重写历史
```

交互式 rebase 并不只是“修改一行文字”，而是重新生成从目标提交开始的历史。在操作前确认工作区、远程状态并建立备份分支，可以让这类修正更安全、可恢复。
