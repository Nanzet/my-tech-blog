---
title: "解决 Navicat Premium 12 远程连接数据库 PostgreSQL 12 报错的问题"
date: 2020-09-23 22:53:00
slug: "navicate-connect-postgresql-error"
image: ""
categories:
    - 技术
tags:
    - 数据库 
draft: false
---
## 远程目标主机环境

&ensp;Debian 10

## 报错内容

&ensp;发生致命错误：没有用于主机“…”，用户“…”，数据库“…”，SSL关闭的pg_hba.conf记录。

## 解决过程

### 找到 postgresql.conf 和 pg_hba.conf 这两个文件

```bash
find / -name  postgresql.conf
find / -name pg_hba.conf
```

### 设置 postgresql 外网访问

#### 检查配置文件 postgresql.conf

`listen_addresses = '*'`

#### 修改 pg_hba.conf 在文件末尾新加一行

```config
# TYPE DATABASE USER CIDR-ADDRESS METHOD
host  all  all  0.0.0.0/0  md5
```

### 重启 postgresql ，远程连接成功

`systemctl restart postgresql`
