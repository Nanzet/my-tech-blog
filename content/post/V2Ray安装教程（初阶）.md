---
title: "V2Ray安装教程（初阶）"
date: 2020-07-04 12:56:00
slug: ""
image: ""
categories:
    - 技术
tags:
    - 科学上网
draft: false
---
> **【声明：仅供学习交流、查阅资料使用，后果自负】**

## 购买 VPS

注：已弃用 virmach 不稳定，购买了 Hostus $16/年的套餐，可以修改系统为 ubuntu 下面的安装 v2ray 等步骤一样。

### 购买说明

&ensp;我购买的是：[virmach](https://billing.virmach.com/)-->register-->[KVM &amp; SSD Windows VPS](https://billing.virmach.com/cart.php?gid=18)（季付，可搜索virmach优惠码进行兑换；注意操作系统建议选择ubuntu 16.04.6，初始选择的 centos 6.5 安装 v2ray 失败）

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020062401.jpg)

&ensp;上述 vps ping 的时候不是特别稳定，不过配置 v2ray 后，速度还可以，能满足查阅资料的需求（这款流量用不完，可以按照自己需求选购套餐）；其他 vps 推荐：[HostUs](http://www.hostusvps.com/)购买以下套餐即可：（已购买速度快很多、更稳定）

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020062402.jpg)

## ubuntu 16.04.6 安装服务端 v2ray 流程

> 注：
> &ensp;使用xshell可远程连接vps，根据hostus提供的root账户密码、IP进行登录连接；初始登录可使用passwd命令更改root账户密码，以后使用该密码即可；若忘记自己设置的密码，在hostus购买的的vps管理界面更改root密码即可。

### 更新 apt

```
sudo apt update && sudo apt -y upgrade
```

### 查看系统时间并修改时区

```
date -R
timedatectl set-timezone Asia/Shanghai 
# 若提示'Failed to create bus connection: No such file or directory'，先执行apt-get install dbus
```

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020062403.jpg)

### 安装 upzip

```
sudo apt install unzip
```

### 下载、安装官方维护脚本

```
wget https://install.direct/go.sh && sudo bash go.sh
```

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020063002.jpg"/>

&ensp;上图的端口号和 uuid 是随机生成的，可在 /etc/v2ray/config.json 配置文件中进行更改。

&ensp;生成正确格式的 uuid 可以参考： [https://www.uuidgenerator.net/，linux也可以使用命令](https://www.uuidgenerator.net/%EF%BC%8Clinux%E4%B9%9F%E5%8F%AF%E4%BB%A5%E4%BD%BF%E7%94%A8%E5%91%BD%E4%BB%A4) cat /proc/sys/kernel/random/uuid 生成。

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020062801.jpg)

&ensp;查看 or 编辑/etc/v2ray/config.json：

```
cat or vim /etc/v2ray/config.json
```

### 设置开机启动 & 启动服务

```
sudo systemctl enable v2ray && sudo systemctl start/restart v2ray
```

注：systemctl start/restart/stop/status v2ray

### 设置防火墙：([ubuntu防火墙设置](https://www.jianshu.com/p/eccb913ac58d))

```
# 开启防火墙
sudo ufw enable
# 打开指定端口
sudo ufw allow 15421/tcp

# 注：要通过本机的 xshell 连接上远程的 vps 则需要开放 vps 的 22 端口
sudo ufw allow 22

# 若提示 command not found，执行 apt-get install ufw -y
```

### 升级更新，重新执行安装，不会修改原配置

```
sudo bash go.sh
```

### 解决高延迟问题

安装 BBR：

```
wget -N --no-check-certificate "https://raw.githubusercontent.com/chiakge/Linux-NetSpeed/master/tcp.sh" && chmod +x tcp.sh && ./tcp.sh
```

&ensp;先选择安装 BBR/BBR 魔改版内核内核，安装完成后，在执行 ./tcp.sh 按需要选择加速，我选择的是魔改版加速。

&ensp;其他 v2ray 配置请参考官方教程有详细说明。

### [TLS 配置](https://guide.v2fly.org/advanced/tls.html)可能遇到的问题及解决方法总结

（1）添加域名解析 A 记录参考：

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020070405.jpg)

（2）解决使用 '~/.acme.sh/acme.sh --issue -d mydomain.me --standalone --keylength ec-256 --force' 命令生成证书的 80 端口被占用问题：

```python
# 查看80端口占用情况
lsof -i:80

# 若要关闭使用这个端口的程序，使用kill + 对应的pid
kill -9 PID号
```

> 参考：
>
> a. [新 V2Ray 白话文指南](https://guide.v2fly.org/)
>
> b. [v2ray完全使用教程](https://yuan.ga/v2ray-complete-tutorial/)
>
> c. [caddy v2 安装教程](https://tophat.top/posts/98b102d8.html)（WebSocket + TLS + Web尝试失败，有空再试，目前参照官方教程的tls配置成功，且速度较快）

## 客户端安装

> 客户端如PC建议在chrome或firefox浏览器下载插件Proxy SwitchyOmega搭配使用。

**客户端：**

[**Windows**](https://github.com/v2ray/v2ray-core/releases)

[**图形化客户端**](https://github.com/2dust/v2rayN/releases)

[**MacOS**](https://github.com/v2ray/v2ray-core/releases)

[**Linux**](https://github.com/v2ray/v2ray-core/releases)

**Android:**

V2RayNG: [Github](https://github.com/2dust/v2rayNG/releases) or [Play Store](https://play.google.com/store/apps/details?id=com.v2ray.ang)

BifrostV:   or [Play Store](https://play.google.com/store/apps/details?id=com.github.dawndiy.bifrostv)

**iOS:（支持以下软件，链接可能过时，请在苹果商店下载）**

 [ShadowRocket](https://itunes.apple.com/tw/app/shadowrocket/id932747118)

 [Kitsunebi - Proxy Utility](http://itunes.apple.com/tw/app/kitsunebi-proxy-utility/id1446584073)

 [Kitsunebi Lite](http://itunes.apple.com/tw/app/kitsunebi-lite/id1387913765)

[Pepi](https://itunes.apple.com/tw/app/pepi/id1283082051)

[i2Ray](https://itunes.apple.com/tw/app/i2ray/id1445270056)

[Quantumult](https://itunes.apple.com/tw/app/quantumult/id1252015438)

**附：**

[**400+苹果软件分享**](https://docs.qq.com/doc/DYlVOcWJtYlFPSFdN)

**解决关于chrome浏览器插件离线安装和设置SwitchyOmega的问题：**😏😏

（1）[下载Chrome扩展插件Crx离线安装包](https://crxdl.com/)--搜索"SwitchyOmega"

（2）[谷歌Chrome浏览器安装扩展插件](https://www.cccitu.com/3391.html)

（3）SwitchyOmega配置[Chrome浏览器SOCKS代理服务器设置教程](https://www.cccitu.com/2655.html)

（4）规则列表：（[规则列表刷新不了](https://blog.csdn.net/qq_38879305/article/details/106619860)、仍然恢复不了：[戳我](https://blog.csdn.net/qq_36561697/article/details/88350512?utm_medium=distribute.pc_relevant.none-task-blog-baidujs-1)）

```
https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt
```

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020062803.jpg)

（5）google！😆😆😆enjoy it!

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020062804.jpg)
