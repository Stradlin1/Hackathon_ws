# 2026-10-22 · 上台展示页（showcase）

## 目标

一个能直接在投影上讲的网页：6–8 分钟、9 屏、断网可跑、零前端构建。

## 为什么不做成 Streamlit 页面

舞台需要全屏、精确字号和不闪的动画；Streamlit 每次交互都 rerun，投影上会闪，排版也只能迁就它的 DOM。
所以做成独立静态站点，Streamlit 那边一个字符都没改。

## 结构

```text
showcase/
  index.html            9 屏：封面 / 问题 / 匹配 / 解释 / 追问 / 隐私 / 架构 / 数据 / 收尾
  assets/stage.css      深色舞台主题、动效、响应式、reduced-motion
  assets/stage.js       翻页、FLIP 重排、属性对照、权重滑块、追问、隐私门
  assets/img/           6 张候选照片 + 二维码
  data/demo.json        构建产物（已提交）
  build_demo.py         只读 items.db，生成 JSON 与图片
  serve.sh              python3 -m http.server，默认 8600
  SCRIPT.md             每屏一句讲稿
```

## 数据怎么来

`build_demo.py` 复用真实代码，不另写一套打分：

- `build_session` + `rank_candidates` 取主故事（充电宝）的 6 个候选与分数；
- `matches/conflicts` 与 `WEIGHTS` 反推证据分，页面才能用滑块演示语义/证据比例；
- `choose_question` 选出追问字段，回答前后各跑一次 `rank_candidates`；
- `evaluate_pair` + `summarize` 产出 Recall@1 与 MRR（开/关软先验）。

二维码编码本机局域网地址 + 8501，手机扫描能直接打开真实 app（前提是 app 在跑）。

## 设计上的选择

- 深色 `#070E18` 底，品牌 navy + teal/amber；投影对比度比浅色界面稳。
- 封面右侧放“失主卡片 → 0.562 → 拾获照片”的构图，开场就让人看懂两边是什么。
- 追问那屏用的是**真实失败样本**：耳机 3 → 2，错误候选被压下去但没有回到第 1；页面明写“不夸大”。
- 权重滑块是演示控件，页面上写明线上固定 0.72 / 0.28。

## 验证

- `pytest -q`：115 passed（新增 7 条 `tests/test_showcase.py`，覆盖数据契约、图片存在、离线约束）。
- 无头 Chromium 逐屏截图检查：9 屏 1920×1080，无 console 错误、无 404。
- `curl` 六个资源全部 200；页面里唯一的外链是 `http://127.0.0.1:8501`。

## 已知边界

- 数据是快照：换库或改 `seed_demo.py` 后要重跑 `build_demo.py`。
- 只做了 1920×1080 与 1440 宽度的断点，没在 Safari / Firefox 上逐项验证。
- 没有演讲者备注窗口；需要纸质稿就用 `SCRIPT.md`。

## 修订（同日，按用户反馈）

- 背景从近黑改成浅绿（`#EAF7F0` + 柔和光斑），文字与卡片整体换成深色系；
- 去掉 `scroll-snap`：滚到两屏之间就停住，不再强行吸附；
- 新增两屏原理：语义（真实 CLIP 向量 + cos 0.323）与证据/合并公式（e = 一致 − 0.8×矛盾 / 可比；0.72 / 0.28），数字全部来自 `build_demo.py`；
- 收尾按钮与二维码改用本机局域网地址（`meta.app_lan`），不再写死 127.0.0.1；
- 序号与页脚页码对齐（11 屏），讲稿同步更新。