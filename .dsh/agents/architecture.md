# 架构与页面流程（Streamlit 单机应用）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[匹配与追问](matching-engine.md)、[指纹](fingerprint.md)、[数据模型](data-model.md)、[隐私](privacy.md)。

**本文件状态：`【事实】`**——读自 `app.py` 与 `state/*.py`（2026-10-21），未做行为改动。

## 模块职责

| 模块 | 职责 | 关键符号 |
| --- | --- | --- |
| `app.py` | 读 `config_auth.yaml`、构造认证器、按 `st.session_state.state` 分发页面 | `st.set_page_config`、`authenticator`、末尾的 if/elif 链 |
| `state/login.py` | 登录表单与账号记忆 | `login` |
| `ui/theme.py` | 设计令牌、全局 CSS 与注入 | `inject`、`CSS` |
| `ui/components.py` | 顶栏、页头、卡片、统计、空状态、徽标 | `topbar`、`page_header`、`card`、`stat_row` |
| `ui/icons.py` | 内联 SVG 图标（不用 emoji） | `icon` |
| `state/register.py` | 自建注册表单；校验后 bcrypt 哈希写入 `config_auth.yaml`，并尽力插入 `users` | `register`、`validate_registration` |
| `state/lost_or_found.py` | 主菜单：报失 / 报拾获 / 我的记录 | `lost_or_found` |
| `state/lost.py` | 失物表单 → 文本向量 → 指纹 → 入库 → 建会话 | `lost` |
| `state/found.py` | 上传 → 清洗 → BLIP 双语图注 → 确认读到的属性 → 登记前追问 → 表单 → 图像向量 → 指纹 → 入库 → 建会话 | `found`、`_cached_caption`、`_lost_pool` |
| `state/interactive_match.py` | 展示指纹与 top 5、追问、重排、发请求 | `interactive_match` |
| `state/profile.py` | 我的失物/拾物、收到/发出/已确认的请求 | `profile` |
| `matching/models.py` | 懒加载 CLIP/BLIP；图像清洗与编码 | `_image_encoder`、`_text_encoder`、`_image_captioner`、`clean_image` |
| `matching/vlm.py` | 可选的 DeepSeek 视觉识别：照片 → 描述 + 图上文字 | `describe_image`、`available` |
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
| `authentication_status` / `username` / `name` | 认证器写入 | `app.py::_restore_from_cookie`、`authenticator.login()` | 浏览器会话 |
| `user` | `User` | `state/login.py`、`app.py::_restore_from_cookie` | 浏览器会话 |
| `auth_cookie_pending` | `bool` | `state/login.py` | 只活一轮，`app.py` 消费后即删 |
| `match_session` | `dict` | `state/lost.py`、`state/found.py` | **仅当前 session**；刷新即丢 |

- 【事实】`match_session` 的键：`direction`、`item_id`、`user`、`fingerprint`、`candidates`、`answers`、`asked`（`matching/workflow.py`）。
- 【设计】`answers` 刻意不落库（见 [privacy](privacy.md)）；代价是**刷新页面后追问结果全部丢失**，用户需要重新提交报告。

## 登录状态怎么跨刷新

- 【事实】登录状态 = 浏览器里的一个 cookie：`config_auth.yaml` 的 `cookie.name`/`key`/`expiry_days`（默认 7 天）决定名字、签名密钥与有效期；内容是 HS256 JWT `{"username", "exp_date"}`，由 `streamlit-authenticator` 生成。
- 【事实】刷新会新建 Streamlit session（`st.session_state` 清空），但请求头里仍带 cookie；`app.py::_restore_from_cookie` 在 `st.context.cookies` 里读它、校验签名与过期时间，再调 `authenticator.authentication_controller.login(token=...)` 还原会话。所以刷新后第一帧就是业务页，不会先闪一下登录框。
- 【事实】登录成功的那一轮以 `st.rerun()` 结束，而 Streamlit 会丢弃「被 rerun 中断的那一轮」渲染出的元素，认证库自己写的 cookie 组件因此到不了浏览器（`tests/` 测不到，只有真浏览器能复现）。所以 `state/login.py` 只置 `auth_cookie_pending`，由 `app.py` 在下一轮补写。
- 【事实】退出登录会删 cookie 并把 `logout` 置 `True`；`_restore_from_cookie` 见到 `logout` 直接返回，避免用同一 session 里残留的旧 cookie 又登回去。
- 【事实】刷新只恢复「已登录」，不恢复页面位置：`state` 回到 `login`，已认证时直接改判为 `lost_or_found`。
- 【事实】已登录页面统一由 `ui.components.topbar` 渲染顶部导航（品牌 / 四个页面按钮 / 退出登录），`st.sidebar` 已全站移除；退出登录仍走 `authenticator.logout(location="main")`，删 cookie 的组件照常送达。
- 【待验证】cookie 只对当前 host 生效；换 `localhost`/`127.0.0.1` 或换端口都会被当成新站点，需要重新登录。

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
| 2026-10-21 | 补「登录状态怎么跨刷新」：cookie 内容、恢复路径、延迟写 cookie 的原因与 logout 防护。 |
