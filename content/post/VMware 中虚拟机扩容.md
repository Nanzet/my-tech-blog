---
title: "VMware 中虚拟机扩容"
date: 2020-09-16 17:24:00
slug: "vmware-expansion"
image: ""
categories:
    - 技术
tags:
    - VMware
draft: false
---
## 前提

&ensp;安装系统时未进行手动分区，系统只有两个分区（根分区和交换分区），该情况下可直接扩展根分区大小。

## 过程

### 虚拟机设置 -> 扩展虚拟机硬盘大小（关机）

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200915115638.png)

### 安装开源磁盘分区工具

```bash
sudo apt-get install gparted
```

### 打开 Gparted ，删除 /dev/sda2 及其子分区，点击顶部绿色对号保存修改

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200915120546.jpg)

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200915120554.jpg)

### 更改 /dev/sda1 空间大小，保存修改

/dev/sda1后都是未分配的空间，选中/dev/sda1右键点击选择"更改大小/移动"，注意预留空间给后面要设置的交换分区。

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200915121108.jpg)

### 对未分配的空间创建交换分区，保存修改

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200915121337.jpg)

### 查看 Linux 系统分区信息

```bash
sudo fdisk -l
```

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20200915121620.jpg)
