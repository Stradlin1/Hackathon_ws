# 2026-10-22 · 演示集补一对「不同特征」的水杯与双肩包

## 需求

`todo.md`：从互联网上找不同特征的水杯、书包，加到登记物品里，并选好失主和拾获者。

## 选图

现有 `demo/photos/` 已有一个透明塑料水杯（FUGUANG）和一个黑色拉杆双肩包，所以这次要的是**特征明显不同**的两件：

| 文件 | 内容 | Open Images ID | 作者 / 许可 |
| --- | --- | --- | --- |
| `梅森杯.jpg` | 蓝色玻璃梅森杯，灰色金属旋盖，杯身 Ball / PERFECT MASON 浮雕，泡着柠檬和薄荷 | `c914001730777e42` | adinaplus / CC BY 2.0，<https://www.flickr.com/photos/48726352@N08/8177083595> |
| `绿色双肩包.jpg` | 绿色方形帆布双肩包，正面红白圆形标志，细肩带，前置拉链袋 | `7491dc5b881626cd` | watashiwani / CC BY 2.0，<https://www.flickr.com/photos/yukochatulapoly/5055254596> |

两张都从 Open Images V6 验证集按 ID 下载，缩到最长边 1024、JPEG q88，与原有 8 张一致；署名补进 `demo/photos/SOURCES.md` 的「追加 2 张」小节。
Wikimedia Commons 在这台机器上不可达（连接超时），Open Images S3 可用，所以沿用仓库既有的取图路径。

## 登记与归属

写进 `seed_demo.SAMPLES` 末尾，保持「拾获者 ≠ 失主」的约定：

- 梅森杯：拾获 **alice**（食堂），失主 **carol**（食堂）。
- 绿色双肩包：拾获 **bob**（图书馆），失主 **david**（图书馆）。

失物描述换了说法，但保留了颜色/材质/标记/形状这些可核对的事实；拾获描述带上 Ball 浮雕、红白圆标这类独特标记。

## 写进本地库

`seed_demo.py` 在库里已有物品时会拒绝运行，所以没有重建库。用一次性脚本（不入库）复用同样的写入流程：
`clean_image` → `encode_image` / `encode_text` → `insert_found_item` / `insert_lost_item` →
`FingerprintStore` → `ReportMeta.publish` → `ImageHashes`。新增 2 件拾获 + 2 件失物，本地库从 33 件变 37 件。
脚本按描述去重，重复运行不会重复插入。

## 验证

- 用真实引擎各跑一次排序：
  - carol 的梅森杯失物 → 第 1 名就是 alice 的拾获（0.521，第 2 名 0.337）。
  - david 的双肩包失物 → 第 1 名就是 bob 的拾获（0.535，第 2 名 0.348）。
- 应用里用关键词「梅森杯」「绿色方形」能在近期动态筛出，照片、水印、属性芯片都正常。
- `tests/` 全量 119 passed；`check_links.py` 0 broken。

## 文档与快照

- 更新 `seed_demo.py` 顶部计数、README / AGENTS 的结构表与演示数量、`.dsh/agents/{operations,report-and-feed,notifications}.md`、backlog 的评估样本条目。
- 上台展示页仍是**旧 12 对快照**，没有重建 `showcase/data/demo.json`；`.dsh/agents/showcase.md` 已写明。等需要时再在干净库上重跑 `build_demo.py` 并同步页面数字。

## 追加（同日）：再补 4 个水杯 + 4 个书包

- 图片：继续用 Open Images V6 验证集（Bottle / Mug / Backpack 类），CC BY 2.0；8 张，署名见 `demo/photos/SOURCES.md` 的「再加 8 张」。
- 水杯：Volvic 矿泉水（carol 拾 / erin 失，食堂）、CISOWIANKA 矿泉水（david / frank，图书馆）、巧克力马克杯（erin / alice，自习区）、天际线马克杯（frank / bob，教室）。
- 书包：红黑双肩包（alice / carol，体育中心）、迷彩双肩包（bob / david，停车场）、ANIMEEXPO 双肩包（carol / erin，主入口）、黑色电脑双肩包（david / frank，礼堂）。
- 写入：复用按描述去重的一次性脚本，库从 37 → 53 件；seed 口径变成 22 件拾获 + 28 件失物。
- 调参：迷彩包最初被绿色 Kånken 压到第 2——「黑色扣带」把它的颜色读成黑色，补上「长方形」后仍和 Kånken 的「方形」冲突不足；去掉「黑色扣带」后颜色回到绿色，回到第 1。CISOWIANKA 与 ANIMEEXPO 也被标签/拉链里的「白 / 黑」带偏，去掉干扰词后分别读成蓝色 / 绿色。
- 验证：8 对全部由真实引擎排到第 1（0.476–0.563）；`pytest` 119 passed。
- 展示页仍是 12 对快照，未重建 `showcase/data/demo.json`。

