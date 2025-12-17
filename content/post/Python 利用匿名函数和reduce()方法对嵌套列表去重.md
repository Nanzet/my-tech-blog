---
title: "Python 利用匿名函数和 reduce() 方法对嵌套列表去重"
date: 2020-07-04 12:57:00
slug: "python-list-deduplication"
image: ""
categories:
    - 技术
tags:
    - Python
draft: false
---
## 示例及结果

```python
from functools import reduce

# 待去重嵌套列表（元素为字典）
aa = [{'bigAsset1': '资产1', 'bigAsset2': '资产2'}, {'bigAsset1': '资产2', 'bigAsset2': '资产1'}, {'bigAsset1': '资产3', 'bigAsset2': '资产1'}, {'bigAsset1': '资产1', 'bigAsset2': '资产2'}, {'bigAsset1': '资产2', 'bigAsset2': '资产3'}]

# 待去重嵌套列表（元素为集合）
bb = [{'资产1', '资产2'}, {'资产2', '资产1'}, {'资产3', '资产1'}, {'资产1', '资产2'}, {'资产2', '资产3'}]

cc = [['资产1', '资产2'], ['资产2', '资产1'], ['资产3', '资产1'], ['资产1', '资产2'], ['资产2', '资产3']]

run_function = lambda x,y : x if y in x else x + [y]

aa = reduce(run_function, [[],] + aa)
bb = reduce(run_function, [[],] + bb)
cc = reduce(run_function, [[],] + cc)

print(aa)
# [{'bigAsset1': '资产1', 'bigAsset2': '资产2'}, {'bigAsset1': '资产2', 'bigAsset2': '资产1'}, {'bigAsset1': '资产3', 'bigAsset2': '资产1'}, {'bigAsset1': '资产2', 'bigAsset2': '资产3'}]
print(bb)
# [{'资产1', '资产2'}, {'资产3', '资产1'}, {'资产3', '资产2'}]
print(cc)
# [['资产1', '资产2'], ['资产2', '资产1'], ['资产3', '资产1'], ['资产2', '资产3']]
```

&ensp;注意上面不同的两种结果，适用于不同场景。对于上例中若对资产顺序无要求，去重应采用bb的形式。

## 原理分析

&ensp;打开你的IDE调试思路会很清晰，打开之前你可能需要了解这些知识：

- [python 匿名函数](https://www.cnblogs.com/shenhongbo/p/11566976.html)
- [python中的*args、**kwargs](https://kodango.com/variable-arguments-in-python#comment-231489)
- [python reduce()函数](https://www.runoob.com/python/python-func-reduce.html)

&ensp;匿名函数run_function这行的功能实现等同于以下方法：

```python
def run_function(x, y):
    if y in x:
        return x
    else:
        return x + [y]
```

&ensp;其次，注意两个列表相加的结果，例如：

```python
[[],] + bb
# [[], {'资产1', '资产2'}, {'资产1', '资产2'}, {'资产3', '资产1'}, {'资产1', '资产2'}, {'资产3', '资产2'}]
```
