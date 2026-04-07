---
title: "弃坑 Parallels！M3 Mac 使用 UTM 丝滑安装 Kali Linux 全记录（含黑屏修复）"
date: 2026-04-07T21:11:42+08:00
slug: "install-kali-linux-on-utm-macbook-m3"
image: ""
categories:
    - 技术
tags:
    - MacOS
    - M3
    - UTM
    - Kali Linux
draft: false
---
## 前言

最近在复现 `perf` + `FlameGraph` 生成 Python 代码性能分析火焰图时，发现原本的虚拟机环境出了点问题：Kali 更新包后与 Mac 的剪贴板同步失效了。折腾 Parallels Tools 时又发现软件提示需要升级付费。

考虑到安全性、成本以及 Apple Silicon 原生支持的趋势，我决定转向开源免费的  **UTM** 。本篇记录了在 M3 芯片上安装 Kali Linux 2026.1 的完整避坑指南。

---

## 准备工作：UTM 和 镜像下载

### UTM 下载

UTM 的最大亮点在于免费 + 极强模拟能力。我们可以直接从官网下载 `.dmg` 安装包，这与 Mac App Store 版本的核心功能完全一致。

* **Mac 版** ：官网 [https://mac.getutm.app/](https://mac.getutm.app/)（免费 .dmg）或 Mac App Store（付费）。
* **iOS 版** ：官网 [https://getutm.app/](https://getutm.app/) 有安装指南（支持 iOS 11+）。
* 官方文档：[https://docs.getutm.app/](https://docs.getutm.app/)（有详细教程，包括创建 Windows/Linux/macOS 虚拟机）。

### Kali Linux 镜像下载

为了保证下载速度，强烈建议使用国内镜像站。

* **镜像版本** ：`kali-linux-2026.1-installer-arm64.iso`（务必选择 arm64 版本以适配 M3 芯片）。
* **下载地址** ：[清华大学开源软件镜像站 (Tsinghua Open Source Mirror)](https://mirrors.tuna.tsinghua.edu.cn/kali-images/current/)。

---

## 解决 UTM 安装黑屏死机问题

在 UTM 中创建好虚拟机并挂载 ISO 后，启动时如果选择 `Install` 或 `Graphical Install`，经常会卡死在以下报错界面：
`[0.017530]PCI: OF: of_root node is NULL, cannot create PCI host bridge node`

### 解决方案：

1. **调整显卡** ：关闭虚拟机，将“模拟显示卡”切换为  **`virtio-ramfb`** 。
2. **添加串行设备** ：在左侧设备栏点击“新建”，添加一个  **`Serial (串行)`** ，点击右下角存储。
3. **通过终端安装** ：重新打开虚拟机，此时会多出一个  **Serial Console（命令行窗口）** 。

   * **核心步骤** ：所有的安装选项进程都在这个窗口中进行。按照常规流程完成语言、键盘、网络、分区及用户配置。
4. **善后处理** ：

   * **移除镜像** ：安装完成后，若重启仍进入安装界面，请先停止虚拟机，在信息面板的 **CD/DVD** 栏点击“清除”。

   * **恢复显示** ：在设置中将显示卡切回  **`virtio-gpu-pci`** ，以获得更高清的显示效果。

---

## 解决 Kali 初始化更新超时

新系统安装后，执行 `sudo apt full-upgrade -y` 经常会因为官方源连接不稳定导致 `Connection timed out`。

### 1. 修改软件源

编辑配置文件：

```bash
sudo nano /etc/apt/sources.list
```

将以下**清华源**地址粘贴进去（建议注释掉原有的官方源）：

```plaintext
deb https://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main non-free contrib non-free-firmware
deb-src https://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main non-free contrib non-free-firmware
```

*按 `Ctrl + O` 保存，`Enter` 确认，`Ctrl + X` 退出。*

### 2. 修复并升级

依次执行以下命令，修复残缺文件并完成全量升级：

```bash
# 刷新软件列表
sudo apt update

# 修复因超时导致的损坏包
sudo apt --fix-broken install

# 重新执行全量升级
sudo apt full-upgrade -y
```

换源后，下载速度基本可以跑满带宽，不再报错。

---

## 总结

对于开发者来说，UTM 在 M3 Mac 上提供了一个非常纯粹的实验环境。虽然在安装初期需要通过“串行窗口”绕过显示驱动的 Bug，但配置完成后，无论是性能还是与系统的兼容性都非常出色，是替代收费商业软件的绝佳选择。
