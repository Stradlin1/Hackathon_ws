# 2026-10-21 — 已归还/归档生命周期

## 目标

P0 第三项：让用户可以**结束一件报告但保留历史**。原来的「撤销登记」是硬删除，无法留下“这件东西已经还了”的记录，也不适合已配对的物品。

## 决策

- **新表 `item_status`**：`item_id` 主键、`status`（`returned`/`archived`）、`updated_by`、`updated_at`、`note`。不改既有五张表。
- **没有 `active` 行**：没有状态记录就是进行中；恢复 = 删掉状态行。
- **候选池统一过滤**：`Database.get_unmatched_lost_items()` 与 `get_unmatched_found_items()` 都 LEFT JOIN `item_status`，状态非空即排除。浏览页、匹配会话、通知生成都复用这个入口，不在页面里各写一套。
- **我的记录分流**：进行中与已处理分开；进行中卡片有「处理」按钮，打开对话框选已归还/归档并写可选备注；已处理区可「恢复为进行中」。
- **通知跳过已处理失物**：`notify_for_found_item()` 额外检查 `get_item_status()`；通知页对已处理的拾获/失物显示状态，失物已处理时不再给「查看候选」。
- **匹配页兜底**：`interactive_match` 渲染前检查查询物品状态；已处理时只给提示与返回按钮，避免旧会话继续展示候选。
- **单方标记**：失主或拾获者都可以结束自己那件报告；没有双方交接确认（留给后续）。
- **撤销仍然保留**：处理保留历史，撤销硬删除；两者并列，已 `accepted` 的物品仍然不能撤销。

## 改了什么

- 新增 `matching/lifecycle.py`：`Lifecycle`、`status_label`、`STATUSES`。
- `db_manager.py`：`create_table()` 新增 `item_status`；两个 `get_unmatched_*` LEFT JOIN 过滤；新增 `get_item_status()`。
- `state/profile.py`：进行中/已处理分流、`_status_dialog`、`_done_card`、恢复；`_date_text` 旁新增 `_timestamp_text` 处理 epoch。
- `state/notifications.py`：显示已处理状态；失物已处理时禁用「查看候选」。
- `state/interactive_match.py`：已处理物品的状态检查。
- `matching/notifications.py`：跳过已处理的失物。
- 测试：`tests/test_lifecycle.py`、`test_notifications.py` 的已处理跳过、`test_pages_smoke.py` 的处理对话框。
- 文档：新增 `.dsh/agents/lifecycle.md`，同步 architecture、data-model、privacy、ui、README、AGENTS、backlog、operations。

## 验证

- `pytest -q`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）→ **83 passed**。
- `compileall` 通过；`check_links.py` 0 broken（最终计数见下一轮验证）。
- 真实数据：
  - 对一条失物（`942228599187412484`）写入 `returned`。
  - `get_unmatched_lost_items()` 不再包含它；「我的记录」出现「已处理的物品」与「已找回」。
  - 点「恢复为进行中」→ 状态清空，失物重新进入未配对池。
- 过程中发现并修复一个真实 bug：已处理卡片的「处理时间」把 epoch 整数传给了只接受 `Item` 的 `_date_text`，抛 `AttributeError`；新增 `_timestamp_text`。
- AppTest 不会执行 `st.dialog` 里面的表单提交：对话框确认在 AppTest 下不落库；页面分流用直接写状态验证，对话框逻辑用 fake UI 单测覆盖。真实浏览器走的是项目已有的 dialog 模式，仍需人工点一次确认。

## 未做 / 留给后续

- 双方交接确认；当前是单方标记。
- 自动归档/保留期。
- 首页统计仍按已登记总数，未区分进行中/已处理。
- 本机工作副本没有 `.git` 且未安装 git，因此没有按 `dsh` 分支提交；改动只存在于工作区。
