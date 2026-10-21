# 归还与归档（非破坏性完成态）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[数据模型](data-model.md) 说明 `item_status` 表；[隐私](privacy.md) 说明备注归属；[架构](architecture.md) 说明页面入口；[通知](notifications.md) 说明已处理物品不再触发提醒。

**本文件状态：`【事实】`**——读自 `matching/lifecycle.py`、`db_manager.py`、`state/profile.py`、`state/interactive_match.py`、`state/notifications.py`（2026-10-21）。

## 解决什么问题

原来的「撤销登记」是硬删除：物品、指纹、请求一起消失，无法保留“这件东西已经还了”的记录。归还/归档让用户可以**结束一件报告但保留历史**，同时把物品移出候选池、浏览页与通知匹配。

## 状态

| 值 | 失物显示 | 拾获显示 | 含义 |
| --- | --- | --- | --- |
| `returned` | 已找回 | 已归还 | 物品已经回到失主手里 |
| `archived` | 已归档 | 已归档 | 用户主动关闭，不表示一定归还 |

- 【事实】`status_label(status, lost)` 负责中文显示；`lost=True` 时 `returned` 显示「已找回」。
- 【事实】没有 `active` 行；没有 `item_status` 记录就是进行中。
- 【事实】状态是单方标记，当前没有双方交接确认。

## 表

```sql
CREATE TABLE IF NOT EXISTS item_status (
  item_id INTEGER PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('returned', 'archived')),
  updated_by TEXT NOT NULL,
  updated_at INTEGER NOT NULL,
  note TEXT NOT NULL DEFAULT ''
)
```

- 【事实】`Database.create_table()` 会建立这张表，因为 `get_unmatched_*` 要在 SQL 里 LEFT JOIN 它；`matching/lifecycle.py::Lifecycle.__init__` 也会幂等建立，便于单独测试。
- 【事实】`Lifecycle.set_status()` 用 `ON CONFLICT(item_id) DO UPDATE` 覆盖状态与备注；备注截断到 80 字符。
- 【事实】`Lifecycle.clear()` 删除状态行，物品恢复为进行中。
- 【事实】不改既有五张表的列（红线 6）。

## 候选池与各页面

- 【事实】`Database.get_unmatched_lost_items()` 与 `get_unmatched_found_items()` 现在都 `LEFT JOIN item_status`，并要求 `st.item_id IS NULL`。所以已处理的物品：
  - 不出现在 AI 匹配的候选里；
  - 不出现在「最近拾获」浏览页；
  - 不会被 `notify_for_found_item()` 当作可提醒的失物。
- 【事实】`notify_for_found_item()` 额外检查 `db.get_item_status(lost_id)`，已处理的失物不再产生新通知。
- 【事实】通知页对已处理的拾获/失物显示状态文案；失物已处理时不再渲染「查看这件失物的候选」。
- 【事实】`interactive_match` 在渲染前检查查询物品的状态；已处理时只给提示和「前往我的记录」，不展示候选。
- 【事实】浏览页不需要额外判断，候选查询已经过滤。

## 「我的记录」怎么展示

- 【事实】`state/profile.py` 用 `Lifecycle.get()` 把失物/拾获分成「进行中」与「已处理」。
- 【事实】统计行显示进行中的失物/拾获数量与「已处理」数量；已处理的物品不再出现在前两个列表。
- 【事实】进行中的卡片有「处理」按钮，打开 `_status_dialog`：选 `returned`/`archived`、写可选备注、确认后写入 `item_status`。
- 【事实】已处理区显示状态徽标、备注、处理时间，并提供「恢复为进行中」。
- 【设计】「处理」与「撤销」并列：处理保留历史，撤销仍然硬删除；已 `accepted` 的物品仍然不能撤销。

## 隐私

- 【事实】`item_status.updated_by` 是操作者用户名，`note` 是本人备注；两者只在「我的记录」里展示给本人，不进入候选、浏览页或通知。
- 【事实】状态不改变联系方式门禁；`MatchRequests.accepted()` 仍是唯一的联系方式出口。
- 【事实】通知页只显示状态文案，不显示备注或 `updated_by`。

## 已知边界

- 单方标记：没有「双方都确认交接」的流程；失主或拾获者任何一方都可以结束自己那件报告。
- 没有自动归档/保留期；状态会一直保留。
- 首页统计仍然按「已登记」总数计算，不区分进行中/已处理；只有「我的记录」区分。
- AppTest 不会执行 `st.dialog` 里的表单提交；对话框逻辑用 fake UI 单测覆盖，页面分流用直接写状态验证。
- 标记已处理后，内存中的 `match_session` 仍可能存在；再次进入该物品的匹配页会被状态检查拦下。

## 怎么改

- 加状态：改 `STATUSES`、表 CHECK 约束（需要迁移旧库时不能只改 CREATE）、`status_label`；同步数据模型文档。
- 加双方交接确认：新表记录两方确认，再写 `item_status`；不要改既有 `matches` 表。
- 加自动归档：定时任务或登录时扫描 `items.time`；仍然是新表 + 应用层逻辑。
- 改候选过滤：`db_manager.py` 的两个 `get_unmatched_*` 是唯一入口，不要在页面里各自过滤。

## 测试

- `tests/test_lifecycle.py`：状态读写、覆盖、恢复、非法状态、候选池排除。
- `tests/test_notifications.py`：已处理的失物不再产生通知。
- `tests/test_pages_smoke.py`：处理对话框写入状态。
- 2026-10-21 真实数据验证：把一条失物标记为「已找回」→ 退出未配对池 → 「我的记录」出现已处理区 → 点「恢复为进行中」→ 状态清空、重新进入池。

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：状态表、候选池过滤、我的记录分流、通知与匹配页行为、隐私与已知边界。 |
