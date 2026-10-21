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
| `state/report.py` | 统一登记入口：`st.pills` 切换失物/拾获，调用内嵌的 `lost`/`found` | `report`、`MODES` |
| `state/lost.py` | 失物表单 → 文本向量 → 指纹 → 入库 → 建会话 | `lost`（`embedded`） |
| `state/found.py` | 上传 → 清洗 → BLIP 双语图注 → 确认读到的属性 → 登记前追问 → 表单 → 图像向量 → 指纹 → 入库 → 建会话 | `found`（`embedded`）、`_cached_analysis`、`_lost_pool` |
| `state/browse.py` | 浏览未配对拾获物品：关键词/类型/地点/时间筛选，只读，不展示联系方式 | `browse`、`filter_records`、`load_records` |
| `state/notifications.py` | 站内通知列表、未读标记、为已有失物重建匹配会话 | `notifications`、`_open_lost_match` |
| `state/interactive_match.py` | 展示指纹与 top 5、追问、重排、发请求 | `interactive_match` |
| `state/profile.py` | 我的失物/拾物、收到/发出/已确认的请求 | `profile` |
| `matching/models.py` | 懒加载 CLIP/BLIP；图像清洗与编码；文本+图像混合向量 | `_image_encoder`、`_text_encoder`、`_image_captioner`、`clean_image`、`combine_text_image` |
| `matching/vlm.py` | 可选的 DeepSeek 视觉识别：照片 → 描述 + 图上文字 | `describe_image`、`available` |
| `matching/fingerprint.py` | 文本 → 六维属性；生成式提案校验 | `fingerprint_from_text`、`extract_known` |
| `matching/workflow.py` | 取未匹配候选、CLIP 语义检索 top 8、惰性补指纹、组装会话 | `build_session` |
| `matching/engine.py` | 证据重排与信息增益追问 | `rank_candidates`、`choose_question` |
| `matching/storage.py` | `item_fingerprints` 表读写 | `FingerprintStore` |
| `matching/requests.py` | 配对请求状态机；pending 上限、拒绝冷却、接受自动关闭；写 `matches` 与 `request_history` | `MatchRequests`、`MAX_PENDING_PER_FOUND`、`REJECT_COOLDOWN_SECONDS` |
| `matching/notifications.py` | 订阅与通知表、拾获入库后的相关性判断、未读数 | `Notifications`、`notify_for_found_item` |
| `matching/lifecycle.py` | `item_status` 表：已归还/归档状态与恢复 | `Lifecycle`、`status_label` |
| `matching/report_meta.py` | `report_meta` 表：首次发布时间与公开/不公开 | `ReportMeta` |
| `matching/content_hash.py` | 内容指纹、图片 dHash、文本近似、展示水印 | `text_fingerprint`、`ImageHashes`、`watermark` |
| `db_manager.py` | `items`/`users`/`lost_items`/`found_items`/`matches` 访问 | `Database`、`Item`、`User` |

## 页面状态机

```text
state=login ──认证成功──> lost_or_found ──> report ──> lost / found（embedded）──build_session──> interactive_match
     │                        │                                                 │
     │                        ├──> browse（双向只读浏览，不建会话）             │
     │                        ├──> notifications ──查看候选──> interactive_match
     │                        └──> profile
     └─ register ──成功──> login
```

| state | 页面函数 | 前置条件 | 出口 |
| --- | --- | --- | --- |
| `login` | `login` | 无 | 认证成功 → `lost_or_found`；注册 → `register` |
| `register` | `register` | 无 | 成功 → `login` |
| `lost_or_found` | `lost_or_found` | 已认证（`app.py` 强制） | `lost` / `found` / `profile` |
| `report` | `report` | 已认证 | 切换方向；内嵌调用 `lost`/`found` |
| `lost` | `lost` | 已认证 | 成功建会话 → `interactive_match`；也可被 `report` 内嵌 |
| `found` | `found` | 已认证 | 成功建会话 → `interactive_match`；也可被 `report` 内嵌 |
| `browse` | `browse` | 已认证 | 只读浏览；可去 `lost` 登记失物 |
| `notifications` | `notifications` | 已认证 | 查看/标记通知；可重建某件失物的匹配会话 → `interactive_match` |
| `interactive_match` | `interactive_match` | 已认证 + `match_session.user` 等于当前用户 | 发请求；`profile` |
| `profile` | `profile` | 已认证 | 再报一件 → `lost_or_found`；可标记已归还/归档或恢复 |

- 【事实】`app.py` 的 `else` 分支把未知 state 归位到 `lost_or_found` 并 `st.rerun()`。
- 【事实】`state=login` 或无 `authentication_status` 时只会进登录页；**所有业务页都隐含"必须已登录"**。

## 会话里有什么（`st.session_state`）

| 键 | 类型 | 谁写 | 生命期 |
| --- | --- | --- | --- |
| `state` | `str` | 各页面按钮 | 浏览器会话 |
| `authentication_status` / `username` / `name` | 认证器写入 | `app.py::_restore_from_cookie`、`authenticator.login()` | 浏览器会话 |
| `user` | `User` | `state/login.py`、`app.py::_restore_from_cookie` | 浏览器会话 |
| `auth_cookie_pending` | `bool` | `state/login.py` | 只活一轮，`app.py` 消费后即删 |
| `match_session` | `dict` | `state/lost.py`、`state/found.py`、`state/notifications.py` | **仅当前 session**；刷新即丢 |
| `unread_notifications` | `int` | `app.py`（每轮重算）、`state/notifications.py`（标记已读后置 0） | 顶栏未读标签 |
| `report_mode` | `str` | `state/report.py`（`'lost'`/`'found'`） | 上次选择的方向 |
| `report_mode_pending` | `str` | 首页/feed/通知/我的记录入口 | 只活一轮；`report()` 消费后预选 pills |
| `duplicate_notice` | `str` | `state/lost.py`、`state/found.py` | 提交时命中文本近似；匹配页显示一次 |

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

1. `state/lost.py` 表单收描述、地点（`rooms.json`）、日期（近 30 天），以及**可选**照片（先 `clean_image`）。
2. `encode_text(description)` → 多语言 CLIP 文本向量；有照片时再 `encode_image`，用 `combine_text_image`（0.5/0.5）得到归一化混合向量。
3. `fingerprint_from_text(description)` → 属性 + `method`。
4. `Item(secrets.randbits(62), picture_or_none, vector, description, stamp, location)` → `items` + `lost_items`；照片存 `items.image`，向量存 `items.emb`。
5. `FingerprintStore().put(item.id, fingerprint)` → `item_fingerprints`。
6. `build_session(direction='lost', ..., query_time=stamp, query_location=location)`：取未匹配的拾获物品，跳过自己，惰性补指纹，`semantic_search` 取 top 8；候选带 `time/location`。
7. `session_state.match_session = session`，切到 `interactive_match`，`st.rerun()`。

- 【事实】`match_session` 还保存 `query_time`/`query_location`；`interactive_match` 把它们传给 `rank_candidates` 计算时间/地点软先验。
- 【事实】`build_session(..., include_matched=True)` 只用于 `evaluate.py`：评估全部对侧报告，而不只是未配对池。
- 【事实】报失/报拾获上传图片时，`ImageHashes.find_near()` 会提示近似重复；提交时 `find_similar_text()` 命中会把提示写进 `duplicate_notice`，由匹配页显示一次。
- 【事实】入库后 `ImageHashes.put()` 写 dHash；撤销时删除。dHash 不参与排序，只做查重提示。
- 【事实】近期动态/我的记录/通知/候选用 `watermark()` 显示带帖子尾号与日期的水印；入库图片与向量保持干净。

报拾获的差异：先 `clean_image` 再 `encode_image`；图注可被用户编辑后再提交；`fingerprint_from_text(description, caption=caption)` 让图注参与属性抽取；候选是未匹配的失物。

## 一次浏览的数据流

1. 首页「浏览近期动态」按钮或顶栏导航把 `state` 设为 `browse`。
2. `browse.py` 同时调用 `get_unmatched_lost_items()` 与 `get_unmatched_found_items()`；两个查询都已经排除 `matches` 与 `item_status`。
3. 逐件读 `item_fingerprints`；旧记录缺指纹时用 `fingerprint_from_text(..., generate=False)` 现算，不落库。
4. 逐件读 `report_meta`：`public=0` 的跳过；有 `published_at` 的用它排序和展示，旧数据回退到 `items.time` 并显示「旧数据未记录」。
5. `filter_records()` 在内存里按方向/关键词/类型/地点/时间过滤，按发布时间倒序；关键词同时匹配描述、地点、规范值与中文显示值。
6. 最多渲染 60 件，每件显示「失物/拾获」胶囊、描述、地点/日期、发布时间、属性胶囊；拾获还有照片。**不渲染任何用户名或邮箱**。
7. 页面底部只提供去 `report` 登记物品的两个入口，不在 feed 直接发请求。

- 【事实】浏览页不改变候选池，也不写数据库；它是只读页面。
- 【事实】已配对、已处理、设为不公开的物品不会出现在 feed。
- 【设计】时间/地点在这里只是筛选条件，不进入 `rank_candidates` 的排序分。

## 通知怎么产生

1. `state/lost.py` 在失物入库后，若表单勾选了「有新拾获时通知我」，写一条 `subscriptions(kind='lost_item')`。
2. `state/found.py` 在拾获物品、图像向量、指纹都落库后，调用 `notify_for_found_item()`。
3. 对每条失物订阅：跳过自己/已配对/缺向量的记录；用 `cosine` + `rank_candidates` 算出排序指标；≥ `0.40` 才写 `notifications`。
4. `app.py` 每轮用 `unread_count()` 刷新 `session_state.unread_notifications`，顶栏显示「通知 · N」。
5. 通知页的「查看这件失物的候选」会重新 `build_session(direction='lost')`，进入 `interactive_match`。

- 【事实】通知只在拾获登记时生成一次；已有拾获不会回溯触发。
- 【事实】通知不 JOIN `users`，因此不泄露拾获者身份或邮箱。
- 【设计】阈值与去重键见 [notifications](notifications.md)。

## 请求生命周期怎么生效

1. `state/interactive_match.py` 发请求前先查 `MatchRequests.state()`：pending/accepted 禁用按钮，rejected 冷却中禁用，冷却结束显示「重新发送匹配请求」。
2. `MatchRequests.create()` 拒绝同一拾获的第 4 个 pending；已配对物品直接拒绝；rejected 行冷却到期后删除并重建 pending。
3. `MatchRequests.respond()` 接受时写 `matches`，并把涉及该拾获/失物的其他 pending 自动改为 rejected；每条结束的请求写 `request_history`。
4. `state/profile.py` 的「等待你确认」提示会自动关闭其他请求；「我发出的请求」对 rejected 显示冷却或「重新发送匹配请求」。
5. 联系方式仍然只在 `accepted` 后由 `MatchRequests.accepted()` 返回。

- 【事实】pending 有意不把物品移出候选池；上限 3 用于控制骚扰。
- 【设计】细节与边界见 [request-lifecycle](request-lifecycle.md)。

## 已处理状态怎么生效

1. `state/profile.py` 的「处理」对话框写 `item_status(status='returned'|'archived')`，保留 `updated_by/updated_at/note`。
2. `Database.create_table()` 建立 `item_status`；`get_unmatched_lost_items()` / `get_unmatched_found_items()` 都 LEFT JOIN 它，状态非空即排除。
3. 因此已处理物品自动退出匹配候选、浏览页与通知生成；`interactive_match` 另有状态检查，防止旧会话继续展示候选。
4. 「我的记录」按 `Lifecycle.get()` 分成进行中与已处理；已处理区可「恢复为进行中」，删掉状态行即可回到池里。

- 【事实】撤销仍然是硬删除；状态是保留历史的另一种结束方式。
- 【事实】状态是单方标记，没有双方交接确认。
- 【设计】细节与边界见 [lifecycle](lifecycle.md)。

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
| 2026-10-21 | 新增 `state/browse.py`：只读浏览未配对拾获物品，支持关键词/类型/地点/时间筛选；补状态机与浏览数据流。 |
| 2026-10-21 | 新增订阅与站内通知：`matching/notifications.py`、`state/notifications.py`；补状态机、session 键与通知数据流。 |
| 2026-10-21 | 新增 `item_status` 与 `matching/lifecycle.py`：已归还/归档物品退出候选池，我的记录分流并可恢复。 |
| 2026-10-21 | 登记失物/拾获合并为 `state/report.py`；`state/browse.py` 扩成双向 feed，加入 `report_meta` 发布时间与公开开关。 |
| 2026-10-21 | 请求生命周期：pending 上限 3、拒绝 24 小时冷却、接受自动关闭其他请求；新增 `request_history` 与页面状态提示。 |
| 2026-10-22 | 会话带上 `query_time/query_location` 与候选 `time/location`；排序增加时间/地点软先验；新增 `evaluate.py`。 |
| 2026-10-22 | 失物支持可选照片：`items.image` 显示，`items.emb` 可存文本+图像混合向量；feed/记录/候选同步展示。 |
| 2026-10-22 | 发布时间/内容指纹置顶；新增 dHash 图片查重、文本近似提示、公开图水印；新增 `image_hashes`。 |
