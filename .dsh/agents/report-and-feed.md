# 统一登记与双向近期动态

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[架构](architecture.md) 说明页面分发；[数据模型](data-model.md) 说明 `report_meta`；[隐私](privacy.md) 说明公开范围；[生命周期](lifecycle.md) 说明已处理物品为什么不出现在 feed。

**本文件状态：`【事实】`**——读自 `state/report.py`、`state/browse.py`、`state/lost.py`、`state/found.py`、`matching/report_meta.py`（2026-10-21）。

## 为什么合并

原来「登记失物」和「登记拾获」是两个平级页面，顶栏有 6 项，移动端要横向滚动；两者只差一个方向，却各自重复页头、返回路径和导航高亮。现在：

- 顶栏改为 **首页 / 登记物品 / 近期动态 / 通知 / 我的记录**（5 项）。
- 「登记物品」里用 `st.pills` 切换「我丢了东西 / 我捡到东西」，只渲染当前方向。
- 首页两张卡仍然保留，但都进入 `state='report'`，只是预选方向。

## 统一登记的调用链

```text
首页「开始登记失物/拾获」
  -> session_state.report_mode_pending = 'lost'/'found'
  -> state = 'report'
  -> state/report.py::report()
       -> topbar('report')
       -> st.pills(... key='report-mode')
       -> lost(authenticator, embedded=True)
          或 found(authenticator, embedded=True)
```

- 【事实】`lost()` / `found()` 新增 `embedded` 关键字参数；为 True 时跳过各自的 `topbar()` 与 `page_header()`，其余表单与逻辑不变。
- 【事实】`report()` 先消费 `report_mode_pending`，再 `session_state.setdefault('report-mode', ...)`；这样首页入口能预选方向，又不会同时传 `default` 和 session state（Streamlit 会警告）。
- 【事实】`state='lost'` / `state='found'` 仍保留在 `app.py` 的分发里，供旧链接与测试直接调用；顶栏不再出现这两个入口。
- 【事实】`lost()` / `found()` 的步骤标题在嵌入式模式下由 `report()` 统一显示「第 1 步 / 共 2 步」。
- 【设计】用 `st.pills` 而不是 `st.tabs`：`st.tabs` 会同时渲染两个表单（包括文件上传器），容易产生隐藏的重复控件与无谓的模型调用。

## 双向近期动态

- 【事实】`state/browse.py::load_records()` 同时读取 `get_unmatched_lost_items()` 与 `get_unmatched_found_items()`，给每条记录加 `direction`。
- 【事实】两个查询本身已经排除已配对（`matches`）与已处理（`item_status`）的物品；feed 不需要再判断。
- 【事实】`report_meta.public=0` 的物品不出现在 feed；匹配、通知仍可使用它们（公开与否只影响发现层）。
- 【事实】feed 支持方向（全部/失物/拾获）、关键词、类型、地点、时间筛选；关键词同时匹配描述、地点、规范值与中文显示值。
- 【事实】按 `published_at` 倒序；没有 `report_meta` 的旧数据回退到 `items.time`，排序仍稳定。
- 【事实】最多渲染 60 件；超过时提示“最多显示最近 60 件”。
- 【事实】失物与拾获都可以有照片：失物照片可选，没有照片时卡片是纯文字；拾获照片是登记必填。卡片用「失物」/「拾获」胶囊区分。
- 【事实】feed 不 JOIN `users`，不展示用户名、邮箱或联系方式；底部只提供去登记物品的两个入口。

## 失物照片与混合向量

- 【事实】失物表单有可选上传（png/jpg/jpeg，≤8 MB）；照片先过 `clean_image`（EXIF、缩放、RGB），再 `encode_image`。
- 【事实】有照片时查询向量是 `normalize(0.5×text_embedding + 0.5×image_embedding)`（`matching.models.combine_text_image`）；没有照片时只用文本向量。
- 【事实】照片存进现有 `items.image`，混合向量存进现有 `items.emb`；没有新增表/列。
- 【事实】近期动态、我的记录、匹配候选都会显示失物照片（如果有）。
- 【设计】0.5/0.5 是起点，不是校准结果；`evaluate.py` 默认的 12 对演示失物没有照片，所以评估覆盖的是文本路径；混合向量另有单元测试。
- 【设计】失物照片和拾获照片可能来自同一张图，会制造虚假的高相似度；这属于“照抄描述”的同类风险，最终仍要靠认领验证。

## 发布时间与公开可见性（`report_meta`）

```sql
CREATE TABLE IF NOT EXISTS report_meta (
  item_id INTEGER PRIMARY KEY,
  published_at INTEGER NOT NULL,
  public INTEGER NOT NULL DEFAULT 1
)
```

- 【事实】`items.time` 是**丢失/拾获日期**，不是发布时间；`published_at` 是登记时刻，两者分开显示。
- 【事实】登记失物/拾获时调用 `ReportMeta.publish(item.id, public=...)`；首次插入记录 `published_at`，之后的 upsert 只更新 `public`，不会改写首次发布时间。
- 【事实】默认 `public=1`；表单复选框「允许在近期动态中公开展示」默认勾选，取消后该条不进入 feed，但仍参与匹配、订阅与通知。
- 【事实】没有 `report_meta` 行的旧数据按公开处理，发布时间显示「旧数据未记录」；`seed_demo.py` 会为新灌数据写行。
- 【事实】`set_public()` 支持事后修改可见性，但当前页面只在登记时提供复选框，没有单独的“改可见性”按钮。
- 【设计】发布时间用于标明先后，**不是所有权证明**；它让“后照抄描述”至少留下时间差，但不能替代认领验证。

## 隐私与风险

- 【事实】失物与拾获的描述、照片（失物可选/拾获必有）、地点/日期、发布时间、已共享属性对所有已登录用户可见。
- 【事实】不展示拾获者/失主的用户名或邮箱；联系方式仍然只在 `match_requests.status='accepted'` 后由 `MatchRequests.accepted()` 返回。
- 【事实】公开是默认值，但失主/拾获者可以在登记时取消勾选；取消后只退出 feed，不影响匹配。
- 【设计】公开失物描述会放大“照抄描述冒领”的风险。当前没有认领验证；拾获者仍需自己判断是否接受请求。后续应补私密挑战问题/第二张照片。
- 【设计】页面明确提示“描述会公开展示，请勿写门牌号、证件号等敏感信息”。

## 已知边界

- 失物照片是可选的；没有照片时仍只用文本向量；混合权重 0.5/0.5 未校准。
- 失物照片和拾获照片可能是同一张（例如从 feed 保存的），会制造虚假的高相似度；这是“照抄描述”的同类风险。
- 可见性只能在登记时设置；没有事后开关（`set_public()` 已就绪，缺 UI）。
- 旧数据没有发布时间，显示「旧数据未记录」；本次演示库已手动回填。
- feed 全量加载未配对物品（含拾获图片 BLOB），>60 件只截断显示，没有分页/索引。
- 发布时间是本地时钟；没有校时或防篡改，不能作为正式证据。
- AppTest 支持 `st.pills` 的读取与切换，但文件上传仍不能驱动；统一登记页的拾获方向只能验证到“渲染了上传入口”。

## 测试

- `tests/test_browse.py`：方向筛选、发布时间排序、关键词/类型/地点/时间。
- `tests/test_report_meta.py`：首次发布时间保留、可见性 upsert、旧数据默认公开。
- `tests/test_pages_smoke.py`：统一登记页按 pills 切换方向；feed 空态与卡片。
- 2026-10-21 真实数据：feed 9 件（失物 5 + 拾获 4），发布时间 9 条，无邮箱；方向筛选 5/4；关键词「键盘」2 件；把一条失物设为不公开后从 feed 消失，恢复后重新出现；首页两个入口分别把 pills 预选到失物/拾获。

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：统一登记入口、双向 feed、`report_meta` 发布时间/公开开关、隐私与已知边界。 |
| 2026-10-22 | 失物可选照片：`items.image` 显示、`items.emb` 存文本+图像混合向量；feed/记录/候选同步展示。 |
