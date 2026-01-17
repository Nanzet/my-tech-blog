---
title: "生产环境部署：python Django Nginx Uwsgi Debug False   关闭 Django 自带的 Admin 后台"
date: 2020-10-18 21:32:52
slug: ""
image: ""
categories:
    - 技术
tags:
    - Python
    - Django
draft: false
---
> **参考：**[https://www.cnblogs.com/zhming26/p/6158660.html](https://www.cnblogs.com/zhming26/p/6158660.html)
>
> **前言：**
>
> &ensp;该种部署方式中nginx接收Web的所有请求，其中所有的静态请求由nginx来处理，所有的非静态请求通过uwsgi传递给Django，由Django来进行处理，从而完成一次WEB请求。

## 测试部署环境

- 操作系统debian 10
- python3.7
- django2.2

## 安装 nginx 及配置

### 切换到 root 权限，安装

`apt-get install nginx`

### 添加对应网站的配置文件和测试内容

`vim /etc/nginx/conf.d/wj.conf`

```conf
server {
    listen       8088;    # 修改端口号
    server_name  localhost;


    #charset koi8-r;


    #access_log  logs/host.access.log  main;


    location / {
        root   html;
        index  index.html index.htm;
    }
}
```

### 重启 nginx 服务

`service nginx restart`

### 本地测试运行：[http://localhost:8088/](http://localhost:8088/)

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201018214308.png" class="about-img" />

## python3.7 安装 uwsgi

### 解决报错

```shell
sudo apt install python3.7-dev

pip3 install uwsgi --upgrade
```

### 测试 uwsgi，创建 test.py 文件

```python
def application(env, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    return [b"Hello World"]
```

### 通过 uwsgi 测试运行该文件

`uwsgi --http :8001 --wsgi-file ./test.py`

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201018214529.png" class="about-img" />

### Tips:（以下内容仅作参考不做配置也可以，关闭服务时 ctrl+c 即可）

- 可在项目根目录下新建两个文件wj_uwsgi.pid和wj_uwsgi.status，一个记录pid号方便重启和停止服务，一个记录服务运行状态。
- 修改你的uwsgi配置文件，wj_uwsgi.ini文件添加以下配置：

```ini
stats=%(chdir)/wj_uwsgi.status   
pidfile=%(chdir)/wj_uwsgi.pid
```

- 以后通过uwsgi启动wj_uwsgi.ini文件，就会在.pid和.status文件内记录内容，启动、重启、停止uwsgi：

```shell
# 启动：
uwsgi --ini xxx.ini
# 重启：
uwsgi --reload xxx.pid
# 停止：
uwsgi --stop xxx.pid
```

## 配置 Django 与 uwsgi 连接

&ensp;django项目位置为：/home/mycode/webshellCheck

### 在项目根目录 webshellCheck 下新建 wj_uwsgi.ini 文件

```ini
# wj_uwsgi file
[uwsgi]

# Django-related settings
socket = 127.0.0.1:9000

# the base directory (full path)
chdir = /home/mycode/webshellCheck

# Django s wsgi file
module = webshellCheck.wsgi

# process-related settings
# master
master = true

# maximum number of worker processes
processes = 4

# ... with appropriate permissions - may be needed
# chmod-socket    = 664
# clear environment on exit
vacuum = true
```

**注：**

- socket 指定项目执行的端口号。
- chdir 指定项目的目录。
- module webshellCheck.wsgi ，可以这么来理解，对于wj_uwsgi.ini文件来说，与它的平级的有一个webshellCheck目录，这个目录下有一个wsgi.py文件。

### 在项目目录下通过 uwsgi 命令读取 wj_uwsgi.ini 文件启动项目

`uwsgi --ini ./wj_uwsgi.ini`

### 修改 nginx.conf 配置文件

```conf
server {
    listen         8099;
    server_name    127.0.0.1
    charset UTF-8;
    access_log      /var/log/nginx/wj_access.log;
    error_log       /var/log/nginx/wj_error.log;


    client_max_body_size 75M;


    location / {
        include uwsgi_params;
        uwsgi_pass 127.0.0.1:9000;
        uwsgi_read_timeout 2;
    }   
    location /static {
        expires 30d;
        autoindex on;
        add_header Cache-Control private;
        alias /home/mycode/webshellCheck/frontend/dist/static;
     }
}
```

### 重启 nginx，然后启动 uwsgi

```shell
service nginx restart

uwsgi --ini ./wj_uwsgi.ini
```

### 在浏览器测试访问：localhost:8099

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201018215145.png" class="about-img" />

&ensp;uwsgi启动成功日志：

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201018215253.png" class="about-img" />

## 生产环境配置：Django debug=False+关闭django自带的admin后台

### 静态文件配置

&ensp;关于本项目中前端打包的静态文件放在项目根目录下的frontend/dist/static路径下，部署到生产环境中需要将debug设置为false，静态文件相关配置如下:

```conf
......
DEBUG = False # 修改

ALLOWED_HOSTS = ['*', ] # 允许所有域名访问

STATIC_URL = '/static/' # 静态路由映射，别名设置，django利用STATIC_URL来让浏览器可以直接访问静态文件

STATICFILES_DIRS = [ # 公共文件夹的静态文件路由配置
    os.path.join(BASE_DIR, "frontend/dist/static"),
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 'DIRS': [],
        'DIRS': ['frontend/dist/static'], # 模板文件的路径设置
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
......
```

### 关闭 django 自带的 admin 后台，主 urls.py 的配置

```python
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView


urlpatterns = [
    # path('admin/', admin.site.urls),    # 生产环境下建议可关闭django自带的后台管理
    path('', TemplateView.as_view(template_name="index.html")),    # 首页模板调用路径
    path('users/', include('wscheck.urls'))
]
```

&ensp;Django关闭DEBUG模式后，就相当于是生产环境了，Django官网上指出如果是django框架一旦作为生产环境，那么它的静态文件访问接口就不应该从Django框架中走了，应该有独立的web环境，首推nginx 。在开发过程中，开发人员在框架的根目录下创建一个static目录，目录在根据里面有几个APP创建对应APP程序静态文件目录。但是一旦放到生产环境（也就是关闭掉DEBUG模式），你在nginx中就要单独做访问/static/目录的路由。

### 存在多个应用内的静态文件时的配置

&ensp;这里由于只有一个应用的静态文件需要加载，所以注意nginx的配置中项目运行需要加载的静态文件就是一个绝对路径，上面关于静态文件的配置完全可以满足本项目的需求。而当该项目下不止一个app且每个app下都有独立的静态文件的时候，我们就需要将所有的静态文件都统一放到一个目录下。django提供了一个比较方便的方法：

（1）在上述例子的静态文件配置的基础上，settings.py中配置一个静态目录的根目录：STATIC_ROOT

```python
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')    # 注意staticfiles可以是其他名称，但是不要和STATICFILES_DIRS设置的名称重复
```

（2）然后在项目根目录下执行以下命令，可将项目下所有的静态资源统一复制到STATIC_ROOT目录下

```shell
root@debian:/home/mycode/webshellCheck# python3 manage.py collectstatic
```

&ensp;执行完命令可以看到在项目根目录下多了一个带锁图标的staticfiles文件夹，记得赋予该目录权限：

`chmod 777 staticfiles -R`

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201018222754.png" class="about-img" />

（3）修改nginx配置中的静态文件路径，将该行 `alias /home/mycode/webshellCheck/frontend/dist/static;`更改为：

`alias /home/mycode/webshellCheck/staticfiles;`

&ensp;重启nginx，启动uwsgi，在浏览器测试运行成功！

&ensp;尝试在浏览器输入 `localhost:8090/不存在的路径`不会出现暴露部分路径的debug信息，尝试输入 `localhost:8090/admin`提示不存在 😆 🎉。
