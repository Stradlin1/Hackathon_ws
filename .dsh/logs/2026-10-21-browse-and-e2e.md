# 2026-10-21 — 新增「最近拾获」浏览页，并留下一次真实端到端证据

## 目标

补 P0 第一项：失主不必先报失，也能浏览尚未配对的拾获物品，并按关键词、类型、地点、时间筛选。

同时记录当天真实模型下的端到端演示，供评审追问时使用。

## 决策

- **只展示未配对的拾获物品**：直接复用 `Database.get_unmatched_found_items()`，已写入 `matches` 的物品不出现。这样不会出现“已经还给别人了还在列表里”的情况。
- **浏览页只读**：不写数据库、不建匹配会话、不发请求；只提供去「登记失物」的入口。发请求仍然必须经过报失 → 候选 → 发送请求的链路。
- **不展示任何身份信息**：不 JOIN `users`，不出现用户名/邮箱；联系方式仍然只在 `accepted` 之后可见。
- **筛选在内存里做**：关键词同时匹配描述、地点、规范值和中文显示值；类型选项来自指纹里的 `category`；时间按 `items.time` 计算；地点选项来自当前池。
- **不引入新表、不改既有表**：浏览是纯查询能力，没有 schema 变更。
- **最多渲染 60 件**：当前是演示规模；分页与性能留给 backlog。

## 改了什么

- 新增 `state/browse.py`：`browse`、`filter_records`、`load_records`、`category_options`、`location_options`。
- `app.py`：注册 `state == 'browse'` 分支。
- `ui/components.py`：顶栏增加「最近拾获」，从 4 个导航项变成 5 个；列宽相应调整。
- `state/lost_or_found.py`：首页增加「浏览最近拾获」按钮。
- `tests/test_browse.py`：筛选纯函数测试。
- `tests/test_pages_smoke.py`：浏览页空池与有卡片两种烟测。
- 文档：`README.md`、`AGENTS.md`、`.dsh/agents/architecture.md`、`ui.md`、`privacy.md`、`backlog.md`。

## 验证

- `pytest -q`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）→ **69 passed**。
- 真实 `items.db` 上用 AppTest 跑浏览页：
  - 4 件拾获中 1 件（鼠标）已配对，浏览页只剩 3 件，符合“只显示未配对”；
  - 关键词「杯子」→ 1 件；类型「键盘」→ 1 件；地点「图书馆」→ 1 件；时间「最近 24 小时」→ 3 件；
  - 页面文本中不出现 `example.invalid`；
  - 关键词「鼠标」在鼠标已配对后返回空状态文案。
- `streamlit run app.py` → HTTP 200。

## 当天真实端到端（DeepSeek + CLIP）

- 失物「浅绿色椭圆形无线鼠标，塑料外壳，滚轮下方有电量显示」→ 指纹 `mouse/green/plastic/oval`，top-1 正是 bob 的鼠标，分数 0.482（CLIP 0.280），类型/颜色/材质/形状全一致。
- 发送请求 → `pending`；bob 在「我的记录」接受 → `accepted`，双方看到对方邮箱，`matches(found, lost)` 写入。
- 更模糊的「浅绿色无线鼠标」只抽出 `mouse/green`，系统追问「形状」；回答「椭圆形」后水杯分数从 0.319 升到 0.359（`oval` 与 `cylindrical` 同属 `roundish`）。
- 拾获侧用 `demo/photos/水杯.jpg`：DeepSeek 描述为「绿色盖子的透明圆柱形水瓶…FUGUANG」，指纹 `water bottle/green/cylindrical/fuguang`，top-1 是 alice 的水杯，分数 0.515（CLIP 0.326）；`cup`/`water bottle` 同族避免了类型矛盾。

## 未做 / 留给后续

- 浏览页分页与性能。
- 浏览页直接“这可能是我丢的”预填失物描述：有意不做，避免失主照抄拾获者描述，破坏证据独立性。
- BLIP 离线路径未验证（本机跳过了 BLIP/opus-mt，用 DeepSeek）。
- 本机工作副本没有 `.git` 且未安装 git，因此没有按 `dsh` 分支提交；改动只存在于工作区。
