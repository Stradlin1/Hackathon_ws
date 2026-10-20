# 架构与页面流程（Streamlit 单机应用）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[匹配与追问](matching-engine.md)、[指纹](fingerprint.md)、[数据模型](data-model.md)、[隐私](privacy.md)。

**本文件状态：`【事实】`**——读自 `app.py` 与 `state/*.py`（2026-10-21），未做行为改动。

## 模块职责

| 模块 | 职责 | 关键符号 |
| --- | --- | --- |
| `app.py` | 读 `config_auth.yaml`、构造认证器、按 `st.session_state.state` 分发页面 | `st.set_page_config`、`authenticator`、末尾的 if/elif 链 |
| `state/login.py` | 登录；把登录用户写入 `users` 表 | `login`、`change_state` |
| `state/register.py` | 注册；把账号回写 `config_auth.yaml` 并插入 `users` | `register` |
| `state/lost_or_found.py` | 主菜单：报失 / 报拾获 / 我的记录 | `lost_or_found` |
| `state/lost.py` | 失物表单 → 文本向量 → 指纹 → 入库 → 建会话 | `lost` |
| `state/found.py` | 上传 → 清洗 → BLIP 图注 → 表单 → 图像向量 → 指纹 → 入库 → 建会话 | `found`、`_cached_caption` |
| `state/interactive_match.py` | 展示指纹与 top 5、追问、重排、发请求 | `interactive_match` |
| `state/profile.py` | 我的失物/拾物、收到/发出/已确认的请求 | `profile` |
| `matching/models.py` | 懒加载 CLIP/BLIP；图像清洗与编码 | `_image_encoder`、`_text_encoder`、`_image_captioner`、`clean_image` |
| `matching/fingerprint.py` | 文本 → 六维属性；生成式提案校验 | `fingerprint_from_text`、`extract_known` |
| `matching/workflow.py` | 取未匹配候选、CLIP 语义检索 top 8、惰性补指纹、组装会话 | `build_session` |
| `matching/engine.py` | 证据重排与信息增益追问 | `rank_candidates`、`choose_question` |
| `matching/storage.py` | `item_fingerprints` 表读写 | `FingerprintStore` |
| `matching/requests.py` | 配对请求状态机；接受时写 `matches` | `MatchRequests` |
| `db_manager.py` | `items`/`users`/`lost_items`/`found_items`/`matches` 访问 | `Database`、`Item`、`User` |

## 页面状态机

```text
state=login ──认证成功──> lost_or_found ──> lost / found ──build_session──> interactive_match
     │                                                                          │
     └─ register ──成功──> login                          profile <────────────┘
```

| state | 页面函数 | 前置条件 | 出口 |
| --- | --- | --- | --- |
| `login` | `login` | 无 | 认证成功 → `lost_or_found`；注册 → `register` |
| `register` | `register` | 无 | 成功 → `login` |
| `lost_or_found` | `lost_or_found` | 已认证（`app.py` 强制） | `lost` / `found` / `profile` |
| `lost` | `lost` | 已认证 | 成功建会话 → `interactive_match` |
| `found` | `found` | 已认证 | 成功建会话 → `interactive_match` |
| `interactive_match` | `interactive_match` | 已认证 + `match_session.user` 等于当前用户 | 发请求；`profile` |
| `profile` | `profile` | 已认证 | 再报一件 → `lost_or_found` |

- 【事实】`app.py` 的 `else` 分支把未知 state 归位到 `lost_or_found` 并 `st.rerun()`。
- 【事实】`state=login` 或无 `authentication_status` 时只会进登录页；**所有业务页都隐含"必须已登录"**。

## 会话里有什么（`st.session_state`）

| 键 | 类型 | 谁写 | 生命期 |
| --- | --- | --- | --- |
| `state` | `str` | 各页面按钮 | 浏览器会话 |
| `authentication_status` / `username` / `name` | 认证器写入 | `authenticator.login()` | 浏览器会话 |
| `user` | `User` | `state/login.py` | 浏览器会话 |
| `match_session` | `dict` | `state/lost.py`、`state/found.py` | **仅当前 session**；刷新即丢 |

- 【事实】`match_session` 的键：`direction`、`item_id`、`user`、`fingerprint`、`candidates`、`answers`、`asked`（`matching/workflow.py`）。
- 【设计】`answers` 刻意不落库（见 [privacy](privacy.md)）；代价是**刷新页面后追问结果全部丢失**，用户需要重新提交报告。

## 一次报失的数据流

1. `state/lost.py` 表单收描述、地点（`rooms.json`）、日期（近 30 天）。
2. `encode_text(description)` → 多语言 CLIP 文本向量。
3. `fingerprint_from_text(description)` → 属性 + `method`。
4. `Item(secrets.randbits(62), None, vector, description, stamp, location)` → `items` + `lost_items`。
5. `FingerprintStore().put(item.id, fingerprint)` → `item_fingerprints`。
6. `build_session(direction='lost', ...)`：取未匹配的拾获物品，跳过自己，惰性补指纹，`semantic_search` 取 top 8。
7. `session_state.match_session = session`，切到 `interactive_match`，`st.rerun()`。

报拾获的差异：先 `clean_image` 再 `encode_image`；图注可被用户编辑后再提交；`fingerprint_from_text(description, caption=caption)` 让图注参与属性抽取；候选是未匹配的失物。

## 实现约定（改代码时保持）

- **页面只做编排**：算法在 `matching/`，表访问在 `db_manager.py` 与 `matching/storage.py`、`matching/requests.py`。
- **数据库连接每页开、每页关**：`db = Database()` 之后必须 `try/finally: db.close()`。
- **模型懒加载**：`functools.lru_cache(maxsize=1)`，跨 rerun 复用；导入失败/权重不可用必须降级（图注失败 → 手填描述；文本生成器失败 → 规则抽取）。
- **错误展示**：页面把 `OSError/ValueError/RuntimeError/ImportError` 转成 `st.error` 或 `st.warning`，不向上抛。
- **没有 URL 路由**：导航全靠 `session_state.state` + `st.rerun()`。

## 测试如何覆盖这些流程

- 【事实】`tests/test_pages_smoke.py` 用假的 `streamlit` 模块（`UI`）和 `FakeDatabase` 直接调用页面函数，断言 `Rerun` 异常与 `session_state` 变化。
- 【事实】模型编码被 `monkeypatch` 替换成固定向量；`tests/test_matching.py` 则直接测引擎与存储。

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：模块职责、状态机、session 键、报失数据流、页面实现约定。 |
