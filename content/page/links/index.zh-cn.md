---
title: 友链
links:
  - title: GitHub
    description: GitHub is the world's largest software development platform.
    website: https://github.com
    image: https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png
  - title: TypeScript
    description: TypeScript is a typed superset of JavaScript that compiles to plain JavaScript.
    website: https://www.typescriptlang.org
    image: ts-logo-128.jpg
menu:
    main: 
        weight: -50
        params:
            icon: link

comments: false
---
要使用此功能，请在头部配置（Front Matter）中添加 `links` 区块。

本页面的头部配置说明：

```yaml
links:
  - title: GitHub
    description: 世界上最大的代码托管平台。
    website: https://github.com
    image: https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png
  - title: TypeScript
    description: TypeScript 是 JavaScript 的类型化超集，它可以编译成纯 JavaScript。
    website: https://www.typescriptlang.org
    image: ts-logo-128.jpg
```

`image` 字段同时支持本地图片和外部（网络）图片。
