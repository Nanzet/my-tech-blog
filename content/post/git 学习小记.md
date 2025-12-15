---
title: "git 学习小记"
date: 2020-02-14 17:03:37
slug: "learning-git-commands"
image: ""
categories:
    - 技术
tags:
    - git
draft: false
---
1、初始化一个Git仓库，使用**git init**命令。可以将某个新建的目录变成Git可以管理的仓库。

2、提交修改和提交新文件到Git仓库，一样分两步：

* 使用命令**git add `<file>`** ，注意，可反复多次使用，添加多个文件；
* 使用命令**git commit -m "说明注释"** ，完成。

3、**git status**可查看工作区状态，**git diff**可查看版本修改内容。

4、**git add**的各种区别：

```bash
git add -A   // 添加所有改动
git add *     // 添加新建文件和修改，但是不包括删除
git add .    // 添加新建文件和修改，但是不包括删除
git add -u   // 添加修改和删除，但是不包括新建文件
```

**git add . 和 git add * 区别：**
&ensp;git add . 会把本地所有untrack的文件都加入暂存区，并且会根据.gitignore做过滤，但是git add * 会忽略.gitignore把任何文件都加入。

5、在 commit 前撤销 add:

```bash
git reset <file> // 撤销提交单独文件
git reset        // unstage all due changes
```

6、版本回退：

* HEAD指向的版本就是当前版本，因此，Git允许我们在版本的历史之间穿梭，使用命令git reset --hard commit_id。
* 穿梭前，用git log可以查看提交历史，以便确定要回退到哪个版本。
* 要重返未来，用git reflog查看命令历史，以便确定要回到未来的哪个版本。

7、理解： 需要提交的文件修改通通放到暂存区，然后，一次性提交暂存区的所有修改。
![](https://cdn.jsdelivr.net/gh/nanzet/nanzet-imgs/images/git.jpg)

8、git管理的是修改而不是文件：每次修改，如果不用git add到暂存区，那就不会加入到commit中。

9、撤销修改：
**场景1：**
&ensp;改乱了工作区某个文件的内容，想直接丢弃工作区的修改时，用命令git checkout -- file。

**场景2：**
&ensp;不但改乱了工作区某个文件的内容，还添加到了暂存区时，想丢弃修改，分两步，第一步用命令git reset HEAD `<file>`，就回到了场景1，第二步按场景1操作。

**场景3：**
&ensp;已经提交了不合适的修改到版本库时，想要撤销本次提交，参考版本回退，不过前提是没有推送到远程库。

10、删除文件流程：

* 在本地仓库删除指定文件：
  `git rm <filename>`
* 删除本地仓库文件夹：（先进入该文件夹所在目录在执行命令）
  `git rm -r 文件夹/`
* 提交修改
  `git commit -m "删除文件夹"`
* 推送到远程仓库
  `git push    # origin master`

**注：git rm命令**

```bash
git rm -h
用法：git rm [<选项>] [--] <文件>...
    -n, --dry-run         演习
    -q, --quiet           不列出删除的文件
    --cached              只从索引区删除
    -f, --force           忽略文件更新状态检查
    -r                    允许递归删除
    --ignore-unmatch      即使没有匹配，也以零状态退出
```

11、从远程库克隆：
&ensp;例如已经在gitea创建了名为PE-TOOL的仓库并勾选了Initialize this repository with a README。
&ensp;使用git clone克隆一个本地库：
`git clone http://xxxx/Nanzet/PE-TOOL.git`
