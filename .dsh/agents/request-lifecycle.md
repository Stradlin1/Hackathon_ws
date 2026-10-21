# 配对请求生命周期

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[架构](architecture.md) 说明页面调用；[数据模型](data-model.md) 说明两张表；[隐私](privacy.md) 说明联系方式门禁；[匹配与追问](matching-engine.md) 说明候选排序。

**本文件状态：`【事实】`**——读自 `matching/requests.py`、`state/interactive_match.py`、`state/profile.py`（2026-10-21）。

## 状态机

```text
(无记录) --create（报告所有者）--> pending
pending --responder accept--> accepted  + INSERT matches(found, lost)
                                  └─ 其余涉及该拾获/失物的 pending 自动 rejected
pending --responder reject--> rejected  + request_history(rejected)
rejected --冷却结束 + create--> pending（删除旧的 rejected 行，history 保留）
```

- 【事实】`match_requests` 的主键仍是 `(found_item_id, lost_item_id)`，状态仍只有 `pending/accepted/rejected`，列没有改。
- 【事实】`request_history` 是新表，记录每次结束的尝试：`accepted`/`rejected`、请求人与响应人、开始与结束时间。
- 【事实】接受后写入 `matches(item1=found, item2=lost)`；一个物品只能被接受一次。
- 【事实】拒绝后 `match_requests` 行保留为 `rejected`，冷却到期后 `create` 删除它并重新插入 `pending`；旧尝试仍在 `request_history`。

## 规则

| 规则 | 值 | 位置 |
| --- | --- | --- |
| 同一拾获的待确认请求上限 | `MAX_PENDING_PER_FOUND = 3` | `matching/requests.py` |
| 拒绝后的冷却 | `REJECT_COOLDOWN_SECONDS = 24 小时` | 同上 |
| 谁能发起 | 报告所有者（由归属表推导，不由调用方传入） | `create` |
| 谁能接受/拒绝 | 只有 `responder` 本人，且状态必须是 `pending` | `respond` |
| 已配对物品 | 任一边已有 `matches` 行就拒绝新请求/接受 | `_is_matched` |
| 接受一个后 | 所有涉及该拾获或该失物的其他 `pending` 自动 `rejected` | `respond` |

- 【事实】`create` 对同一对已有 `pending`/`accepted` 时直接返回已有状态；已有 `rejected` 时检查冷却。
- 【事实】冷却中的 `create` 抛 `ValueError("对方已拒绝；N 小时后可重新发起。")`；页面会显示冷却提示，不会让用户误以为还能点。
- 【事实】到上限时抛 `ValueError("这件拾获已有 3 个待确认请求，请等待对方处理。")`。
- 【事实】`_is_matched` 同时检查拾获和失物：任一边已配对，拒绝新请求与接受。
- 【事实】接受时被自动关闭的其他请求也写 `request_history(rejected)`，冷却从关闭时刻起算。
- 【事实】撤销物品时 `cancel_for_item` 删除该物品相关的 `match_requests`、`matches` 与 `request_history`。

## 为什么 pending 不把物品移出候选池

- 【设计】有意不隐藏：如果第一个（可能是冒领的）请求就把拾获物品从其他人的候选里拿走，会形成“先到先得”的阻塞。
- 【设计】用**上限 3 个**控制骚扰，让拾获者在「我的记录」里比较多个请求再决定。
- 【事实】pending 不影响 `matches` 查询，所以物品仍在候选池；只有 `accepted` 写入 `matches` 后才移出。
- 【事实】接受后自动关闭其他 pending，避免同一拾获被重复接受；这也是“上限”不会留下悬空请求的原因。

## 页面行为

- 【事实】`interactive_match` 在「请求确认」里对当前选中的候选查询 `state()`：
  - `pending`：显示「已发送请求，等待对方确认」，按钮禁用；
  - `accepted`：显示「已经配对」，按钮禁用；
  - `rejected` 且冷却中：显示「对方已拒绝；N 小时后可重新发起」，按钮禁用；
  - `rejected` 且冷却结束：按钮变为「重新发送匹配请求」；
  - 无记录：按钮为「发送匹配请求」。
- 【事实】`state` 对新 pair 返回 `can_request=True`；对 pending/accepted 返回 False。
- 【事实】「我的记录 → 等待你确认的请求」显示待确认数量，并提示“接受其中一个后，其余会自动关闭”。
- 【事实】接受/拒绝失败时页面给出 warning（请求已处理/已配对）。
- 【事实】「我发出的请求」对 `rejected` 行显示冷却提示；冷却结束且物品未配对时出现「重新发送匹配请求」按钮。按钮会按物品归属推断方向，再调 `create`。
- 【事实】若对应物品已配对，页面显示「这条配对已经完成，不能重新发起」；若物品已撤销，显示对应提示。

## 隐私

- 【事实】`request_history` 只存 id、用户名、状态与时间；不存联系方式、拒绝理由或聊天内容。
- 【事实】联系方式仍然只在 `accepted` 后由 `MatchRequests.accepted()` 返回；pending/rejected 页面不 JOIN `users.email`。
- 【事实】`request_history` 只在冷却计算与审计中使用，没有对外展示页面；撤销物品会删除相关历史。

## 已知边界

- 冷却 24 小时、上限 3 个都是产品默认值，未用真实投诉/滥用数据校准。
- 自动关闭的请求在状态上仍是 `rejected`，没有单独的 `closed` 状态或原因；用户看到“已拒绝”可能不知道是别人先被接受。
- 拒绝/自动关闭不会主动通知请求者；他们下次打开「我的记录」才看到。
- 没有按用户/按天的请求速率限制；上限只按单件拾获计算。
- 可以接受自己另一件物品的请求？`create` 的 requester 检查只要求“发起者是报告所有者”，没有禁止同一用户同时拥有失物和拾获的极端情况；当前 UI 不提供这种路径。
- 接受一个请求后，其他被关闭请求的 `request_history` 冷却从关闭时刻起算；如果对方物品已被别人拿走，冷却结束后 `_is_matched` 会阻止重新发起。

## 测试

- `tests/test_requests.py`：方向换算、冷却、上限、接受自动关闭、已配对拒绝、无记录可发起。
- `tests/test_matching.py`：原有双方确认、拒绝、撤销清理。
- `tests/test_pages_smoke.py`：交互页发送、个人页接受、状态对话框。
- 2026-10-21 真实数据：键盘失物对键盘拾获发送 → 待确认（按钮禁用）；bob 拒绝 → alice 看到「冷却中：24 小时」；把历史 `ended_at` 提前后出现「重新发送匹配请求」，点击后回到 pending。

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：请求状态机、3 个上限、24 小时冷却、接受自动关闭、`request_history`、页面行为与边界。 |
