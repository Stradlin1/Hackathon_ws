# 2026-10-21 — 统一登记入口 + 双向近期动态

## 目标

用户在试用后指出：「登记失物」和「登记拾获」是重复入口，可以合并成「登记物品」；「最近拾获」可以扩成「近期丢失/拾获」，把所有人的失物与拾获都公开。默认公开，但允许勾选不公开，并显示发布时间。

## 决策

- **合并入口**：顶栏从 6 项降到 5 项（首页 / 登记物品 / 近期动态 / 通知 / 我的记录）。`state/report.py` 用 `st.pills` 切换方向，调用 `lost()` / `found(..., embedded=True)`，两个旧流程保留。
- **不用 `st.tabs`**：tabs 会同时渲染两个表单和文件上传器；pills 只渲染当前方向。
- **首页两张卡保留**：它们变成带方向的快捷入口，写 `report_mode_pending` 后跳到 `report`。
- **双向 feed**：`state/browse.py` 同时取未配对失物与拾获；匹配/已处理/不公开的排除。
- **新表 `report_meta`**：`published_at` + `public`。`items.time` 是丢失/拾获日期，不能当发布时间；首次发布时间在后续 upsert 时保持不变。
- **默认公开、可关闭**：登记失物/拾获表单都有「允许在近期动态中公开展示」复选框，默认勾选；`public=0` 只退出 feed，不影响匹配、订阅、通知。
- **显示发布时间**：feed 卡片显示 `发布于：YYYY-MM-DD HH:MM`，用于标明先后；旧数据显示「旧数据未记录」。
- **不显示身份/联系方式**：feed 只读 `items` 与指纹，不 JOIN `users`。
- **不改既有表**：只新增 `report_meta`。

## 改了什么

- 新增 `state/report.py`：`report()`、`MODES`、方向 pills、`report_mode_pending`。
- 新增 `matching/report_meta.py`：`ReportMeta.publish/get/set_public/is_public`。
- `state/lost.py` / `state/found.py`：新增 `embedded` 参数；表单加公开复选框；登记后写 `ReportMeta`。
- `state/browse.py`：双向 feed、方向筛选、失物/拾获胶囊、发布时间、公开过滤、两个登记 CTA。
- `app.py`：注册 `state='report'`。
- `ui/components.py`：顶栏 5 项；「近期动态」替换「最近拾获」。
- `state/lost_or_found.py`：首页两张卡预选方向；按钮改名「浏览近期动态」。
- `state/profile.py` / `state/notifications.py`：相关 CTA 改为统一登记页。
- `seed_demo.py`：为演示数据写 `report_meta`。
- 测试：`tests/test_browse.py` 方向/发布时间；`tests/test_report_meta.py`；`test_pages_smoke.py` 统一登记切换与 feed。
- 文档：新增 `.dsh/agents/report-and-feed.md`，同步 architecture、data-model、privacy、ui、README、AGENTS、backlog、operations。

## 验证

- `pytest -q`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）→ **88 passed**。
- `compileall` 通过。
- 真实数据（11 条 items，先回填 `report_meta`）：
  - feed 显示 **9 件（失物 5 · 拾获 4）**，9 条「发布于」，无 `example.invalid`；
  - 方向筛选：失物 5 / 拾获 4；关键词「键盘」2 件；
  - 把一条失物设为不公开 → 从 feed 消失；恢复 → 重新出现；
  - 首页「开始登记失物/拾获」分别把统一登记页的 pills 预选到「我丢了东西 / 我捡到东西」；
  - 顶栏 5 项，`登记物品` / `近期动态` 正常。
- 过程中修掉一个 Streamlit 警告：同时给 pills 传 `default` 和 session state 会触发 policy warning；改为 `setdefault('report-mode', ...)` 后不再出现。
- AppTest 支持读取/切换 `st.pills`；文件上传仍不能驱动，拾获方向只验证到“渲染了上传入口”。

## 未做 / 留给后续

- 公开失物描述可能被照抄；认领验证仍未实现。
- 失物没有照片，feed 里只能文字。
- 公开/不公开只能在登记时设置，事后没有 UI（`set_public()` 已就绪）。
- feed 全量加载，没有分页。
- 旧数据没有发布时间；当前演示库已手动回填。
- 本机工作副本没有 `.git` 且未安装 git，因此没有按 `dsh` 分支提交；改动只存在于工作区。
