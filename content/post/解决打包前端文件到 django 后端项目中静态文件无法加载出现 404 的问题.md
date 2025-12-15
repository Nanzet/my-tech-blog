---
title: "解决打包前端文件到 Django 后端项目中静态文件无法加载出现 404 的问题"
date: 2020-10-11 20:54:57
slug: ""
image: "https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201011221205.jpg"
categories:
    - 技术
tags:
    - Django
draft: false
---
### 1. 运行环境

- 后端：Django v2.2、Python v3.7.1
- 前端：vue v2.9.6、Node.js v12.18.4、npm v6.14.6（vue-cli 安装参考：[ubuntu](https://blog.csdn.net/sinat_33384251/article/details/93127561)、[windows](https://blog.csdn.net/muzidigbig/article/details/80490884)）

### 2. 解决过程

#### 2.1 从 github 或 gitea 上下载前端项目文件

&ensp;在django根目录下新建一个文件夹frontend，将下载后解压的前端项目文件放到frontend目录中。

#### 2.2 在 frontend 目录下创建 vue.config.js 文件（解决报错的关键步骤）

```javascript
module.exports = {
    assetsDir: 'static',  # 指定`build`时，在静态文件上一层添加static目录
};
```

#### 2.3 在 frontend 项目下执行 "npm install" 安装依赖，执行完成后会多一个 node_modules 目录

#### 2.4 执行 "npm run build" 命令生成打包文件 dist（frontend 目录下的子目录，chmod 777 /frontend -R）

&ensp;生成打包文件dist目录后可将之前下载的前端文件都删除。（django项目根目录/frontend/dist）

&ensp;我生成的dist打包文件目录如下：

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201011213840.png" style="zoom:67%;" />

#### 2.5 配置 settings.py

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201011212346.png)

#### 2.6 django 项目根目录下的 urls.py 的加载模板设置

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201011212530.png)

#### 2.7   运行 django 服务成功解决

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201011214139.png" style="zoom:80%;" />
