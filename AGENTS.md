# 404NotFound — 项目索引（智能体入口）

一个 Streamlit 单机应用：把失主的**文字描述**与拾获者的**物品照片**做跨模态匹配，按证据重排，并用信息增益追问收敛候选。
本仓库**只负责这套本地应用**：页面流程、指纹抽取、检索/重排、SQLite 存储与双方确认。**不负责**账号后端（交给 `streamlit-authenticator` + 本地 `config_auth.yaml`）、云端部署、多租户或真实校方数据库对接。

权威来源：本仓库的代码与 [`README.md`](README.md)。【待验证】是否存在比赛评分标准/提交要求——2026-10-21 询问未获答复，暂以 README 与代码为唯一权威；拿到后落成 `.dsh/agents/` 独立文档并在路由表加一行（见 [`backlog.md`](backlog.md)）。

> [!IMPORTANT]
> 1. **本文件只是索引 + 工作方式 + 红线 + 路由表 + 目录结构**。分主题事实在 `.dsh/agents/`——动手前按路由表读对应文档，改完回来更新它。
> 2. **每句话都必须能归类**：`【事实】`= 代码/README/实测；`【设计】`= 本仓库已实现的方案；`【待验证】`= 假设，验证前不能作为依据。**没标 `【事实】` 的数字不许写进代码常量。**
> 3. 本仓库已在本地环境跑通（117 tests；`streamlit` HTTP 200），上台演示页在 `showcase/`。本地 `items.db` 已灌入 6 个账号的演示数据：12 件拾获 + 18 件失物（每个账号 2 + 3），照片在 `demo/photos/`。当前卡点见 [`backlog.md`](backlog.md)。

## 工作方式：git 分支纪律（**先读这条**）

1. **所有开发在 `dsh` 分支上进行。** `main` 是用户已确认的状态，不直接在其上改代码。
2. **合并回 `main` 必须经用户明确确认。** 改动小、测试通过都不是理由。
3. **每次提交前机械校验分支**，不要相信记忆（工作区可能被另一个终端切走）：
   ```sh
   [ "$(git branch --show-current)" = dsh ] || { echo "wrong branch, aborting"; exit 1; }
   ```
   只打印分支名不算检查：`&&` 不会因为 `echo` 输出错误就停下。
4. **合并前先把 `.dsh/agents/` 与 `.dsh/logs/` 更新到与代码一致。**

## 红线（不翻文档也必须记住）

1. **指纹只接受有原文证据的值。** 模型提案若字面没有出现在描述/图注里，必须丢弃；与用户描述冲突时以描述为准。→ [fingerprint](.dsh/agents/fingerprint.md)
2. **缺失属性中性，矛盾才扣分。** 证据项 = `(一致 − 0.8×矛盾) / 可比项`；任一边缺失就不参与。→ [matching-engine](.dsh/agents/matching-engine.md)
3. **基础分：语义 72%、证据 28%；时间/地点软先验最多 +0.05，缺失/未知为 0、不扣分。** 证据从全一致(+1)翻到全矛盾(−1)只值 0.28 分，等价于 **0.28 ÷ 0.72 = 0.389 的 CLIP 相似度差**；软先验只加不减，不改变“矛盾扣分”的方向。→ [matching-engine](.dsh/agents/matching-engine.md)
4. **排序分不是所有权概率。** 页面与文档都必须说「排序指标」（ranking metric），不得改称概率或置信度。→ [matching-engine](.dsh/agents/matching-engine.md)
5. **联系方式只在对方 `accept` 之后可见**，且请求只能由该报告的所有者发起。→ [privacy](.dsh/agents/privacy.md)
6. **澄清答案只以「属性」形式落库**：存归一化值 + `confirmed` 字段名，不存回答原文与问答历史；这些属性对匹配对象可见。→ [privacy](.dsh/agents/privacy.md)
7. **不改既有表结构**：`items`/`users`/`lost_items`/`found_items`/`matches` 已存在；新能力只能 `CREATE TABLE IF NOT EXISTS` 新表。→ [data-model](.dsh/agents/data-model.md)
8. **上传图片先去 EXIF 再存储/编码**（`clean_image`），模型不可用时必须降级而不是崩溃。→ [privacy](.dsh/agents/privacy.md)、[operations](.dsh/agents/operations.md)

## 路由表：要做什么 → 先读什么

| 我要做的事 | 先读 |
| --- | --- |
| 改排序公式、权重、矛盾惩罚 | [`.dsh/agents/matching-engine.md`](.dsh/agents/matching-engine.md) |
| 改追问选择、信息增益、提问上限 | [`.dsh/agents/matching-engine.md`](.dsh/agents/matching-engine.md) |
| 改属性抽取、词表、生成式指纹、提案校验 | [`.dsh/agents/fingerprint.md`](.dsh/agents/fingerprint.md) |
| 加表/加字段/兼容旧 `items.db` | [`.dsh/agents/data-model.md`](.dsh/agents/data-model.md) |
| 改配对请求、联系方式可见性、隐私 | [`.dsh/agents/privacy.md`](.dsh/agents/privacy.md) |
| 改订阅、站内通知、未读数、通知阈值 | [`.dsh/agents/notifications.md`](.dsh/agents/notifications.md) |
| 改已归还/归档、候选池过滤、我的记录状态 | [`.dsh/agents/lifecycle.md`](.dsh/agents/lifecycle.md) |
| 改登记入口、近期动态、公开可见性、发布时间 | [`.dsh/agents/report-and-feed.md`](.dsh/agents/report-and-feed.md) |
| 改配对请求状态机、上限、冷却、自动关闭 | [`.dsh/agents/request-lifecycle.md`](.dsh/agents/request-lifecycle.md) |
| 改发布时间、内容指纹、图片/文本查重、水印 | [`.dsh/agents/anti-copy.md`](.dsh/agents/anti-copy.md) |
| 改界面、样式、顶栏、卡片 | [`.dsh/agents/ui.md`](.dsh/agents/ui.md) |
| 改上台展示页、演示数据、讲稿 | [`.dsh/agents/showcase.md`](.dsh/agents/showcase.md) |
| 加页面、改跳转、Streamlit 状态 | [`.dsh/agents/architecture.md`](.dsh/agents/architecture.md) |
| 装环境、跑不起来、模型权重、离线 | [`.dsh/agents/operations.md`](.dsh/agents/operations.md) |
| 接/关 DeepSeek 视觉、图片识别走哪个模型 | [`.dsh/agents/operations.md`](.dsh/agents/operations.md) |
| 提交前逐条核对红线 | [`.dsh/agents/invariants.md`](.dsh/agents/invariants.md) |
| 现在卡在哪、下一步问谁 | [`backlog.md`](backlog.md) |
| 为什么这么定、踩过什么坑 | [`.dsh/logs/README.md`](.dsh/logs/README.md) |

## 仓库结构（**只记目录与根文件，不记目录里的文件**）

| 路径 | 职责 |
| --- | --- |
| `AGENTS.md` | 本文件：索引 + 工作方式 + 红线 + 路由表（**给智能体**，每轮自动加载） |
| `README.md` | 人类入口：能力、匹配流程、页面操作、安装、配置、测试、模块地图、已知限制 |
| `backlog.md` | 已知未完成的事，按「卡住什么」分组 |
| `MODIFICATIONS.md` | 本次会话的改动说明、验证结果与后续建议（面向人） |
| `.gitignore` | 什么不进版本控制，以及为什么 |
| `.streamlit/config.toml` | 主题令牌与工具栏默认值（启动时读取） |
| `.dsh/agents/` | 分主题的项目事实、设计决定、不变量、排查流程 |
| `.dsh/logs/` | 过程记录，只追加不改写正文 |
| `.dsh/tools/` | 可执行的校验脚本（链接检查） |
| `app.py` | Streamlit 入口与页面分发 |
| `db_manager.py` | `items.db` 既有表访问层（物品、用户、归属、匹配） |
| `reset_db.py` | **破坏性**：删除 `items.db` 并写入合成样例 |
| `create_demo_users.py` | 生成 `config_auth.yaml`：六个演示账号（密码=用户名）+ 随机 cookie key |
| `seed_demo.py` | 从 `demo/photos/`（回退 `input/`）照片灌入多用户演示数据：6 个账号各 2 拾获 + 3 失物，已有物品时拒绝运行 |
| `evaluate.py` | 离线评估：Recall@1/5、MRR；对比时间/地点软先验开关，支持自定义 labels JSON |
| `download_models.py` | 一次性拉取所有模型权重（默认 hf-mirror，已缓存则跳过） |
| `run.sh` | 以 `HF_HUB_OFFLINE=1` 启动 Streamlit |
| `rooms.json` | 地点下拉选项 |
| `config_auth.example.yaml` | 本地账号配置模板（真配置 `config_auth.yaml` 不入库） |
| `settings.example.yaml` | 可选配置模板（DeepSeek key、指纹生成器）；复制为 `settings.yaml` 后生效，真文件不入库 |
| `requirements.txt` / `requirements-dev.txt` | 运行 / 测试依赖 |
| `matching/` | 指纹、模型、检索、重排、指纹存储、配对请求 |
| `state/` | 每个页面的 Streamlit 流程 |
| `ui/` | 展示层：设计令牌 / 全局 CSS / 顶栏与卡片组件 / SVG 图标 |
| `tests/` | 算法与页面烟测（模型权重被 mock） |
| `static/` | 品牌图 `logo_rounded.png`（页面图标与顶栏） |
| `demo/photos/` | 已提交的 12 张演示照片（8 张 CC BY 2.0，署名见 `SOURCES.md`），供 `seed_demo.py` 复现同一份数据 |
| `showcase/` | 上台演示用的静态单页（11 屏 + 交互，含语义/证据原理），数据由 `build_demo.py` 从 `items.db` 生成 |

**为什么只记目录**：列到文件就成了文件系统的第二份副本，下一次提交就过期；目录职责很少变，写下来才守得住。想知道有哪些模块，代码才是权威。同理不要写「某目录下有几个文件」。

## 知识管理约定（每次会话遵守）

- **`AGENTS.md`**——索引、工作方式、红线、路由表。保持精简，细节进 `.dsh/agents/`。
- **`.dsh/agents/`**——改代码前按路由读，**改完回来更新**；一个事实只有一个家，别处只链接。
- **`backlog.md`**——缺什么、找谁、卡住什么；**做完就删**，不留完成记录。
- **`.dsh/logs/`**——当天快照，不改写；索引是手工维护的 [`README.md`](.dsh/logs/README.md)。
- **顺序**：先更新 `.dsh/agents/` → 再写日志 → 再改 `.dsh/logs/README.md` 索引。
- **校验**：`python .dsh/tools/check_links.py` 检查所有相对链接与锚点。

**为什么本文件必须在仓库根目录**：DSH 只自动加载名为 `AGENTS.md` / `CLAUDE.md` 的指令文件，而位置决定作用域——根目录那份是项目级、每轮都在上下文里；放进 `.dsh/` 就只对那个目录生效。所以索引留在根目录，细节才敢外放。

## 相关文档

[`.dsh/agents/`](.dsh/agents/) 下的 [architecture](.dsh/agents/architecture.md)、[showcase](.dsh/agents/showcase.md)、[matching-engine](.dsh/agents/matching-engine.md)、[fingerprint](.dsh/agents/fingerprint.md)、[data-model](.dsh/agents/data-model.md)、[privacy](.dsh/agents/privacy.md)、[notifications](.dsh/agents/notifications.md)、[lifecycle](.dsh/agents/lifecycle.md)、[report-and-feed](.dsh/agents/report-and-feed.md)、[request-lifecycle](.dsh/agents/request-lifecycle.md)、[anti-copy](.dsh/agents/anti-copy.md)、[operations](.dsh/agents/operations.md)、[invariants](.dsh/agents/invariants.md)；未完成事项见 [`backlog.md`](backlog.md)，过程见 [`.dsh/logs/`](.dsh/logs/README.md)。
