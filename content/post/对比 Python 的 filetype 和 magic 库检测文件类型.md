---
title: "对比 Python 的 Filetype 和 Magic 库检测文件类型"
date: 2020-09-17 21:47:45
slug: "filetype-detect-compare"
image: ""
categories:
    - 技术
tags:
    - Python
draft: false
---
## 需求场景和测试结论

**测试环境**：python 3.7.x | windows 10 | debian 10

&ensp;最近写了一个Webshell在线检测接口，其中需要对用户上传文件类型做检测。最简单的方式是可以直接获取文件后缀名，但这种方法不准确，用户可以更改后缀名上传文件。网上找了一些资料，发现Python的filetype和magic库都可以进行文件类型的检测。以下是一些可用在其他场景的通用方法可以作为参考。

&ensp;在使用了这两种库进行测试之后，得出以下结论：

> a. 可以检测出视频、音频、图片、压缩文件、PDF文件等被修改后缀的原格式。
>
> b. magic库更可靠更详细，filetype会出现误检测和无结果。

## 获取文件后缀名的方法

### 使用正则表达式

```python
import re

file_name = "C:\\Users\Dell\\Desktop\\11111111111\\test.php.txt.asp"
fstr = re.search(r'.*\.(.*)$', file_name, re.I).group(1)
print(fstr)	# "asp"
```

### 使用 os.path.basename() 方法

&ensp;Unix命令行中的 `file <文件路径>`命令，就是通过该方式实现功能的。

```python
import os

file_name = "/home/test/test.json.mp3.jsp"
fstr = os.path.basename(file_name).split('.')[-1].lower()
print(fstr)	# "jsp"
```

## Python的filetype和magic库安装

### [filetype](https://github.com/h2non/filetype.py)

```
pip install filetype
```

### [magic](https://github.com/ahupp/python-magic)

```
# Linux下安装:
pip install python-magic

# OSX下安装(需要先安装libmagic依赖项):
brew install libmagic
pip install python-magic

# Windows下安装:
pip install python-magic-bin 0.4.14
```

## 检测脚本

```python
# coding = utf-8
# 适用于windows和linux系统环境
# 检测结果：magic库更可靠更详细，filetype会出现误检测和无结果。
# 可以检测出视频、音频、图片、压缩文件、PDF文件等被修改后缀的原格式。
# 注意：Windows下检测路径末尾可以不加'\'，但是Linux下需要在末尾加'/'否则会报错

import os

import filetype
import magic


def fdirTraverser(file_dir):
    """
    简单的文件目录遍历器
    file_dir：待检测目录地址
    """
    for root, dirs, files in os.walk(file_dir):
        print("当前目录路径：%s\n" % root)
        print("当前路径下所有子目录：%s\n" % dirs)
        print("当前路径下所有非目录子文件：%s\n" % files)


def getSpecFile(file_dir, file_extension):
    """
    获取当前路径下除子目录外所有指定后缀的文件名列表（绝对路径）
    file_dir：待检测目录地址
    file_extension：指定文件后缀名
    """
    aa = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            # os.path.splitext()函数将路径拆分为文件名+扩展名
            if os.path.splitext(file)[1] == file_extension:
                aa.append(os.path.join(root, file))
        return aa


def getAllFile(path, list_name):
    """
    递归获取当前路径下所有文件名（绝对路径，包括所有子目录下的文件）
    path: 待检测目录地址
    list_name: 存储主目录下所有文件名称的列表（绝对路径）
    """

    b = os.listdir(path)
    # print(b)
    for file in b:
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            getAllFile(file_path, list_name)
        else:
            list_name.append(file_path)


def ck_ftype(path_list):
    """使用python的ftype和magic库对比判断文件类型"""
    for i in path_list:
        print("++++*******************START********************++++")
        print("待检测的文件为：%s\n" % i)
        # 使用filetype库
        kind = filetype.guess(i)
        print("[+]--------filetype--------[+]")
        print("filetype库检测的文件类型：")
        if kind is None:
            print('[-] 使用filetype库未检测出文件类型！\n')
        else:
            print('文件扩展名: %s，文件MIME类型：%s' % (kind.extension, kind.mime))
            print("[+]------------------------[+]\n")

        # 使用magic库
        # bb = magic.from_file(i)
        # cc = magic.from_file(i, mime=True)
        bb = magic.from_buffer(open(i, "rb").read(2048))
        cc = magic.from_buffer(open(i, "rb").read(2048), mime=True)
        print("[+]------------magic------------[+]")
        print("magic库检测的文件类型：%s，MIME类型：%s" % (bb, cc))
        print("[+]-----------------------------[+]\n")
        print("++++******************END*********************++++\n\n")


if __name__ == '__main__':
    # 支持linux和windows
    # path = "/home/mycode/test_files/"
    path = input("请输入要查询的文件路径：")

    # 简单的文件、目录遍历
    fdirTraverser(path)

    # 获取当前路径下除子目录外所有指定后缀的文件名列表（绝对路径）
    file_extension = ".png"
    file_list = getSpecFile(path, file_extension)
    print("file_list：%s\n" % file_list)

    # 递归获取当前路径下所有文件名（绝对路径，包括所有子目录下的文件）
    aa = []
    getAllFile(path, aa)
    print("待检测所有文件列表: %s\n" % aa)

    # 使用python的ftype和magic库对比判断文件类型
    ck_ftype(aa)
```

## 部分检测结果截图

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200917144610.png)

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200917144707.png)

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200917145129.png)

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200917145317.png)
