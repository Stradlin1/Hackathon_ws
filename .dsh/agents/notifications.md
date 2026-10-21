# 订阅与站内通知

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[架构](architecture.md) 说明谁调用；[数据模型](data-model.md) 说明两张新表；[隐私](privacy.md) 说明通知里能看到什么；[匹配与追问](matching-engine.md) 提供排序公式。

**本文件状态：`【事实】`**——读自 `matching/notifications.py`、`state/notifications.py`、`state/lost.py`、`state/found.py`、`state/profile.py`（2026-10-21）。

## 解决什么问题

失物招领是异步事件：东西什么时候被捡到不确定，失主不会每天回来刷新。订阅把「有人捡到可能相关的物品」变成被动到达的站内通知，而不是要求失主反复登录。

## 订阅模型

- 【事实】订阅的单位是**一件已登记的失物**，不是关键词。
- 【事实】`subscriptions.kind` 目前只写 `lost_item`；表里保留了 `keyword/category/location` 列，但**没有保存搜索的 UI**。
- 【事实】登记失物时表单默认勾选「有新拾获时通知我」，提交后写一条订阅；「我的记录」里每件失物有「提醒我 / 取消提醒」按钮。
- 【事实】取消订阅只删 `subscriptions`，已经产生的通知保留。
- 【事实】撤销失物会调用 `Notifications.delete_for_item()`，连带删除它的订阅和通知；撤销拾获会删除指向它的通知。

## 通知怎么产生

入口是 `state/found.py` 在拾获物品入库、指纹落库之后调用：

```text
notify_for_found_item(found_item, fingerprint, db, store, owner)
```

对每条 `kind='lost_item'` 订阅：

1. 跳过订阅者就是拾获者本人的记录。
2. 跳过已删除、已有 `matches` 的失物。
3. 跳过缺失向量的失物（旧库兼容）。
4. 用 `cosine(found.emb, lost.emb)` 算语义分。
5. 用 `rank_candidates(lost_fp, [candidate])` 复用同一套证据公式，得到排序指标。
6. 指标 ≥ `NOTIFY_THRESHOLD = 0.40` 才写通知。

- 【事实】阈值是启发式排序门槛，**不是概率**；通知页写「排序指标 x.xxx · 不是所有权概率」。
- 【事实】通知只插入一次：`notifications` 的唯一键是 `(username, found_item_id, subscription_id)`，用 `INSERT OR IGNORE` 去重。
- 【设计】通知在登记请求内同步生成；订阅很多时会拖慢拾获登记，但实现简单，且演示规模很小。
- 【事实】通知不发送邮件、短信或推送；只在站内。

## 两张新表

| 表 | 关键列 | 说明 |
| --- | --- | --- |
| `subscriptions` | `id`, `username`, `kind`, `lost_item_id`, `keyword`, `category`, `location`, `created_at` | `UNIQUE(username, kind, lost_item_id, keyword, category, location)`；`lost_item_id=0` 保留给未来的保存搜索 |
| `notifications` | `id`, `username`, `found_item_id`, `lost_item_id`, `subscription_id`, `score`, `created_at`, `read_at` | `UNIQUE(username, found_item_id, subscription_id)`；`read_at IS NULL` 表示未读 |

- 【事实】两张表都由 `Notifications.__init__` 用 `CREATE TABLE IF NOT EXISTS` 建立，不改既有五张表（红线 6）。
- 【事实】`notifications` 的 `lost_item_id` 允许为空，为未来的搜索订阅留位；当前所有通知都有值。
- 【事实】没有外键；撤销物品时由应用层清理。

## 未读数与阅读状态

- 【事实】`app.py` 在每次运行、已认证时调用 `matching.notifications.unread_count(username)`，把结果写进 `st.session_state.unread_notifications`。
- 【事实】`ui.components.topbar()` 只读这个 session 键，不直接查库；有未读时导航标签变成 `通知 · N`。
- 【事实】通知页有「全部标为已读」和每条的「标为已读」；点「查看这件失物的候选」会先标记该条已读。
- 【事实】`read_at` 只写一次；`mark_read` 的 WHERE 带 `read_at IS NULL`。

## 通知页能做什么

- 【事实】展示拾获物品的描述、照片、地点/日期、排序指标，以及对应的失物描述。
- 【事实】「查看这件失物的候选」会校验失物归属、是否已配对、向量是否存在，然后调用 `build_session(direction='lost', ...)` 重建会话并进入 `interactive_match`。
- 【事实】「浏览最近拾获」跳到 `browse`。
- 【事实】**不展示拾获者用户名或邮箱**；联系方式仍然只在 `match_requests.status='accepted'` 后由 `MatchRequests.accepted()` 返回。

## 红线检查

1. 联系方式仍然只在 `accepted` 之后可见：通知页只 JOIN `items`，不 JOIN `users`。
2. 排序分仍叫「排序指标」，没有改称概率或置信度。
3. 只新增表，不改既有表；图片仍然先过 `clean_image`。
4. 通知里没有追问原文，只有物品描述与排序分。

## 已知边界

- 阈值 `0.40` 来自早期 4 对演示数据的观察，未用真实数据校准；演示集扩到 12 对后也未重新标定。
- 没有保存搜索（关键词/类型/地点）的 UI；表结构留了位，但 `notify_for_found_item` 只处理 `lost_item`。
- 没有邮件/短信/推送，也没有保留期或批量清理；通知会一直在本地库。
- 同一用户订阅多件相似失物时，同一件拾获可能产生多条通知；唯一键只保证「同一订阅 + 同一拾获」不重复。
- 通知在登记时生成一次；之后新增的订阅不会回溯已存在的拾获物品。

## 怎么改

- 改阈值：`matching/notifications.py::NOTIFY_THRESHOLD`；同步更新本文件与 `backlog.md` 的校准项。
- 改相关性：复用 `rank_candidates`，不要另写一套打分；否则会出现两套排序口径。
- 加保存搜索：实现 `subscriptions.kind='search'` 的写入与匹配分支，并在通知页加表单；仍不需要改既有表。
- 加邮件：在 `Notifications.add()` 成功后发送；失败不能影响登记。
- 改通知页：只展示物品级信息，禁止把 `users.email` JOIN 进来。

## 测试

- `tests/test_notifications.py`：订阅幂等、通知去重、未读/已读、全部已读、撤销清理、阈值上/下、已配对/自己/缺向量跳过。
- `tests/test_pages_smoke.py`：登记失物勾选后写订阅、通知页空态渲染。
- 2026-10-21 真实数据验证：键盘失物订阅后，用 bob 的键盘拾获触发通知，排序指标 0.50388；通知页未读数 1、无邮箱；点开候选 top-1 是键盘（0.504）。

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：订阅模型、通知生成、两张新表、未读数、通知页行为、红线与已知边界。 |
