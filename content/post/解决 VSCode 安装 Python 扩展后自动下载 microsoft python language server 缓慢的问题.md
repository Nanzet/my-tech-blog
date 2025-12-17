---
title: "解决 VSCode 安装 Python 扩展后自动下载 microsoft python language server 缓慢的问题"
date: 2020-07-07 23:52:30
slug: "vscode-python-language-server-slow"
image: ""
categories:
    - 技术
tags:
    -  VSCode
draft: false
---
## 采取手动安装的方法

1、根据失败提示记录下载nupkg文件，例如：[https://pvsc.azureedge.net/python-language-server-stable/Python-Language-Server-win-x64.0.5.51.nupkg](https://pvsc.azureedge.net/python-language-server-stable/Python-Language-Server-win-x64.0.5.51.nupkg)

2、解压缩文件至插件文件夹目录

**windows下：**

&ensp;解压缩nupkg文件至到Windows系统下的目录：C:\Users\yourname\.vscode\extensions\ms-python.python-2020.3.71113\languageServer.0.5.51（复制前清空ms-python.python-2020.3.71113文件夹内的内容）重新打开vs code即可激活拓展。

**linux下：**

&ensp;方法类似：

```shell
# 以下命令中的 `ms-python.python-2020.3.71113` 为当前安装的 python 插件文件夹，如果你的 python 版本不一样需自行替换
unzip Python-Language-Server-linux-x64.0.5.51.nupkg -d ~/.vscode/extensions/ms-python.python-2020.3.71113/languageServer.0.5.51
chmod +x ~/.vscode/extensions/ms-python.python-2020.3.71113/languageServer.0.5.51/Microsoft.Python.LanguageServer
```

3、安装完成后打开 vscode 设置文件 ~/.config/Code/User/settings.json（也可使用 ctrl+, 打开 vscode 图形界面配置），添加 "python.autoUpdateLanguageServer": false 以禁用 python 插件自动去更新 language server。windows下直接点文件-->首选项-->设置，搜索python.autoUpdateLanguageServer取消勾选即可。

4、如果按照上述设置后发现VS Code还是会自动下载microsoft python language server，那么可能是[Settings Sync插件](https://juejin.im/post/5b9b5a6f6fb9a05d22728e36)的原因了，该插件用于两台PC同步VS Code配置，禁用该插件后解决问题。（注：languageServer文件夹名称最好去掉版本号）
