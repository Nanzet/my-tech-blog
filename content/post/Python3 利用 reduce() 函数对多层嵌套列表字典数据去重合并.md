---
title: "Python3 利用 Reduce() 函数对多层嵌套列表字典数据去重合并"
date: 2020-09-23 22:11:00
slug: "python-reduce-list-comnibe"
image: ""
categories:
    - 技术
tags:
    - Python
draft: false
---
## 需求场景

&ensp;基于角色的权限设计，在登录接口中对当前用户角色权限的权限字典进行构造，由于当前用户可能拥有多个角色（普通用户、管理员1、管理员2、超级管理员...），导致权限数据字典可能会出现这种情况：权限字典列表中，不同角色模块字典下具有相同、不同或部分的接口代号、地址。

&ensp;以下方法可以对当前场景下多层嵌套的列表字典数据进行去重并合并同模块的接口数据，可以根据业务需求修改下面的代码。

## 功能测试代码

```python
# coding=utf-8

from functools import reduce

# 测试数据，权限字典列表；第一层字典的键不同的数字表示不同的模块
aa = [
    {
        '2': {
            'codes': ['list', 'tree', 'add', 'delete', 'update', 'detail', 'import', 'generate', 'export'],
            'urls': ['/users/rm/searchlt', '/users/rm/ltree', '/users/addRisk', '/users/rm/delete', '/users/risk/update', '/users/rm/detail', '/users/rm/risk/import', '/users/rm/risk/export', '/users/rm/risk/download']
        },
        '4': {
            'codes': ['list', 'tree', 'add', 'delete', 'update', 'detail'],
            'urls': ['/users/sm/searchlt', '/users/sm/ltree', '/users/addStrategy', '/users/sm/delete', '/users/strategy/update', '/users/sm/detail']
        }
    },
    {
        '1': {
            'codes': ['list', 'tree', 'add1', 'add2', 'delete', 'update', 'detail'],
            'urls': ['/users/bm/searchlt', '/users/bm/ltree', '/users/addbaseAsset', '/users/addptAsset', '/users/bm/delete', '/users/asset/update', '/users/bm/detail']
        },
        '4': {
            'codes': ['list', 'tree', 'add', 'delete', 'update', 'detail'],
            'urls': ['/users/sm/searchlt', '/users/sm/ltree', '/users/addStrategy', '/users/sm/delete', '/users/strategy/update', '/users/sm/detail']
        }
    },
    {
        '3': {
            'codes': ['selDetail', 'tree', 'add', 'update', 'delete'],
            'urls': ['/users/szm/searchlt', '/users/szm/ltree', '/users/sz', '/users/sz/update', '/users/szm/delete']
        }
    }
]


def sum_dict(a, b):
    temp = dict()
    # 获取a, b字典中的键值列表，不改变原来的元素顺序去重
    union_keys = list(a.keys()) + list(b.keys())
    new_keys = list(set(union_keys))
    new_keys.sort(key=union_keys.index)
    for key in new_keys:
        print(key)  # '2'
        # 可以根据业务需求修改下面的代码
        m = 0
        for d in (a, b):
            d = d.get(key)
            print(d)
            if d:
                m = m + 1
                # 对于a, b字典中重复出现的键里可能存在对应值不相同的情况，取并集并做格式转换
                if m == 2:
                    union_codes_list = a.get(key).get(
                        'codes') + b.get(key).get('codes')    # list
                    union_urls_list = a.get(key).get(
                        'urls') + b.get(key).get('urls')
                    new_codes = list(set(union_codes_list))
                    new_urls = list(set(union_urls_list))
                    # set后不改变原来元素顺序
                    new_codes.sort(key=union_codes_list.index)
                    new_urls.sort(key=union_urls_list.index)
                    temp[key] = {"codes": new_codes, "urls": new_urls}
                else:
                    temp[key] = d

    return temp


perm_dict = reduce(sum_dict, aa)

print(perm_dict)
```

## 运行结果

```json
{
  "2": {
    "codes": ["list", "tree", "add", "delete", "update", "detail", "import", "generate", "export"],
    "urls": [
      "/users/rm/searchlt",
      "/users/rm/ltree",
      "/users/addRisk",
      "/users/rm/delete",
      "/users/risk/update",
      "/users/rm/detail",
      "/users/rm/risk/import",
      "/users/rm/risk/export",
      "/users/rm/risk/download"
    ]
  },
  "4": {
    "codes": ["list", "tree", "add", "delete", "update", "detail"],
    "urls": [
      "/users/sm/searchlt",
      "/users/sm/ltree",
      "/users/addStrategy",
      "/users/sm/delete",
      "/users/strategy/update",
      "/users/sm/detail"
    ]
  },
  "1": {
    "codes": ["list", "tree", "add1", "add2", "delete", "update", "detail"],
    "urls": [
      "/users/bm/searchlt",
      "/users/bm/ltree",
      "/users/addbaseAsset",
      "/users/addptAsset",
      "/users/bm/delete",
      "/users/asset/update",
      "/users/bm/detail"
    ]
  },
  "3": {
    "codes": ["selDetail", "tree", "add", "update", "delete"],
    "urls": [
      "/users/szm/searchlt",
      "/users/szm/ltree",
      "/users/sz",
      "/users/sz/update",
      "/users/szm/delete"
    ]
  }
}
```
