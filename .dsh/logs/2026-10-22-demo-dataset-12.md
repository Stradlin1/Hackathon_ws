# 2026-10-22 · 演示数据扩到 12 组（含 Open Images 网图）

## 目标

原来的演示集只有 4 对（充电宝 / 水杯 / 键盘 / 鼠标），`evaluate.py` 的 Recall/MRR
几乎只能当冒烟测试。这次补 8 对，凑到 12 组：12 张拾获照片（bob）+ 12 条对应失物描述（alice）。

## 图从哪来

这台机器上 Wikimedia Commons、Openverse、Unsplash API 都不通，Pexels 的页面 403，
Bing 图搜按地区返回花瓣/素材站的图（许可不明，不能提交）。可用的只有：

- `images.pexels.com`（知道 ID 才能下，但没有可用的搜索接口）；
- Open Images V6（GCS/S3 可达）。

所以用 Open Images 验证集：先拉 `validation-annotations-human-imagelabels.csv` 和
`class-descriptions.csv`，按类别筛正样本，再从
`https://open-images-dataset.s3.amazonaws.com/validation/<ImageID>.jpg` 下载候选，
拼成 contact sheet 用视觉逐张挑。

挑中 8 类：耳机、钱包、棒球帽、背包、围巾、手提包、行李箱、雨伞。被淘汰的候选主要是
"人戴着物品"的构图、多物品合影、以及标注和画面不符的样本（例如标成 umbrella 的红色跑车）。

## 许可

8 张全部是 **CC BY 2.0**，作者与原始 Flickr 页面来自
`validation-images-with-rotation.csv` 的 `Author` / `License` / `OriginalLandingURL` 列，
逐条写进 `demo/photos/SOURCES.md`。缩放到最长边 1024 px、JPEG q88 后入库，
总共约 1.2 MB。

## 代码与文档

- `seed_demo.py`：样本从 4 条扩到 12 条，新增 `耳机 / 钱包 / 棒球帽 / 背包 / 围巾 / 手提包 / 行李箱 / 雨伞`，
  地点取自 `rooms.json`（图书馆、食堂、体育中心、教室、自习区、礼堂、停车场、主入口）。
- 每条的 `found` 按照片里真实可见的属性写（AKG 标志、CHARLOTTE HORNETS 刺绣、拉杆轮子、流苏等），
  `lost` 用不同措辞复述同一组事实，避免两边字面雷同。
- README / AGENTS / `.dsh/agents/{operations,data-model,anti-copy,report-and-feed,notifications}.md`
  里的 "4 张 / 4 对" 一并改成 12；`backlog.md` 删掉"static 里两张未引用图"（上一轮已删图）。

## 验证

在 `/tmp/seedtest` 里软链仓库代码、另建 `items.db` 试灌，不碰本地库：

```text
完成：12 件拾获（bob）+ 12 件失物（alice）    # 11.3 s（GPU，模型已缓存）
prior=on   pairs=12  Recall@1=12/12  Recall@5=12/12  MRR=1.000
prior=off  pairs=12  Recall@1=12/12  Recall@5=12/12  MRR=1.000
```

100% 是预期内的：失物描述本来就是照同一张照片写的，这组数据只能证明管线没坏，
不能证明模型在真实口述下的效果。`pytest -q` 仍是 108 passed。

## 本地库还没换

`seed_demo.py` 在库非空时会拒绝运行，所以本地 `items.db` 仍是早先的 4 对。要换成 12 对：

```bash
cp items.db items.db.bak
rm items.db
HF_HUB_OFFLINE=1 python seed_demo.py
```

（会丢掉现有的 pending 请求与通知，`items.db.bak` 留着可回滚。）
