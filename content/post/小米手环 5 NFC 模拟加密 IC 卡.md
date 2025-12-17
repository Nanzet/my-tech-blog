---
title: "小米手环 5 NFC 模拟加密 IC 卡"
date: 2020-10-09 22:53:00
slug: "xiaomi-band-ic"
image: "https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201010001853.png"
categories:
    - 兴趣
tags:
    - 小米手环
draft: false
---
## 前言

&ensp;小米手环4是在刚出的时候买的，因为心悦它的公交卡、门禁卡、支付宝支付、切歌等功能，我就入手了一个，使用下来觉得支付宝支付的功能比较鸡肋，那块屏幕太小了，切歌就不说了（老网抑云了）基本没用过。怎么突然就入了小米5呢，刚开始看到雷总发的微博的时候，我被它的磁吸式充电和更大的屏幕吸引了，但是那时候我忍住了没买怕和小4比差不了多少，某次发现小4屏幕上多了一道划痕，强迫症不能忍😱😱！买它，买它，买它！小5用了快一个月了，明显感觉表带比小4舒服很多，比较柔软的材质不过容易沾灰，戴着睡觉手腕基本无感很舒服。其实最实用的功能还是门禁卡、公交卡了，这次的小5也加入了女性健康记录功能，Nice😊

&ensp;上班的时候刷电梯卡，手环贴上去，实测生效，方便快捷，出门必备之良品，还可以自定义表盘为自己的爱豆，哈哈哈❤️对程序员来说，久坐提醒也很贴心，坐久了颈椎疼腰酸眼睛也酸，年纪轻轻就...唉~💔

&ensp;由于园区卡是加密的IC卡，所以需要破解才能模拟成功，支持的卡片类型如下：

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201009233252.png" style="zoom:50%;" />

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201009233601.png" style="zoom:50%;" />

## 硬件和软件

- 小米手环5 NFC版、win10 PC
- MifareOneTool
- PN532、CH340g、cuid蓝卡

## 连线和驱动安装

&ensp;CH340G模块接线方式：gnd对gnd，vcc对5v，SDA对TXD，SCL对RXD，剩下的两个排针用黄色跳线帽盖上。

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201009234523.png" style="zoom:50%;" />

&ensp;接好后连接到电脑，右击看下我的电脑【属性】--设备管理器--【端口】点开，看看有没有ch340驱动，有就可以打开软件使用了,如图：

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201009234831.png)

### 情况一

&ensp;如没有驱动，看看其他设备里面有没有一个带感叹号的usb2.0的设备，有的话，右键更新驱动，不要选择联网更新，选择浏览计算机以查找驱动程序软件手动安装。

### 情况二（我遇到的是该种情况，按照下述解决）

&ensp;端口有ch340驱动，软件检测无NFC设备,这时只要将红色板子SDA和SCL这两个线换一下即可，其他线都不动，检测出有NFC设备，然后打开软件使用就可以了。

## 运行 MifareOneTool 软件，具体破解操作

- [X] 第一步:检测链接【出现NFC设备】；

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201009235536.png)

- [X] 第二步:将自己的卡放上后【点击扫描卡片】后【点击检测加密】（SAK值为08一般表示可解）；

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201009235757.png)

- [X] 第三步:【点击一键解原卡】等待解密过程，等待跳出对话框后保存DUMP文件，保存后将卡片拿开；
- [X] 第四步:高级操作模式，【点击Hex编辑器】后，【点击左上角文件】，【点击打开】打开保存的解密dump文件，【点击扇区0】，复制第0块信息的前8位数，【再点击文件】-新建后【点击工具】，在【点击修改UID】，将复制的8位数替换上去，再【点击文件后另存为MFD文件】；
- [X] 第五步:将cuid卡放上去，【点击CUID写】，选中刚保存的MFD文件，进行写入，需要写入64块才算完成，一定要显示完【成写入64/64个块】【等于0扇区已写好，接下来就是模拟了】；
- [X] 第六步:再把cuid卡给手环模拟，模拟成功后，再将手环放到pn532模块上【可以去除表带，放表芯背面到pn532上面】，【点击扫描卡片】，页面有显示读到手环的数据【结果要显示有数据=1才可以，=0是没扫到，需要移动位置重新扫描】，再【点击CUID写】，将第一个保存的dump文件写入直到完成即可，显示63/64块即可【原理，前面已经模拟了1块进去了，所以只需63即可】；

![](https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201010000102.png)

## 测试模拟成功

<img src="https://cdn.jsdelivr.net/gh/Nanzet/nanzet-imgs/images/20201010000225.png" style="zoom:50%;" />
