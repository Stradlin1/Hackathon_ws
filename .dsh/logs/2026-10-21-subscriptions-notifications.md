# 2026-10-21 — 订阅与站内通知

## 目标

P0 第二项：失主不必反复回来刷新；新拾获物品入库后，如果和某件已订阅的失物足够相关，就在站内提醒失主。

## 决策

- **订阅单位是单件失物**，不是关键词。失主已经写过描述，订阅直接复用这件失物的向量与指纹，不需要再教用户怎么搜。
- **复用同一套排序**：`cosine(found.emb, lost.emb)` + `rank_candidates(lost_fp, [found])`，不另写一套“通知分数”。
- **阈值 0.40**：演示数据里正确配对约 0.48–0.52，错误候选约 0.24–0.39；0.40 是排序门槛，不是概率。
- **只新增两张表**：`subscriptions`、`notifications`，全部 `CREATE TABLE IF NOT EXISTS`，不改既有五张表。
- **通知不含身份**：只 JOIN `items`，展示描述/照片/地点/日期/排序指标；不 JOIN `users`，联系方式仍由 `accepted` 控制。
- **登记时默认订阅**：失物表单加一个默认勾选的复选框；「我的记录」里每件失物可以开关提醒。
- **通知页可以行动**：点「查看这件失物的候选」会校验归属/配对状态/向量，重建 `build_session(direction='lost')`，进入匹配页。
- **未读数由 `app.py` 每轮重算**：`topbar()` 只读 `session_state.unread_notifications`，不在展示组件里查库。
- **失败不阻断主流程**：订阅、通知生成、清理都用 try/except 包住；登记失物/拾获仍以物品入库为准。

## 改了什么

- 新增 `matching/notifications.py`：`Notifications`、`notify_for_found_item`、`unread_count`、`NOTIFY_THRESHOLD`。
- 新增 `state/notifications.py`：通知列表、未读标记、`_open_lost_match()`。
- `state/lost.py`：登记表单增加「有新拾获时通知我」；入库后写订阅。
- `state/found.py`：入库后调用 `notify_for_found_item()`。
- `state/profile.py`：失物卡片增加「提醒我 / 取消提醒」；撤销时清理订阅与通知。
- `app.py`：每轮刷新未读数；注册 `state='notifications'`。
- `ui/components.py`：顶栏增加「通知」，有未读时显示 `通知 · N`。
- `ui/icons.py`：新增 `bell` 图标。
- 测试：`tests/test_notifications.py`，以及 `test_pages_smoke.py` 的订阅/通知页烟测。
- 文档：新增 `.dsh/agents/notifications.md`，同步 architecture、data-model、privacy、ui、README、AGENTS、backlog、operations。

## 验证

- `pytest -q`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）→ **77 passed**。
- 真实数据（不是 mock）：
  - 订阅 alice 的键盘失物（`1362530411216040894`）。
  - 用 bob 的键盘拾获（`952798711189094561`）调用 `notify_for_found_item()`。
  - 生成 1 条通知，排序指标 **0.50388**，未读 1。
  - 登录 alice，顶栏标签为 **`通知 · 1`**；通知页包含键盘描述、「未读」「排序指标」，不包含 `example.invalid`。
  - 点「查看这件失物的候选」→ `state=interactive_match`，`match_session.item_id` 是键盘失物，top-1 是键盘拾获，分数 **0.504**。
  - 测试后把 `read_at` 置回 NULL，留一条未读通知给人工演示。
- `streamlit` HTTP 200（重启后）。

## 未做 / 留给后续

- 邮件、短信、微信推送；当前只有站内。
- 关键词/类型/地点的保存搜索（表结构留了列，没有 UI 与匹配分支）。
- 阈值校准：需要至少 20–50 对标注数据，不能继续用 4 对演示数据调参。
- 通知保留期/批量清理。
- 通知在登记请求内同步生成；订阅多时会拖慢拾获登记。
- 本机工作副本没有 `.git` 且未安装 git，因此没有按 `dsh` 分支提交；改动只存在于工作区。
