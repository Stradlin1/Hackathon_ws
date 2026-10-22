# 演示照片来源与许可

`demo/photos/` 里的照片只用于本仓库的演示与离线评估（`seed_demo.py` / `evaluate.py`）。

## 原有 4 张

`充电宝.jpg`、`水杯.jpg`、`键盘.jpg`、`鼠标.jpg` 是项目自带的拍摄照片，随仓库提交。

## 新增 8 张

全部取自 **Open Images V6 验证集**（`validation` 子集），按图像 ID 从
`https://open-images-dataset.s3.amazonaws.com/validation/<ImageID>.jpg` 下载，
再缩放到最长边 1024 px、JPEG 质量 88。每张图的作者、原始页面与许可如下，
许可均为 **CC BY 2.0**（<https://creativecommons.org/licenses/by/2.0/>）：

| 文件 | Open Images ID | 作者 | 原始页面 |
| --- | --- | --- | --- |
| `耳机.jpg` | `dc8857479b0c8d32` | Jan-Willem Reusink | <https://www.flickr.com/photos/jimmybenson/6311981004> |
| `钱包.jpg` | `9b769fffb1ce4378` | Moki Meeh | <https://www.flickr.com/photos/mokimeeh/3942840723> |
| `棒球帽.jpg` | `3160e13a54ec1f30` | Randy Scribner Jr. | <https://www.flickr.com/photos/jupiter_jazz/34360927> |
| `背包.jpg` | `854bbae71c1315f0` | Dustin Gaffke | <https://www.flickr.com/photos/onepointfour/6526607393> |
| `围巾.jpg` | `e162cac021dbcf2a` | smittenkittenorig | <https://www.flickr.com/photos/smittenkittenoriginals/2830897176> |
| `手提包.jpg` | `3da7da182200a0ec` | Rosenfeld Media | <https://www.flickr.com/photos/rosenfeldmedia/3264752127> |
| `行李箱.jpg` | `ac4c3b2697cd78fa` | Dirk de Kok | <https://www.flickr.com/photos/dirkdekok/5458789550> |
| `雨伞.jpg` | `f8ca116285a527c4` | CasparGirl | <https://www.flickr.com/photos/caspargirl/7531060532/> |

Open Images 的标注数据以 CC BY 4.0 发布；上面的图像按各自原始许可（此处均为
CC BY 2.0）使用，转载时请保留本文件的署名与许可链接。

## 追加 2 张（2026-10-22）

为演示「不同特征的水杯 / 书包」补充，同样取自 **Open Images V6 验证集**，许可均为
**CC BY 2.0**，处理方式与上面 8 张一致（最长边 1024 px、JPEG 质量 88）：

| 文件 | Open Images ID | 作者 | 原始页面 |
| --- | --- | --- | --- |
| `梅森杯.jpg` | `c914001730777e42` | adinaplus | <https://www.flickr.com/photos/48726352@N08/8177083595> |
| `绿色双肩包.jpg` | `7491dc5b881626cd` | watashiwani | <https://www.flickr.com/photos/yukochatulapoly/5055254596> |


## 再加 8 张（2026-10-22）

继续补充「不同特征的水杯 / 书包」，同样取自 Open Images V6 验证集（Bottle 与 Mug 类），CC BY 2.0，最长边 1024 px、JPEG 质量 88：

| 文件 | Open Images ID | 作者 | 原始页面 |
| --- | --- | --- | --- |
| Volvic矿泉水.jpg | 49e6a10cc09950c8 | pyntofmyld | <https://www.flickr.com/photos/pyntofmyld/213297601> |
| Cisowianka矿泉水.jpg | 3f68d660d5fd07e5 | Jess Pac | <https://www.flickr.com/photos/7174132@N05/3878609409> |
| 巧克力马克杯.jpg | c88aa18f9fffa58d | Wapster | <https://www.flickr.com/photos/wapster/8296913114> |
| 天际线马克杯.jpg | 34aebaebe39bfaf0 | Carles Caño Valls | <https://www.flickr.com/photos/carlescv/6429975597> |
| 红黑双肩包.jpg | 0eef565649be3038 | www.homejobsbymom.com | <https://www.flickr.com/photos/76588981@N02/16990442068> |
| 迷彩双肩包.jpg | 2edc0212721c4f22 | Karl Baron | <https://www.flickr.com/photos/kalleboo/9400639906> |
| 动漫展双肩包.jpg | ad6c671913df1a7d | porcupiny | <https://www.flickr.com/photos/porcupiny/4789162348> |
| 黑色电脑双肩包.jpg | dc747e1d542bf243 | EHRENBERG Kommunikation | <https://www.flickr.com/photos/ehrenbergkommunikation/15823041733> |
## 换用自己的照片

把照片放进仓库根目录的 `input/`（同名文件优先用 `demo/photos/`），
`input/` 已被 `.gitignore` 排除，不会提交。
