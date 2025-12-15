---
title: "解决 VScode 自动将 lambda 表达式转换为 def 的问题"
date: 2020-09-23 21:47:45
slug: "VSCode-python-lambda"
image: "https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200923235431.jpg"
categories:
    - 技术
tags:
    - VSCode
    - Python 
draft: false
---
### 1. Alt + Shift + F

&ensp;查看左下角显示，找到当前格式化代码使用的是autopep8。

### 2. 修改配置

[官方文档](https://pypi.org/project/autopep8/)配置说明：

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200923234614.jpg)

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200923234903.jpg)

#### 3. 解决方案

&ensp;在项目的根目录下，新建个.pep8的文件，里面的内容如下：

```pep8
[pycodestyle]
ignore = E731
```

&ensp;尝试在VScode内格式化代码，lambda表达式未被转换！
