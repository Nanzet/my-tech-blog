---
title: "了解美团点评分布式ID生成系统 - Leaf"
date: 2020-06-11 12:00:00
slug: ""
image: "https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020061201.jpg"
categories:
    - 技术
tags:
    - 分布式唯一ID
draft: false
---
### 1、**开源项目地址：**

[https://github.com/Meituan-Dianping/Leaf](https://github.com/Meituan-Dianping/Leaf)

### 2、**原理：**

[https://tech.meituan.com/2017/04/21/mt-leaf.html](https://tech.meituan.com/2017/04/21/mt-leaf.html)

### 3、**安装：**

- MySQL 8.0.20（[安装](https://www.runoob.com/w3cnote/windows10-mysql-installer.html)）
- java环境（[安装](https://www.runoob.com/java/java-environment-setup.html)）
- maven（是一个项目管理工具，可以对 Java 项目进行构建、依赖管理。[教程](https://www.runoob.com/maven/maven-tutorial.html)）
- zookeeper（一个分布式的，开放源码的分布式应用程序协调服务，是Hadoop和Hbase的重要组件。它是一个为分布式应用提供一致性服务的软件，提供的功能包括：配置维护、域名服务、分布式同步、组服务等。[安装](https://blog.csdn.net/weixin_39249427/article/details/99637734)）

### 4、**对比开源项目需要做的兼容mysql 8的修改：**

参考：

> a. [基于MySQL8.0美团leaf测试分布式ID生成系统](https://blog.csdn.net/qq_39455116/article/details/99458001?utm_medium=distribute.pc_relevant.none-task-blog-baidujs-5)
>
> b. [Leaf：美团的分布式唯一ID方案深入剖析](https://www.jianshu.com/p/bd6b00e5f5ac)

**修改1：**

&ensp;父目录下的pom文件修改MySQL版本号：

&ensp;查看版本:

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020061001.jpg)

&ensp;修改pom.xml文件：

`<mysql-connector-java.version>8.0.20</mysql-connector-java.version>`

**修改2：**

&ensp;数据库的设置，修改文件leaf.properties：

```properties
leaf.name=com.sankuai.leaf.opensource.test
# segment模式开关，这种模式依赖数据库
leaf.segment.enable=true
leaf.jdbc.url=jdbc:mysql://localhost:3306/leaf?autoReconnect=true&useSSL=false&serverTimezone=Asia/Shanghai
leaf.jdbc.driver-class-name=com.mysql.cj.jdbc.Driver
leaf.jdbc.username=root
leaf.jdbc.password=xxxxx

# snowflake模式，这种模式依赖zookeeper
leaf.snowflake.enable=true
leaf.snowflake.zk.address=127.0.0.1:2181
leaf.snowflake.port=9099
```

**修改3：**

&ensp;修改xxx\Leaf\leaf-server\src\main\java\com\sankuai\inf\leaf\server\Constants.java，Constants类添加driver支持：

`public static final String driver = "leaf.jdbc.driver-class-name";`

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020061002.png)

**修改4：**

&ensp;修改xxx\Leaf\leaf-server\src\main\java\com\sankuai\inf\leaf\server\service\SegmentService.java，SegmentService类下面添加driver支持：

`dataSource.setDriverClassName(properties.getProperty(Constants.driver));`

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020061003.png)

&ensp;mvn方式运行服务：

`mvn spring-boot:run`

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020061004.jpg)

&ensp;Snowflake和Segment两种获取唯一ID的模式的访问方式如下：

```
# Segment 模式获取唯一ID
http://localhost:8080/api/segment/get/pay
http://localhost:8080/api/segment/get/account

# Snowflake 模式获取唯一ID
http://localhost:8080/api/snowflake/get/pay
http://localhost:8080/api/snowflake/get/account
```

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020061005.jpg)

&ensp;Segment模式监控页面：

`http://localhost:8080/cache`

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020061006.jpg)
