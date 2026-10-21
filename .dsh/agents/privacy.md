# 隐私与双方确认（谁能看到什么）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[数据模型](data-model.md) 说明字段落点；[架构](architecture.md) 说明页面顺序。

**本文件状态：`【事实】`**——读自 `matching/requests.py`、`matching/models.py`、`state/*.py`（2026-10-21），另标了一条 `【设计】`。

## 保证清单

| 问题 | 保证 | 实现位置 |
| --- | --- | --- |
| 未确认配对的对方能看到邮箱吗？ | 不能；`incoming`/`outgoing` 只查描述与状态 | `MatchRequests.incoming`、`outgoing` |
| 谁能发起请求？ | 只能由**自己那件报告**的所有者发起 | `MatchRequests.create` 的 `PermissionError` |
| 谁能接受/拒绝？ | 只有 `responder` 本人，且状态必须是 `pending` | `respond` 的 `WHERE responder=? AND status='pending'` |
| 邮箱何时出现？ | 只在 `status='accepted'` 的查询里 JOIN `users` | `MatchRequests.accepted` |
| 追问答案会入库吗？ | 不会，只在 `st.session_state.match_session` | `matching/workflow.py` 文档字符串、`state/interactive_match.py` |
| 上传照片的 EXIF 会保留吗？ | 不会，存库前先 `clean_image` | `matching/models.py` |

## 请求状态机

```text
(无记录) --create（请求者=报告所有者）--> pending
pending --responder accept--> accepted  ──同时 INSERT OR IGNORE matches(found, lost)
pending --responder reject--> rejected
```

| 操作 | 前置条件 | 失败表现 |
| --- | --- | --- |
| `create` | direction ∈ {lost, found}；两件物品都有归属；`requester == username` | `ValueError` / `PermissionError` |
| `respond` | 调用者就是 `responder`；状态 `pending` | 返回 `False`（不抛异常） |
| 再次 `create` 同一对 | 主键已存在 → `INSERT OR IGNORE` | 返回**已有状态**（可能是 `rejected`） |

- 【事实】`match_requests` 主键是 `(found_item_id, lost_item_id)`，所以**一次拒绝就是终局**：没有把 `rejected` 改回 `pending` 的路径（见 `backlog.md`）。
- 【事实】`accepted()` 返回 `contact_username`/`contact_email`，两人都能看到对方的联系方式。
- 【设计】该表不记录拒绝理由，也不记录查看行为；没有审计日志。

## 本地凭据

- 【事实】认证读取 `config_auth.yaml`（根目录、与 `app.py` 同目录）；缺失时 `app.py` 直接 `st.error` + `st.stop()`。
- 【事实】`config_auth.example.yaml` 是模板，密码位要求 **bcrypt 哈希**，`cookie.key` 要求随机串（README 给出两条生成命令）。
- 【事实】`config_auth.yaml`、`.env*`、`*.pem/*.p12/*.pfx` 均被 `.gitignore` 排除；提交示例文件里的占位符不算泄露。
- 【事实】`users.password` 列在登录/注册时写入空字符串，真实口令只在配置文件里（bcrypt 哈希）。**不要**因为看到空串就往里写明文。
- 【事实】注册页是自建表单（`state/register.py`）：支持中文姓名、不要验证码；用户名 3–20 位、密码至少 8 位且含字母和数字，重复用户名/邮箱会被拒绝。
- 【事实】注册只改 `credentials.usernames` 再把整份配置写回，`cookie` 段原样保留：别人注册不会让已登录的会话失效，轮换 `cookie.key` 才会（见 [architecture](architecture.md)）。

## 图像卫生

- 【事实】`clean_image` 依次做：`ImageOps.exif_transpose`（按方向纠正）→ `thumbnail((1600,1600))` → `convert("RGB")` → 复制成新 `Image`。EXIF 不随新图保留。
- 【事实】`state/found.py` 另设 `Image.MAX_IMAGE_PIXELS = 20_000_000`，上传上限 8 MB，捕获 `DecompressionBombError`。
- 【事实】`tests/test_pages_smoke.py` 断言入库图片的 `getexif() == {}`。
- 【事实】照片以 BLOB 存 `items`，向量以 pickle 存 `emb`；`items.db` 被 `.gitignore` 排除。

## 追问答案

- 【事实】`build_session` 的会话字典含 `answers`/`asked`，但**没有任何写库调用**；`FingerprintStore` 只存初始指纹。
- 【事实】刷新页面丢失 `match_session`，追问历史一并消失；这是隐私与实现的共同结果，不是 bug。
- 【事实】`interactive_match` 底部会把 `answers` 以中文属性名展示给当前用户看（`st.caption(f'已提问 ... 回答：{answers_text}')`），这是本人可见，不是跨用户泄露。

## 数据落盘与信任边界

- 【事实】所有数据都在本地 `items.db`；没有服务端同步、没有加密。
- 【事实】`image`/`emb` 用 pickle，README 明确「treat as trusted local data, not an untrusted exchange format」。
- 【事实】没有速率限制、没有邮箱验证、没有封禁机制；注册即写入本地配置。
- 【待验证】多用户同时在线时，`accepted()` 之前的描述是否可能通过候选页泄露过细信息——目前候选页只显示描述与图片，属于设计如此（物品描述本就是拾获者提供）。

## 排查表

| 症状 | 先查 |
| --- | --- |
| 页面能看到对方邮箱但状态不是 accepted | `grep -rn "contact_email" matching/requests.py`，确认没有第二处查询 |
| 自己能给别人报告发请求 | `MatchRequests.create` 的 `requester != username` 分支是否被绕过 |
| 刷新后追问没了 | 预期行为；`match_session` 不持久化 |
| 图片带定位信息 | 是否绕过了 `clean_image`（只有 `state/found.py` 一处入口） |

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：保证清单、请求状态机、凭据、图像卫生、答案与信任边界。 |
