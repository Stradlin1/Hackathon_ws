# 2026-10-21 — 请求生命周期修复

## 目标

P0 第四项：原来的请求只有「发出 → 接受/拒绝」两下，拒绝后永久不可再发；同一拾获可以被无限请求；接受一个请求后其他 pending 还挂着，甚至可能出现同一物品被接受两次。这一轮把请求变成可恢复、有上限、有结束清理的状态机。

## 决策

- **同一拾获最多 3 个 pending**：防止一个请求刷屏/骚扰；拾获者在「我的记录」里比较后决定。
- **拒绝后 24 小时冷却**：冷却到期可以重新发起。仍不改 `match_requests` 的主键/状态值，而是新增 `request_history` 记录结束的尝试；冷却到期时删除旧的 rejected 行、重新插入 pending。
- **pending 不把物品移出候选池**：有意为之。不然第一个（可能是冒领的）请求就会阻塞其他人；用上限 3 控制骚扰，而不是先到先得。
- **接受一个请求后，自动关闭其他待确认请求**：所有涉及该拾获或该失物的 pending 改为 rejected，并写 history。这样同一物品不会被接受两次，请求者也不会永远停在 pending。
- **已配对物品拒绝新请求/接受**：`_is_matched` 同时检查拾获和失物。
- **页面显示真实状态**：待确认/已配对禁用按钮；拒绝冷却中显示剩余时间；冷却结束出现「重新发送匹配请求」。
- **联系方式门禁不变**：仍然只有 `accepted` 后 `MatchRequests.accepted()` 返回邮箱。

## 改了什么

- `matching/requests.py`：新增 `request_history` 表、`pair_ids()`、`cooldown_text()`、`state()/state_pair()`、`_is_matched()`；重写 `create()` 与 `respond()`；`cancel_for_item()` 连带删除 history。
- `state/interactive_match.py`：请求确认区显示 pending/accepted/rejected 状态，按钮按冷却与状态禁用/改名。
- `state/profile.py`：待确认数量提示；接受/拒绝失败 warning；发出的 rejected 请求显示冷却或「重新发送匹配请求」。
- 测试：新增 `tests/test_requests.py`，并修正交互页烟测的 fake。
- 文档：新增 `.dsh/agents/request-lifecycle.md`，同步 architecture、data-model、privacy、README、AGENTS、backlog、operations。

## 验证

- `pytest -q`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）→ **94 passed**。
- 真实数据（键盘失物 ↔ 键盘拾获）：
  - alice 发送请求 → `pending`；匹配页按钮禁用，提示「已发送请求，等待对方确认」。
  - bob 在「我的记录」看到「共 1 个待确认请求」并拒绝 → alice 的「我发出的请求」显示「已拒绝」与「冷却中：24 小时后可重新发起」，没有重发按钮。
  - 把 `request_history.ended_at` 提前 25 小时后再看 → 出现「重新发送匹配请求」；点击后回到 `pending`。
  - 页面全程不出现邮箱；联系方式仍然只在 accepted 后出现。
- `compileall` 通过；`check_links.py` 0 broken（最终计数见收尾验证）。

## 未做 / 留给后续

- 24 小时冷却与上限 3 未用真实数据校准。
- 自动关闭的请求在状态上仍显示“已拒绝”，没有独立的 closed 状态或原因。
- 拒绝/自动关闭不会主动通知请求者；下次打开「我的记录」才看到。
- 没有按用户/按天的请求速率限制。
- 本机工作副本没有 `.git` 且未安装 git，因此没有按 `dsh` 分支提交；改动只存在于工作区。
