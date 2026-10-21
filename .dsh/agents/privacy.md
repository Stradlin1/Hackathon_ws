# 隐私与双方确认（谁能看到什么）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[数据模型](data-model.md) 说明字段落点；[架构](architecture.md) 说明页面顺序。

**本文件状态：`【事实】`**——读自 `matching/requests.py`、`matching/models.py`、`state/*.py`（2026-10-21），另标了一条 `【设计】`。

## 保证清单

| 问题 | 保证 | 实现位置 |
| --- | --- | --- |
| 未确认配对的对方能看到邮箱吗？ | 不能；`incoming`/`outgoing` 只查描述与状态 | `MatchRequests.incoming`、`outgoing` |
| 浏览「最近拾获」能看到拾获者身份吗？ | 不能；只展示描述、已清洗照片、地点/日期与已共享属性 | `state/browse.py` |
| 站内通知能看到拾获者身份吗？ | 不能；通知只 JOIN `items`，展示描述/照片/地点/日期与排序指标 | `state/notifications.py` |
| 已归还/归档的备注别人能看到吗？ | 不能；`item_status.updated_by` 与 `note` 只在本人「我的记录」展示 | `state/profile.py` |
| 近期动态能看到失物描述吗？ | 默认能看到（可勾选不公开）；不展示发布者身份或联系方式 | `state/browse.py`、`state/lost.py`、`state/found.py` |
| 查重提示会泄露什么？ | 只给已有帖子的 id、相似度或图片距离；不含用户名、邮箱或联系方式 | `matching/content_hash.py` |
| 谁能发起请求？ | 只能由**自己那件报告**的所有者发起 | `MatchRequests.create` 的 `PermissionError` |
| 谁能接受/拒绝？ | 只有 `responder` 本人，且状态必须是 `pending` | `respond` 的 `WHERE responder=? AND status='pending'` |
| 邮箱何时出现？ | 只在 `status='accepted'` 的查询里 JOIN `users` | `MatchRequests.accepted` |
| 追问答案会入库吗？ | **会，但只存归一化后的属性值**（`item_fingerprints` 的 attributes + `confirmed` 列表），不存回答原文与问答历史；这些属性对匹配对象可见 | `matching/storage.py::merge`、`state/interactive_match.py` |
| 上传照片的 EXIF 会保留吗？ | 不会，存库前先 `clean_image` | `matching/models.py` |

## 请求状态机

```text
(无记录) --create（请求者=报告所有者）--> pending
pending --responder accept--> accepted  + matches(found, lost)
                                  └─ 其他涉及该拾获/失物的 pending 自动 rejected
pending --responder reject--> rejected + request_history
rejected --24 小时冷却结束 + create--> pending（旧行被替换，history 保留）
```

| 操作 | 前置条件 | 失败表现 |
| --- | --- | --- |
| `create` | direction ∈ {lost, found}；两件物品都有归属；`requester == username` | `ValueError` / `PermissionError` |
| `respond` | 调用者就是 `responder`；状态 `pending` | 返回 `False`（不抛异常） |
| 再次 `create` 同一对 | 主键已存在 → `INSERT OR IGNORE` | 返回**已有状态**（可能是 `rejected`） |

- 【事实】拒绝后进入 **24 小时冷却**；冷却到期可以重新发起（旧 `rejected` 行被替换，`request_history` 保留这次尝试）。
- 【事实】同一拾获最多 **3 个 pending**；接受一个后，涉及该拾获或该失物的其他 pending 自动改为 `rejected`。
- 【事实】`request_history` 只存物品 id、用户名、状态与时间；不存拒绝理由、联系方式或聊天内容；撤销物品会删除相关历史。
- 【设计】pending **不**把物品移出候选池，避免一个（可能是冒领的）请求阻塞其他人；用上限 3 控制骚扰，让拾获者比较后决定。
- 【事实】`accepted()` 返回 `contact_username`/`contact_email`，两人都能看到对方的联系方式。
- 【事实】`state/browse.py` 只调用 `get_unmatched_found_items()` 与 `FingerprintStore.get()`，不 JOIN `users`；页面没有用户名或邮箱字段。
- 【设计】浏览页把未配对拾获物品的描述与照片展示给所有已登录用户；这是有意的（失主不必先报失），联系方式仍受 `accepted` 门禁约束。
- 【事实】订阅只存 `username` 与失物 id（以及保留的搜索条件列），不存邮箱；通知只对订阅者本人可见。
- 【事实】站内通知不含拾获者用户名/邮箱，只含物品描述、照片、地点/日期、对应失物描述与排序指标。
- 【事实】登记失物时默认订阅，但只写本地表，不发送任何邮件或短信；用户可在「我的记录」里关闭。
- 【事实】撤销失物/拾获时，`Notifications.delete_for_item()` 会删除相关订阅与通知。
- 【事实】`item_status` 只存物品 id、状态、操作者用户名、时间与本人备注；备注不会进入候选、浏览页或通知。
- 【事实】已归还/归档不改变联系方式门禁：`MatchRequests.accepted()` 仍然是唯一出口。
- 【事实】与撤销不同，归还/归档保留 `items`、归属、指纹、请求与配对记录；撤销仍是硬删除。
- 【事实】「近期动态」默认展示所有已登录用户登记的失物与拾获：描述、拾获照片、地点/日期、发布时间、已共享属性；**不展示用户名、邮箱或联系方式**。
- 【事实】登记失物/拾获时都有「允许在近期动态中公开展示」复选框，默认勾选；取消后 `report_meta.public=0`，只退出 feed，仍参与匹配、订阅与通知。
- 【事实】发布时间来自 `report_meta.published_at`，只用于标明先后，不是所有权证明；`items.time` 是丢失/拾获日期，两者分开显示。
- 【设计】公开失物描述会放大“照抄描述冒领”的风险；当前没有认领验证，拾获者仍需自己判断是否接受请求。页面已提示不要写门牌号、证件号等敏感信息。
- 【事实】失物也可以上传可选照片；照片同样先 `clean_image` 去 EXIF，存 `items.db`，并可能随公开动态展示；不上传照片不影响匹配。
- 【设计】失物照片和拾获照片可能来自同一张图（例如从动态保存），会制造虚假的高相似度；这属于“照抄描述”的同类风险，仍要靠认领验证兜底。
- 【事实】内容指纹是规范化描述的 SHA-256 前 10 位，随帖子公开显示；它不包含用户名/邮箱。
- 【事实】`image_hashes` 只存 64-bit dHash 与时间，不存图片副本；撤销物品时删除。
- 【事实】查重提示只给帖子 id、文本相似度或图片 Hamming 距离，不 JOIN `users`；水印只写帖子尾号与日期。
- 【设计】发布时间/指纹/水印都是**公开信号**，不是不可篡改的证据；本地数据库有权限的人可以修改。
- 【设计】该表不记录拒绝理由，也不记录查看行为；没有审计日志。

## 本地凭据

- 【事实】认证读取 `config_auth.yaml`（根目录、与 `app.py` 同目录）；缺失时 `app.py` 直接 `st.error` + `st.stop()`。
- 【事实】`config_auth.example.yaml` 是模板，密码位要求 **bcrypt 哈希**，`cookie.key` 要求随机串（README 给出两条生成命令）。
- 【事实】`config_auth.yaml`、`.env*`、`*.pem/*.p12/*.pfx` 均被 `.gitignore` 排除；提交示例文件里的占位符不算泄露。
- 【事实】`users.password` 列在登录/注册时写入空字符串，真实口令只在配置文件里（bcrypt 哈希）。**不要**因为看到空串就往里写明文。
- 【事实】注册页是自建表单（`state/register.py`）：支持中文姓名、不要验证码；用户名 3–20 位、密码至少 8 位且含字母和数字，重复用户名/邮箱会被拒绝。
- 【事实】注册只改 `credentials.usernames` 再把整份配置写回，`cookie` 段原样保留：别人注册不会让已登录的会话失效，轮换 `cookie.key` 才会（见 [architecture](architecture.md)）。

## 第三方视觉模型（可选）

- 【事实】在 `settings.yaml` 里填 `deepseek.api_key`（或设环境变量 `DEEPSEEK_API_KEY`）后，拾获登记会把**照片副本**（JPEG base64）发送到 DeepSeek API 做一次识别；不填则全程不联网。`settings.yaml` 已 gitignore。
- 【事实】发送内容只有图片与一段固定提示词，不含用户名、邮箱、坐标或历史记录。
- 【设计】识别结果（描述、图上文字、属性）随指纹存进本机 `items.db`；API 侧是否留存由服务方政策决定，本地无法控制。
- 【事实】页面隐私说明会随开关变化：开启时写"照片会发送到 DeepSeek API 一次"，关闭时写"不联网"。
- 【待验证】DeepSeek API 的数据留存与训练使用条款未逐条核对；对外部署前必须核实。

## 图像卫生

- 【事实】`clean_image` 依次做：`ImageOps.exif_transpose`（按方向纠正）→ `thumbnail((1600,1600))` → `convert("RGB")` → 复制成新 `Image`。EXIF 不随新图保留。
- 【事实】`state/found.py` 另设 `Image.MAX_IMAGE_PIXELS = 20_000_000`，上传上限 8 MB，捕获 `DecompressionBombError`。
- 【事实】`tests/test_pages_smoke.py` 断言入库图片的 `getexif() == {}`。
- 【事实】照片以 BLOB 存 `items`，向量以 pickle 存 `emb`；`items.db` 被 `.gitignore` 排除。

## 追问答案

- 【事实】回答归一化成功后，`FingerprintStore.merge(item_id, {字段: 值})` 把它写进 `item_fingerprints` 的 attributes，并在 `confirmed` 里记下字段名；**原文与问答历史不落库**。
- 【事实】登记前追问的答案（`state/lost.py`、`state/found.py`）在入库前就直接并进指纹；追问页的答案在回答时写回。
- 【事实】合并后的属性会展示给匹配对象（候选卡片的属性胶囊），也会成为对方登记前追问的选项来源。这是有意为之：物品属性本来就该共享，共享的不是"谁回答了什么"。
- 【事实】`match_session.answers` 仍然只用于当前会话的排序；刷新后问答上下文消失，但已合并的属性留在库里。

## 撤销登记（删除）

- 【事实】只有登记人自己能在「我的记录」里撤销：`_remove_report` 先查 `lost_items`/`found_items` 的归属，不是本人直接 `PermissionError`。
- 【事实】删除是**硬删除**，没有软删除字段（不改既有表结构）：`items` 行、`lost_items`/`found_items` 归属、`item_fingerprints`、以及 `match_requests` 中引用它的行一并删除；`matches` 里的相关行也一并清掉。
- 【事实】已经有 `accepted` 配对的物品**不允许撤销**，弹窗只给提示；避免单方面抹掉双方已经交换的联系方式记录。
- 【事实】撤销是本地行为，没有"对方通知"；对方下次打开列表时请求已经消失。

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
| 刷新后追问没了 | 问答上下文不持久化，这是预期；已确认的属性仍在 `item_fingerprints` 里，可在「我的记录 → 补全信息」查看 |
| 图片带定位信息 | 是否绕过了 `clean_image`（只有 `state/found.py` 一处入口） |

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：保证清单、请求状态机、凭据、图像卫生、答案与信任边界。 |
| 2026-10-21 | 补浏览页保证：只展示描述/照片/地点/属性，不展示拾获者身份或联系方式。 |
| 2026-10-21 | 补订阅与通知：通知只给订阅者，不含身份/联系方式；只写本地表，不发邮件。 |
| 2026-10-21 | 补归还/归档：备注与操作者只给本人看；状态不改变联系方式门禁。 |
| 2026-10-21 | 补近期动态：失物/拾获描述默认公开、可关闭；发布时间只是先后标记；无身份/联系方式。 |
| 2026-10-21 | 补请求生命周期：拒绝 24 小时冷却、pending 上限 3、接受自动关闭其他请求；history 不含理由/联系方式。 |
| 2026-10-22 | 补失物照片：可选上传、去 EXIF、可能进入公开动态；同一张照片照抄风险仍在。 |
| 2026-10-22 | 补内容指纹/图片哈希/水印：只展示帖子 id、相似度与公开时间，不含身份/联系方式。 |
