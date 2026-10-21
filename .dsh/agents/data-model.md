# 数据模型（SQLite `items.db` 与两张扩展表）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[架构](architecture.md) 说明谁在写；[隐私](privacy.md) 说明哪些字段不能外泄。

**本文件状态：`【事实】`**——表结构读自 `db_manager.py`、`matching/storage.py`、`matching/requests.py`。

## 表

| 表 | 列 | 写入方 | 用途 |
| --- | --- | --- | --- |
| `items` | `id` PK, `image` BLOB, `emb` BLOB, `description` TEXT, `time` INTEGER, `location` TEXT | `Database.insert_item` | 物品主表；`image`/`emb` 是 **Python pickle** 的 ndarray（失物的 `image` 现在也可有值，`emb` 可为文本或文本+图像混合向量） |
| `users` | `username` PK, `password` TEXT, `email` TEXT | `insert_user`（登录/注册） | 认证由 `config_auth.yaml` 负责；`password` 实际总是空串 |
| `lost_items` | `item_id`, `user_id`, PK(item_id,user_id) | `insert_lost_item` | 失物归属（多对多形状，实际一人一件） |
| `found_items` | 同上 | `insert_found_item` | 拾获归属 |
| `matches` | `item1_id`, `item2_id`, PK(item1,item2) | `insert_match`、`MatchRequests.respond` | 已确认配对 |
| `item_status` | `item_id` PK, `status`, `updated_by`, `updated_at`, `note` | `Lifecycle.set_status` | 已归还/归档；无行=进行中 |
| `item_fingerprints` | `item_id` PK, `fingerprint_json` TEXT | `FingerprintStore.put` | `{"attributes": ..., "method": ..., "caption": ...}` 的 JSON |
| `match_requests` | `found_item_id`, `lost_item_id`, `requester`, `responder`, `status`, `created_at`, PK(found,lost) | `MatchRequests` | 双方确认状态机；状态仍只有 pending/accepted/rejected |
| `request_history` | `id`, `found_item_id`, `lost_item_id`, `requester`, `responder`, `status`, `created_at`, `ended_at` | `MatchRequests` | 已结束的请求尝试；冷却与审计 |
| `subscriptions` | `id`, `username`, `kind`, `lost_item_id`, `keyword`, `category`, `location`, `created_at` | `Notifications` | 失物订阅；当前只有 `kind='lost_item'` |
| `notifications` | `id`, `username`, `found_item_id`, `lost_item_id`, `subscription_id`, `score`, `created_at`, `read_at` | `Notifications` | 站内通知；`read_at IS NULL` 为未读 |
| `report_meta` | `item_id` PK, `published_at`, `public` | `ReportMeta` | 首次发布时间与公开/不公开 |
| `image_hashes` | `item_id` PK, `dhash`, `created_at` | `ImageHashes` | 图片 64-bit dHash；查重提示 |

- 【事实】前六张表由 `Database.create_table()` 用 `CREATE TABLE IF NOT EXISTS` 建立（含 `item_status`，因为未匹配查询要 JOIN 它）；后七张由各自的类在构造时建立。
- 【事实】**没有外键约束**（SQLite 默认关闭），`remove_item` 只删 `items`，会留下归属行；读取时的 JOIN 让这些行自然消失。

## 方向约定（最容易写反的地方）

- 【事实】`matches.item1_id = 拾获物品`，`item2_id = 失物`。依据：`MatchRequests.respond` 接受时写 `(found, lost)`；`reset_db.py` 写 `insert_match(found.id, lost.id)`。
- 【事实】未匹配查询依赖这个方向：
  - 失物候选 = `found_items LEFT JOIN matches m ON fi.item_id = m.item1_id WHERE m.item1_id IS NULL`
  - 拾获候选 = `lost_items LEFT JOIN matches m ON li.item_id = m.item2_id WHERE m.item2_id IS NULL`
- 【事实】写反方向的后果是：已配对的物品仍会出现在候选里，且没有任何报错。改任何写 `matches` 的代码前先回来看这一节。

## 标识与时间

- 【事实】新物品 id 用 `secrets.randbits(62)`（`state/lost.py`、`state/found.py`）；样例数据用 10–13。
- 【事实】`items.time` 是 **epoch 秒**，取所选日期的本地零点（`datetime.combine(date, datetime.min.time()).timestamp()`）。`state/profile.py` 直接打印这个整数，没有格式化。
- 【事实】`items.time` / `items.location` 现在参与 `rank_candidates` 的时间/地点软先验（同地点 +0.02、时间接近最多 +0.03）；缺失或“未知/其他”为 0，不扣分。
- 【事实】失物照片存 `items.image`；有照片时 `items.emb` 是 `normalize(0.5×text + 0.5×image)`，没有照片时是纯文本向量。没有新增表/列。
- 【事实】`match_requests.created_at` 是 `int(time.time())`。

## 连接与生命周期

- 【事实】`Database.__init__` 直接连接字符串 `'items.db'`，**相对进程工作目录**。从别的目录启动会静默创建/使用另一个空库。
- 【事实】没有连接池、没有 WAL、没有 busy timeout；每页 `Database()` 开、`close()` 关，指纹与请求类则每次操作新开短连接。
- 【待验证】多浏览器会话同时写入时是否会出现 `database is locked`——未实测，演示前建议单用户操作。
- 【事实】`get_item(id)` 在 id 不存在时对 `None` 取下标，抛 `TypeError`（见 backlog）。

## 删除（撤销登记）

- 【事实】撤销走 `state/profile.py::_remove_report`：先验归属，再删 `lost_items`/`found_items`、`items`、`item_fingerprints`，最后 `MatchRequests.cancel_for_item` 清掉 `match_requests` 与 `matches` 里的相关行。
- 【事实】没有软删除。既有表不加列（红线 7），所以撤销就是真删；已 `accepted` 的物品拒绝撤销，避免单方面抹掉双方的配对记录。
- 【事实】删除后如果当前 `match_session.item_id` 指向它，session 会被清空。

## 归还/归档（非破坏性）

- 【事实】`item_status` 的 `status` 只允许 `returned`/`archived`；没有行表示进行中。
- 【事实】`Database.get_unmatched_lost_items()` 与 `get_unmatched_found_items()` 都 LEFT JOIN `item_status`，并要求 `st.item_id IS NULL`；已处理物品因此退出候选池与浏览页。
- 【事实】`Lifecycle.set_status()` 用 upsert 覆盖状态；`Lifecycle.clear()` 恢复为进行中。
- 【事实】`updated_by`/`note` 只给本人看；不进入候选、浏览页或通知。
- 【设计】与撤销的区别：撤销是硬删除；状态保留 `items`、归属、指纹、请求与配对记录。

## 订阅与通知

- 【事实】`subscriptions` 的唯一键是 `(username, kind, lost_item_id, keyword, category, location)`；`kind='lost_item'` 时 `lost_item_id` 是失物 id，`keyword/category/location` 为空串。
- 【事实】`notifications` 的唯一键是 `(username, found_item_id, subscription_id)`；同一订阅对同一拾获最多一条。
- 【事实】`notifications.lost_item_id` 允许为空，为未来的保存搜索保留；当前写入时都有值。
- 【事实】`notifications.score` 是 `rank_candidates` 的排序指标，**不是概率**。
- 【事实】撤销物品时 `state/profile.py::_remove_report` 调 `Notifications.delete_for_item()`：删掉指向该物品的通知与以它为失物的订阅。
- 【事实】通知生成只读 `items`、`subscriptions`，不 JOIN `users`；联系方式仍由 `MatchRequests.accepted()` 控制。
- 【设计】没有外键；删除靠应用层清理。两张表都不修改既有五张表的列。

## 请求历史与冷却

- 【事实】`request_history` 记录每次结束的请求尝试（accepted/rejected），列包括双方 id、请求人/响应人、开始与结束时间。
- 【事实】`match_requests` 的列与状态值没有改；拒绝行仍保留为 `rejected`，冷却到期后 `create` 删除它并重新插入 `pending`。
- 【事实】冷却 24 小时、同一拾获最多 3 个 pending；常量在 `matching/requests.py`。
- 【事实】接受一个请求时，涉及该拾获或该失物的其他 pending 自动改为 `rejected`，并写 `request_history`。
- 【事实】撤销物品的 `cancel_for_item` 同时删除该物品相关的 `match_requests`、`matches` 与 `request_history`。
- 【设计】没有新增状态值，避免修改 `match_requests` 的 CHECK 约束与旧库迁移。

## 发布时间与公开可见性

- 【事实】`report_meta.item_id` 是主键；`published_at` 是首次登记时刻（epoch 秒），`public` 是 0/1。
- 【事实】`ReportMeta.publish()` 用 upsert：首次插入 `published_at`，后续只改 `public`，不改首次发布时间。
- 【事实】没有 `report_meta` 行的旧数据按公开处理；feed 的发布时间显示「旧数据未记录」。
- 【事实】`items.time` 是丢失/拾获日期，**不是**发布时间；两者分别展示。
- 【事实】`public=0` 只影响「近期动态」；匹配、订阅、通知仍然可以使用这条报告。
- 【设计】`report_meta` 是独立新表，不修改 `items`，避免给旧库补列的迁移问题。

## 内容指纹与图片哈希

- 【事实】`image_hashes` 只存 64-bit dHash 与时间，不存图片副本；撤销物品时 `ImageHashes.delete()` 删除对应行。
- 【事实】登记失物/拾获时写哈希；`seed_demo.py` 会为 4 张拾获照片写哈希。
- 【事实】上传预览用 `find_near()` 比较 Hamming 距离 ≤ 6 的已有图片，只提示不阻断。
- 【事实】内容指纹（`text_fingerprint`）不落库，显示时由规范化描述计算 SHA-256 前 10 位；描述改变则指纹改变。
- 【设计】`image_hashes` 是独立新表，不修改既有表；查重阈值是启发式，不作为所有权证据。

## 兼容与演进规则

- 【事实】仓库没有任何迁移脚本；`CREATE TABLE IF NOT EXISTS` 是唯一的建表手段。
- 【设计】**不改既有五张表的列定义**：旧 `items.db` 可能已经在用户机器上。新能力用新表（如 `item_fingerprints`、`match_requests` 就是这么加的）。
- 【事实】旧行可能没有 `emb`：`build_session` 对失物候选在缺少向量时用 `encode_image(item.image)`，对拾获候选用 `encode_text(item.description)` 现场补算；没有指纹时用 `fingerprint_from_text(description, generate=False)` 生成并落库。
- 【设计】如果确实需要给旧表加列，必须同时写迁移与回滚说明，不能只改 `CREATE TABLE`——对已有库它不会生效。

## 数据格式风险

- 【事实】`image` 与 `emb` 是 pickle。README 明确把它当作**可信本地数据**，不是交换格式；读取不可信来源的 `items.db` 等于执行任意代码。
- 【事实】`items.db` 被 `.gitignore` 的 `*.db` 排除；`uploads/`、`private_data/` 同样排除。

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：七张表、方向约定、id/time、连接生命周期、演进与 pickle 风险。 |
| 2026-10-21 | 新增 `subscriptions` 与 `notifications` 两张表：唯一键、未读语义、撤销清理与联系方式边界。 |
| 2026-10-21 | 新增 `item_status`：归还/归档状态、候选池 JOIN 过滤、与撤销的区别。 |
| 2026-10-21 | 新增 `report_meta`：首次发布时间、公开/不公开；`items.time` 与发布时间分开。 |
| 2026-10-21 | 新增 `request_history`：拒绝冷却、接受自动关闭与审计；`match_requests` 列/状态不变。 |
| 2026-10-22 | 没有 schema 变更；`items.time/location` 开始提供排序软先验。 |
| 2026-10-22 | 没有 schema 变更；失物可复用 `items.image`，`items.emb` 可为文本+图像混合向量。 |
| 2026-10-22 | 新增 `image_hashes`：图片 dHash、查重提示；不存图片副本，撤销时删除。 |
