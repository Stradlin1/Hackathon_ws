# 2026-10-21 — 剩余英文化盘点与 backlog 收口

## 目标

用户指出界面里仍有英文（最明显的是「丢东西」页的地点下拉），但要求**本轮先不改**，先把这些点和今天发现的问题写进 backlog，并把今天的改动都留在 `dsh` 分支。

## 做了什么

1. 盘点应用里仍会显示英文的位置：
   - `rooms.json` 的 12 个地点值；
   - BLIP 生成的英文图注（会预填进拾获物品的描述框）；
   - Streamlit 自带控件（文件上传、日期选择器、右上角菜单、回车提示）；
   - `reset_db.py` 的英文样例描述与地点；
   - `static/` 两张英文 `Lost`/`Found` 图片。
2. 重写 [`backlog.md`](../../backlog.md)：删掉已经完成的「本机测试跑不通」条目，新增「界面完全中文化」与「真实照片下的端到端演示」两组，保留排序/配对策略与小项。
3. 没有改 `rooms.json`、没有改任何页面代码；本轮只动 backlog 与本日志。
4. 复跑测试与文档校验。

## 今天的提交（dsh）

| 提交 | 内容 |
| --- | --- |
| `43c2702` | 建立 `.dsh/` 渐进披露知识库、`AGENTS.md`、`backlog.md`、链接校验脚本 |
| `41d553a` | README 覆写为中文并贴合当前实现 |
| `519be8d` | 前端文案中文化（页面、认证表单、状态/方法、属性值） |
| `09f948b` | 自建中文注册表单，替换认证库的英文/验证码表单 |
| `7075239` | 模型本地缓存优先、BLIP 上 GPU、HF 镜像说明 |
| 本次提交 | 剩余英文化盘点 + backlog + 日志 |

## 关键决策

### 为什么本轮不改 `rooms.json`

它同时是 UI 选项和已经入库的 `items.location` 值。直接改文件会让旧记录仍显示英文，新旧数据混用；需要先定中文译名，再决定是迁移旧值还是加映射。这个决定属于演示/产品，不属于本轮代码修正。

### 为什么英文图注不顺手翻译

BLIP 是英文 caption 模型，翻译需要另一个模型或调用；属于模型选型与性能权衡，不能靠改文案解决。

### Streamlit 内置控件不追

`Browse files`、月份名、右上角菜单、`Press Enter to submit form` 都没有本地化 API。要做到只能自定义组件或注入 CSS，成本和收益不成比例，先作为已知限制记录。

### 已修复的问题不再进 backlog

HuggingFace 不可达、缓存不完整、BLIP 在 CPU 上这些问题已经修复，事实写进 [`operations`](../agents/operations.md) 与 [caption-slow-hf](2026-10-21-caption-slow-hf.md)；backlog 只留未完成项。

## 验证

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` → **24 passed**。
- `python3 .dsh/tools/check_links.py` → **0 broken**。
- `git diff --check` 通过；本轮没有代码/UI 改动。
- 未跑真实照片的端到端流程（仍无照片数据）。

## 未做（明确留给后续）

- 没有改 `rooms.json` 或任何页面文案。
- 没有灌入真实照片或样例数据。
- 没有把 `HF_ENDPOINT`/`HF_HUB_OFFLINE` 固化成启动脚本。
- 未合并 `main`。
