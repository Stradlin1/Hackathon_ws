# 2026-10-21 — README 改为中文并按当前实现重写

## 目标

README 是给人的入口，但仍是英文，且只讲算法，缺少页面流程、模块地图、已知限制与当前环境提示。用户要求覆写为中文，并让它贴合迭代后的代码。

## 做了什么

1. 逐条把旧 README 的陈述与代码对照：`app.py`、`state/*`、`matching/*`、`db_manager.py`、`tests/*`。
2. 覆写 `README.md`（203 行），结构改为：定位与边界 → 能力 → 匹配流程 → 页面与操作 → 快速开始 → 配置项 → 数据与隐私 → 测试与校验 → 模块地图 → 已知限制 → 常见问题 → 知识库与开发约定。
3. 同步更新 `AGENTS.md` 结构表里 README 一行，使其职责与新版一致。
4. 复跑 `.dsh/tools/check_links.py`。

## 关键决策与依据

### 中文正文，UI 文案保留英文

界面按钮与提示是英文（`I lost something`、`Send match request`、`Confirmed matches` 等），所以正文用中文、引用界面时保留原文，避免读者对不上屏幕。依据是 `state/*.py` 里的字符串字面量。

### 不复制权威数字与版本号

旧 README 直接写模型名与流程；新版只保留用户能感知的行为（最多四轮追问、展示前 5 个候选、8 MB 上传上限），权重、0.389 阈值、表结构统一链到 `.dsh/agents/`。依赖版本指向 `requirements.txt`，避免升级时两处过期。

### 把「已知限制」写进 README

这是旧 README 最缺的部分，也是迭代后最容易踩的行为：

- 时间/地点不参与排序（代码 `matching/engine.py` 只比较六类属性）；
- 被拒绝的配对无法重发（`match_requests` 主键 + `INSERT OR IGNORE`）；
- 待处理请求不会把物品移出候选池（未匹配查询只看 `matches`）；
- 只有 mock 测试，没有真实模型端到端记录。

### 工作流只留一句 + 链接

分支纪律的权威在 `AGENTS.md`。README 只保留「在 `dsh` 开发、合并需确认、提交前跑 guard」，避免同一规则出现两份完整版本。

## 从原始资料里读出的结论

- `git log --stat` 显示 README 在 `37e1c6e`（第四次提交）与 `matching/` 重写**同一个提交**里改过 124 行；旧的 `someone_found.py`、`this_your_item.py` 等页面也在该提交删除。**README 并没有停留在旧架构上**，本次主要是语言、覆盖面与可操作性，而不是大批纠错。
- 唯一发现的表述偏差：旧 README 把 `test_fingerprint_database_upsert` 说成 "SQLite fingerprint migration"，但仓库没有迁移脚本，只有建表 + upsert；新 README 已改成事实描述。
- 旧 README 未说明但代码确实存在的行为：刷新匹配页会丢会话、候选只展示前 5、请求下拉只列前 5、上传 8 MB / 2000 万像素 / 最长边 1600、注册重写 `config_auth.yaml`。

## 中途改正过的地方

- 初稿写「注册会把新账号写回该文件」，核对 `state/register.py` 后改为「重写该文件，并在 `users` 表插入账号」——认证库是否把新用户并入传入的 `config` 没有实测，不能断言。
- 初稿准备把权重表和 0.389 阈值搬进 README，最终改为链接 `matching-engine.md`，避免第二份权威数字。
- 每个数字（4 轮、top 5、8 MB、2000 万像素、1600）都回代码确认后才写入，没有沿用旧 README 的措辞。

## 验证

- `python3 .dsh/tools/check_links.py`：全部相对链接与锚点通过（0 broken）。
- `wc -l README.md`：203 行。
- `grep -n "MAX_QUESTIONS\|ranked\[:5\]\|8 \* 1024 \* 1024\|MAX_IMAGE_PIXELS\|thumbnail" ...`：与 README 中的数字一致（见 [matching-engine](../agents/matching-engine.md)、[privacy](../agents/privacy.md)）。
- `git diff --stat`：只改 `README.md`、`AGENTS.md`、本日志与索引，未触碰应用代码。

## 未做（明确留给后续）

- 仍未运行 `streamlit` / `pytest`：本机依赖缺失且 numpy 损坏（见 [operations](../agents/operations.md)），所以 README 不声称已在本机验证。
- 未改任何应用代码，未合并 `main`，未处理 `static/` 的去留。
- 注册回写 `config_auth.yaml` 的实际效果（新用户是否进入文件）仍待真实环境验证，已记录为不确定表述。
