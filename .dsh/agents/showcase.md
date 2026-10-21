# 上台展示页（showcase）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[架构](architecture.md) 说明页面状态机，[匹配与追问](matching-engine.md) 提供分数口径。

**本文件状态：`【事实】`**——读自 `showcase/` 与 `tests/test_showcase.py`（2026-10-22）。

## 它是什么

- 【设计】一个**独立静态站点**，不嵌进 Streamlit：舞台需要精确排版、全屏和动画，Streamlit 的 rerun 会在投影上闪。
- 【事实】`showcase/serve.sh` 用 `python3 -m http.server` 托管，默认 `127.0.0.1:8600`；`PORT` / `BIND` 可覆盖。
- 【事实】页面有 9 屏：封面、问题、现场匹配、分数解释、追问、隐私、架构、数据、收尾；键盘 `←/→`、空格、滚轮翻屏，`location.hash` 记页码。
- 【设计】深色舞台主题（`#070E18` 底），沿用 app 的品牌 navy 与 teal/amber 语义色；字号用 `clamp()`，1920×1080 与 1440×900 都不出现纵向滚动。

## 目录与职责

| 路径 | 职责 |
| --- | --- |
| `index.html` | 9 屏结构；文案写死，数字不写死 |
| `assets/stage.css` | 舞台主题、布局、动效、响应式与 `prefers-reduced-motion` |
| `assets/stage.js` | 翻页、FLIP 重排、属性对照、权重滑块、追问、隐私门 |
| `assets/img/` | 构建时复制的候选照片与二维码 |
| `data/demo.json` | 构建产物（已提交）；页面唯一数据源 |
| `build_demo.py` | 只读 `items.db`，调用真实引擎生成 JSON 与图片 |
| `serve.sh` | 本地静态服务 |
| `SCRIPT.md` | 每屏一句讲稿 + 现场检查 |

## 数据契约（`data/demo.json`）

| 键 | 内容 |
| --- | --- |
| `meta` | 物品/账号/配对数、Recall@1 与 MRR（prior 开/关）、`app_lan` |
| `pair` | 主故事：失物描述、属性、地点；对应拾获描述与照片 |
| `candidates` | 6 个候选：分数、语义分、证据分（-1..1 与 0..1）、一致/矛盾字段、属性、是否为目标 |
| `weights` | `0.72 / 0.28`，与 `matching/engine.py` 一致 |
| `clarify` | 真实失败样本：问题、选项、前后各 4 个候选、名次变化 |
| `privacy` | 占位联系信息（`example.invalid` 与打码号码） |

- 【事实】`candidates` 的 `score` 由 `rank_candidates` 给出；`evidence` 由构建脚本按 `WEIGHTS` 从 `matches/conflicts` 反推，只用于页面上的权重演示。
- 【事实】页面上的权重滑块**只演示**语义/证据的比例，线上公式固定 `0.72 × 语义 + 0.28 × 证据`，不是产品参数。

## 离线与失败模式

- 【事实】无 CDN、无外部字体、无构建步骤；`tests/test_showcase.py` 会拒绝除 `127.0.0.1:8501` 与 SVG 命名空间以外的 URL。
- 【事实】`fetch` 加载 JSON，所以必须通过 `serve.sh`（或任意静态服务器）打开；`file://` 会被浏览器拦截并显示提示。
- 【事实】缺 `demo.json` 时页面显示「先运行 python showcase/build_demo.py」，不白屏。
- 【事实】二维码编码本机局域网地址 + `8501`；换网络后重跑构建脚本即可。

## 怎么改

- 改文案、屏数：直接改 `index.html`；不要把分数写死在 HTML 里，从 `demo.json` 渲染。
- 改演示哪一对：改 `build_demo.py` 里 `SAMPLES[0]` 的选择与 `clarify` 的样本，重跑脚本。
- 改视觉：只动 CSS 变量与 `stage.css`，结构不要跟着改。
- 改完跑：`python showcase/build_demo.py && python -m pytest -q tests/test_showcase.py`。

## 已知边界

- 【事实】追问故事是**真实的失败样本**：耳机 3 → 2，并没有回到第 1；页面上也写明「不夸大」。
- 【事实】只有 12 对演示数据，页面上的 11/12 与 0.944 来自当前 `items.db`；换库后数字会变。
- 【设计】没有演讲者备注窗口、没有导出 PDF；要纸质备份就浏览器打印。
