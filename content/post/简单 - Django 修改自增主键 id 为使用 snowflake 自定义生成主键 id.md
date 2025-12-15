---
title: "简单 - Django 修改自增主键 id 为使用 snowflake 自定义生成主键 id"
date: 2020-07-14 10:00:00
slug: "django-snowflake-id"
image: "https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020071602.jpg"
categories:
    - 技术
tags:
    - Python
    - Django
draft: false
---
#### 1. 场景

##### 1.1 安装环境

python==3.7.1

Django==2.2

##### 1.2 应用场景

&ensp;原来使用的所有数据库表模型里的主键都是自定义或数据库自动生成的自增ID，它存在以下两大缺点无法满足后续的需求，使用雪花算法自定义生成主键ID可以避免这种问题。

**数据库主键自增id的缺点：**

&ensp;a. 极度依赖数据库，分表分库或者数据库做主从结构时无法保证唯一性，ID在生成时会出现性能瓶颈。

&ensp;b. 不安全，客户端可以根据自增ID很轻易猜出我们的业务数据

#### 2. 了解雪花算法snowflake

**原理：**

&ensp;参考：https://www.cnblogs.com/oklizz/p/11865750.html

**优点：**

&ensp;不依赖第三方系统，ID全局唯一，数据具有递增的连续性，便于查询。

**缺点：**

&ensp; 依赖系统时钟，如果系统时钟有问题，会导致ID重复（该问题可以通过很多方式避免）

#### 3. 过程

##### 3.1 models.py中创建测试原始模型类testRMF，表名'tb_testRMF'

**字段：**
自增主键：test_uid   BigAutoField、

名称：test_name   CharField

年龄：test_age   IntegerField

`<u>`*models.py:*`</u>`

```python
class testRMF(models.Model):
    """just for test"""
    test_uid =  models.BigAutoField(primary_key=True, verbose_name="测试数据uid")  # 主键
    test_name = models.CharField(max_length=64, verbose_name="名称")
    test_age = models.IntegerField(null=True, verbose_name="年龄")

    def __str__(self):
        return str(self.test_name)

    class Meta:
        db_table = 'tb_testRMF'
        verbose_name = verbose_name_plural = '测试数据表'
```

##### 3.2 生成并应用数据库迁移文件，数据表生成

```python
python3 manage.py makemigrations
python3 manage.py migrate
```

*`<u>`tb_testRMF：`</u>`*

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020071401.jpg)

##### 3.3 修改为使用snowflake自定义生成主键ID

  首先需要将原来的测试原始模型类testRMF注释掉，运行3.2两行代码移除数据表。

&ensp;在应用目录下（即与models.py同级的目录）新建一个脚本文件snow.py保存雪花算法代码，在models.py中将雪花算法调用方法封装为一个返回id的函数供default参数赋值使用，修改后重新应用并生成数据库迁移文件。

*`<u>`修改后的models.py:`</u>`*

```python
# coding=utf-8
import django.utils.timezone as timezone
from django.contrib.auth.hashers import check_password, make_password
from django.db import models

from .snow import *


# Create your models here.

def test_genID():
    worker = IdWorker(0, 0)
    my_id = worker.get_id()
    return my_id

class testRMF(models.Model):
    """just for test"""
    test_uid = models.BigIntegerField(primary_key=True, default=test_genID, verbose_name="测试数据uid")
    test_name = models.CharField(max_length=64, verbose_name="名称")
    test_age = models.IntegerField(null=True, verbose_name="年龄")

    def __str__(self):
        return self.test_name

    class Meta:
        db_table = 'tb_testRMF'
        verbose_name = verbose_name_plural = '测试数据表'
```

&ensp;记得执行3.2两行命令。

*`<u>`tb_testRMF：`</u>`*

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/2020071402.jpg)
