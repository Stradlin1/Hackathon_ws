# 数据模型（SQLite `items.db` 与两张扩展表）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[架构](architecture.md) 说明谁在写；[隐私](privacy.md) 说明哪些字段不能外泄。

**本文件状态：`【事实】`**——表结构读自 `db_manager.py`、`matching/storage.py`、`matching/requests.py`。

## 表

| 表 | 列 | 写入方 | 用途 |
| --- | --- | --- | --- |
| `items` | `id` PK, `image` BLOB, `emb` BLOB, `description` TEXT, `time` INTEGER, `location` TEXT | `Database.insert_item` | 物品主表；`image`/`emb` 是 **Python pickle** 的 ndarray |
| `users` | `username` PK, `password` TEXT, `email` TEXT | `insert_user`（登录/注册） | 认证由 `config_auth.yaml` 负责；`password` 实际总是空串 |
| `lost_items` | `item_id`, `user_id`, PK(item_id,user_id) | `insert_lost_item` | 失物归属（多对多形状，实际一人一件） |
| `found_items` | 同上 | `insert_found_item` | 拾获归属 |
| `matches` | `item1_id`, `item2_id`, PK(item1,item2) | `insert_match`、`MatchRequests.respond` | 已确认配对 |
| `item_fingerprints` | `item_id` PK, `fingerprint_json` TEXT | `FingerprintStore.put` | `{"attributes": ..., "method": ..., "caption": ...}` 的 JSON |
| `match_requests` | `found_item_id`, `lost_item_id`, `requester`, `responder`, `status`, `created_at`, PK(found,lost) | `MatchRequests` | 双方确认状态机 |

- 【事实】前五张表由 `Database.create_table()` 用 `CREATE TABLE IF NOT EXISTS` 建立；后两张由各自的类在构造时建立。
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
- 【事实】`match_requests.created_at` 是 `int(time.time())`。

## 连接与生命周期

- 【事实】`Database.__init__` 直接连接字符串 `'items.db'`，**相对进程工作目录**。从别的目录启动会静默创建/使用另一个空库。
- 【事实】没有连接池、没有 WAL、没有 busy timeout；每页 `Database()` 开、`close()` 关，指纹与请求类则每次操作新开短连接。
- 【待验证】多浏览器会话同时写入时是否会出现 `database is locked`——未实测，演示前建议单用户操作。
- 【事实】`get_item(id)` 在 id 不存在时对 `None` 取下标，抛 `TypeError`（见 backlog）。

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
