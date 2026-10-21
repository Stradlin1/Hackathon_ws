# 本次改动说明（2026-10-22）

> 面向：项目作者、队友、评审。
> 范围：从最初的 P0 一轮一轮做到 P1 的失物照片与查重；只改本仓库的单机 Streamlit 应用。
> 详细事实与不变量在 [`.dsh/agents/`](.dsh/agents/)，过程记录在 [`.dsh/logs/`](.dsh/logs/)。

---

## 一、这次做了什么

### 1. 统一登记入口

**问题**：`登记失物` 和 `登记拾获` 是两个平级页面，顶栏 6 项，移动端要横向滚动；两者只差方向，却重复页头与导航。

**做法**：

- 新增 [`state/report.py`](state/report.py)：一个「登记物品」入口，用 `st.pills` 在「我丢了东西 / 我捡到东西」之间切换。
- `lost()` / `found()` 新增 `embedded=True` 参数，只渲染表单本身，不重复顶栏/页头。
- 顶栏改为 **首页 / 登记物品 / 近期动态 / 通知 / 我的记录**（5 项）。
- 首页两张卡保留，但都跳到统一页并预选方向。

**相关文件**：[`app.py`](app.py)、[`state/report.py`](state/report.py)、[`state/lost.py`](state/lost.py)、[`state/found.py`](state/found.py)、[`ui/components.py`](ui/components.py)、[`state/lost_or_found.py`](state/lost_or_found.py)

### 2. 双向近期动态

**问题**：原来只有「最近拾获」，失主必须先报失才能看到；捡到东西的人也无法主动找失主。

**做法**：

- [`state/browse.py`](state/browse.py) 同时读取未配对的失物与拾获。
- 支持方向（全部/失物/拾获）、关键词、类型、地点、时间筛选。
- 卡片显示方向胶囊、描述、地点/日期、发布时间、属性；有照片就显示照片。
- 只显示未配对、未处理、允许公开的帖子；不展示发布者身份或联系方式。
- 新增 [`matching/report_meta.py`](matching/report_meta.py)：`report_meta(item_id, published_at, public)` 记录首次发布时间与公开/不公开。
- 登记失物/拾获表单都有「允许在近期动态中公开展示」复选框，默认勾选；关闭后只退出 feed，仍参与匹配与通知。
- 卡片底部统一显示：`首次发布于：… · 内容指纹 …`。

**相关文件**：[`state/browse.py`](state/browse.py)、[`matching/report_meta.py`](matching/report_meta.py)、[`seed_demo.py`](seed_demo.py)

### 3. 订阅与站内通知

**问题**：失主不会每天回来刷新；匹配上了也可能错过。

**做法**：

- 新增 [`matching/notifications.py`](matching/notifications.py)：`subscriptions` / `notifications` 两张新表。
- 登记失物时默认订阅；每件失物可在「我的记录」里开关提醒。
- 新拾获入库时，用同一套 `cosine + rank_candidates` 计算与每条订阅失物的相关性；排序指标 ≥ **0.40** 才写通知。
- 顶栏显示 `通知 · N`；通知页可标记已读、全部已读，并可「查看这件失物的候选」重建匹配会话。
- 通知不 JOIN `users`，不展示拾获者身份或联系方式。

**相关文件**：[`matching/notifications.py`](matching/notifications.py)、[`state/notifications.py`](state/notifications.py)、[`state/found.py`](state/found.py)、[`state/lost.py`](state/lost.py)、[`state/profile.py`](state/profile.py)、[`app.py`](app.py)

### 4. 已归还 / 归档生命周期

**问题**：原来的「撤销登记」是硬删除；没有“已归还”的完成态，也没有历史。

**做法**：

- 新增 [`matching/lifecycle.py`](matching/lifecycle.py) 与 `item_status` 表：`returned` / `archived`。
- 已处理物品自动退出候选池、浏览页、通知匹配；但保留 `items`、归属、指纹、请求与配对记录。
- 「我的记录」分成「进行中」与「已处理」；已处理可「恢复为进行中」。
- 匹配页对已处理物品做拦截，避免旧会话继续展示候选。
- 撤销仍然是硬删除，两者并存。

**相关文件**：[`matching/lifecycle.py`](matching/lifecycle.py)、[`db_manager.py`](db_manager.py)、[`state/profile.py`](state/profile.py)、[`state/interactive_match.py`](state/interactive_match.py)

### 5. 请求生命周期

**问题**：拒绝后永久不可再发；同一拾获可被无限请求；接受一个后其他 pending 还挂着，甚至可能重复接受。

**做法**（[`matching/requests.py`](matching/requests.py)）：

- 同一拾获最多 **3 个 pending**。
- 拒绝后 **24 小时冷却**；到期可重新发起。
- 新增 `request_history` 表，记录每次结束的尝试；冷却到期删除旧 rejected 行并重建 pending。
- 接受一个请求时，涉及该拾获/该失物的其他 pending 自动改为 rejected，并写 history。
- `_is_matched` 同时检查拾获与失物，禁止同一物品被接受两次。
- 匹配页/我的记录显示 pending、冷却中、可重新发起等真实状态。

**相关文件**：[`matching/requests.py`](matching/requests.py)、[`state/interactive_match.py`](state/interactive_match.py)、[`state/profile.py`](state/profile.py)

### 6. 时间 / 地点软先验

**问题**：`items.time` / `items.location` 原来完全不参与排序。

**做法**（[`matching/engine.py`](matching/engine.py)）：

```text
base  = clamp(0.72×CLIP + 0.28×证据项, 0, 1)
time  = 0.03 × exp(-|相差天数| / 14)      # 两边都有日期
place = 0.02                              # 同地点，且不是“未知/其他”
score = clamp(base + time + place, 0, 1)
```

- 只加不减；缺失/未知不扣分，最多 +0.05。
- `rank_candidates(..., use_priors=False)` 可关闭，评估脚本用它对比。
- 输出增加 `base_score` / `prior_bonus`；候选卡显示地点/日期与加分。

**相关文件**：[`matching/engine.py`](matching/engine.py)、[`matching/workflow.py`](matching/workflow.py)、[`matching/notifications.py`](matching/notifications.py)、[`state/interactive_match.py`](state/interactive_match.py)

### 7. 离线评估脚本

**问题**：只有 mock 单测，没有可重复的 Recall/MRR。

**做法**：

- 新增 [`evaluate.py`](evaluate.py)：默认用 `seed_demo.py` 的 4 对演示数据；支持 `--labels`、`--verbose`、`--json`。
- 会把**所有**拾获报告都纳入候选（包括已配对），同时输出软先验开启/关闭的 Recall@1、Recall@5、MRR。
- 当前结果：两组都是 **Recall@1 4/4、MRR 1.000**；软先验把每对正确候选从 0.48–0.52 抬到 0.53–0.57。

**相关文件**：[`evaluate.py`](evaluate.py)、[`tests/test_evaluate.py`](tests/test_evaluate.py)

### 8. 失物可选照片 + 混合向量

**问题**：失物只有文字，feed 里失物没有照片，也很难描述品牌/型号。

**做法**：

- 失物表单增加「上传物品照片（可选）」；照片先 `clean_image`（去 EXIF、缩放、RGB）。
- 有照片时：

  ```text
  items.emb = normalize(0.5×text_embedding + 0.5×image_embedding)
  ```

  没有照片时仍然只用文本向量。
- 照片存现有 `items.image`，混合向量存现有 `items.emb`；**没有新增表/列**。
- 近期动态、我的记录、匹配候选都显示失物照片（如果有）。

**相关文件**：[`state/lost.py`](state/lost.py)、[`matching/models.py`](matching/models.py)、[`state/browse.py`](state/browse.py)、[`state/profile.py`](state/profile.py)

### 9. 发布时间、内容指纹、查重、水印

**问题**：公开 feed 后，任何人可以保存拾获照片/复制描述，再注册一条“失物”，制造虚假高相似度。

**做法**：

- **发布时间 + 内容指纹**：每帖底部显示 `首次发布于：… · 内容指纹 …`；指纹是规范化描述的 SHA-256 前 10 位。
- **图片 dHash 查重**：新增 `image_hashes` 表，64-bit 感知哈希；上传时与已有帖子比对，Hamming ≤ 6 提示近似重复，**不阻断**。
- **文本近似**：提交时用 `SequenceMatcher`，长度 ≥ 12、ratio ≥ 0.92 提示；匹配页顶部显示一次。
- **公开图水印**：显示时加底部半透明条，写 `404NotFound · #帖子尾号 · 日期`；入库图片/向量/dHash 保持干净。
- **明确不做**：CSS/JS 禁止右键/选择、禁止保存。浏览器截图/OCR/开发者工具无法真正阻止；这些只能算“防顺手复制”，不能当安全边界。

**相关文件**：[`matching/content_hash.py`](matching/content_hash.py)、[`state/lost.py`](state/lost.py)、[`state/found.py`](state/found.py)、[`state/browse.py`](state/browse.py)、[`state/profile.py`](state/profile.py)、[`state/notifications.py`](state/notifications.py)、[`state/interactive_match.py`](state/interactive_match.py)

---

## 二、新增数据表

既有五张表（`items` / `users` / `lost_items` / `found_items` / `matches`）**没有改列**。新增：

| 表 | 用途 | 关键约束 |
| --- | --- | --- |
| `item_status` | 已归还/归档 | `item_id` PK；状态 `returned`/`archived` |
| `subscriptions` | 失物订阅 | 唯一键 `(username, kind, lost_item_id, keyword, category, location)` |
| `notifications` | 站内通知 | 唯一键 `(username, found_item_id, subscription_id)` |
| `request_history` | 请求冷却与审计 | 每次结束的 accepted/rejected 尝试 |
| `report_meta` | 首次发布时间与公开开关 | `item_id` PK；`published_at` / `public` |
| `image_hashes` | 图片 dHash 查重 | `item_id` PK；只存 64-bit 哈希，不存图片副本 |

数据模型细节：[`.dsh/agents/data-model.md`](.dsh/agents/data-model.md)。

---

## 三、文件清单（主要）

| 文件 | 改动 |
| --- | --- |
| [`app.py`](app.py) | 注册 `report` / `notifications`；每轮刷新未读数 |
| [`db_manager.py`](db_manager.py) | 新增 `item_status` 表、`get_item_status()`、未匹配查询 JOIN 过滤 |
| [`matching/engine.py`](matching/engine.py) | 时间/地点软先验、`use_priors`、`base_score/prior_bonus` |
| [`matching/workflow.py`](matching/workflow.py) | 会话带查询时间/地点、候选带时间/地点、`include_matched` |
| [`matching/models.py`](matching/models.py) | `combine_text_image()` |
| [`matching/requests.py`](matching/requests.py) | pending 上限、拒绝冷却、接受自动关闭、`request_history` |
| [`matching/notifications.py`](matching/notifications.py) | 新增：订阅、通知、相关性判断 |
| [`matching/lifecycle.py`](matching/lifecycle.py) | 新增：归还/归档状态 |
| [`matching/report_meta.py`](matching/report_meta.py) | 新增：发布时间/公开开关 |
| [`matching/content_hash.py`](matching/content_hash.py) | 新增：内容指纹、dHash、文本近似、水印 |
| [`state/report.py`](state/report.py) | 新增：统一登记入口 |
| [`state/browse.py`](state/browse.py) | 双向 feed、方向筛选、发布时间/指纹、水印 |
| [`state/notifications.py`](state/notifications.py) | 新增：通知页、未读、重建候选 |
| [`state/lost.py`](state/lost.py) | `embedded`、可选照片、混合向量、订阅、公开、查重 |
| [`state/found.py`](state/found.py) | `embedded`、公开、通知、图片/文本查重 |
| [`state/profile.py`](state/profile.py) | 订阅开关、已处理分流、请求重发、发布时间/水印 |
| [`state/interactive_match.py`](state/interactive_match.py) | 请求状态/冷却、软先验、候选发布时间/水印、重复提示 |
| [`state/lost_or_found.py`](state/lost_or_found.py) | 首页入口改为统一登记/近期动态 |
| [`ui/components.py`](ui/components.py) | 顶栏 5 项、通知未读标签 |
| [`ui/icons.py`](ui/icons.py) | `bell` 图标 |
| [`seed_demo.py`](seed_demo.py) | 写入 `report_meta` 与图片 dHash |
| [`reset_db.py`](reset_db.py) | 重建样例时写 `report_meta` |
| [`evaluate.py`](evaluate.py) | 新增：Recall@1/5、MRR、软先验对比 |

测试新增：`test_browse.py`、`test_notifications.py`、`test_lifecycle.py`、`test_requests.py`、`test_report_meta.py`、`test_evaluate.py`、`test_content_hash.py`；并补了 `test_matching.py` 与 `test_pages_smoke.py`。

知识库新增：[`.dsh/agents/notifications.md`](.dsh/agents/notifications.md)、[`lifecycle.md`](.dsh/agents/lifecycle.md)、[`report-and-feed.md`](.dsh/agents/report-and-feed.md)、[`request-lifecycle.md`](.dsh/agents/request-lifecycle.md)、[`anti-copy.md`](.dsh/agents/anti-copy.md)。

---

## 四、验证结果

```text
pytest                108 passed
compileall            OK
check_links.py        0 broken
streamlit HTTP        200
evaluate.py           prior=on/off 都是 Recall@1 4/4、MRR 1.000
```

真实数据抽查：

- 近期动态 9 条「首次发布于…内容指纹」；我的记录 7 条；通知 1 条。
- 鼠标照片 dHash 命中失物 `#942228599187412484` 与拾获 `#1517754286063885471`，距离都是 0。
- 相同描述文本近似 `ratio=1.0`。
- 请求：发送 → pending（按钮禁用）→ 对方拒绝 → 24 小时冷却 → 历史时间提前后出现「重新发送匹配请求」→ 回到 pending。
- 失物照片：文本/图像/混合向量都是 512 维，混合后范数 1.0。
- 页面文本不出现邮箱；联系方式仍然只在 accepted 后出现。

---

## 五、红线与已知风险

**仍然守住的红线**：

1. 指纹只接受有原文证据的值。
2. 缺失属性中性，矛盾才扣分。
3. 基础分仍是 72% 语义 + 28% 证据；时间/地点软先验最多 +0.05，只加不减。
4. 页面仍叫“排序指标”，不叫概率/置信度。
5. 联系方式只在 `accepted` 后由 `MatchRequests.accepted()` 返回。
6. 澄清答案只以属性形式落库。
7. 不改既有五张表；新能力全部新表。
8. 上传图片先 `clean_image` 去 EXIF；模型失败降级。

**新增的风险/边界**：

- 公开失物描述 + 公开照片放大了“照抄描述/保存照片再上传”的风险；目前只有提示与追溯，不能阻止。
- dHash ≤ 6、文本 ratio ≥ 0.92、通知阈值 0.40、软先验 0.03/0.02/14 天，都是演示数据上的启发式，未用真实数据校准。
- 时间/地点软先验使用丢失/拾获日期，不是发布时间；迟到登记可能失真。
- `published_at`、内容指纹、dHash 都是本地数据，有数据库权限的人可以改；不是密码学证明。
- AppTest 不能驱动文件上传，也不能执行 `st.dialog` 内的提交；这两条路径靠 fake UI + 真实模型函数验证，仍需人工在浏览器点一次。
- 当前 `.venv` 是基于 `yolo` 环境 Python 建的 `--system-site-packages`，复用了它的 CUDA torch；换环境时要重新装依赖。
- 本机工作副本没有 `.git`，也没有安装 git；`AGENTS.md` 的 `dsh` 分支纪律这次无法执行，所有改动只在工作区。

---

## 六、接下来的修改建议

### 第一优先：来源可信度

**问题**：DeepSeek/BLIP 图注读出的颜色、材质现在和用户陈述同等可信；图注读错会作为“真实矛盾”扣分（−0.8 × 权重），比“缺失”更糟。

**建议**：

- 指纹里给每个属性记录来源：`user` / `caption` / `model`。
- 机器来源的矛盾降权（例如 ×0.5），用户确认的矛盾保持全权重。
- 需要同步改 `rank_candidates`、文档与测试；仍保持 72/28 基础公式。

**工期**：2–3 天。**风险**：会改动红线 2/3 的文档表述，但方向是让证据更可信。

### 第二优先：多图 + 本地 OCR

- 拾获登记支持多张照片，逐图抽属性后合并；冲突降级为“不确定”。
- 本地 OCR（Tesseract/PaddleOCR）读型号/序列号，作为无 DeepSeek key 时的兜底；OCR 文本仍要过字面证据校验。
- **工期**：3–5 天。**风险**：系统级依赖与权重体积；演示机不一定装得上。

### 第三优先：站内消息 / 联系方式遮罩

- 接受后先开匿名会话，而不是直接给邮箱；双方同意交接后再揭示联系方式。
- 需要新 `messages` 表；Streamlit 的聊天体验有限，可能需要轮询。
- **工期**：3–5 天。

### 第四优先：保管点 / 交接码 / 线下核验

- 拾获者可标记“已交至图书馆/保卫处”，失主直接去领。
- 接受配对后生成一次性交接码/二维码，双方到场展示，工作人员核对学生证。
- 这是比线上问答更可信的验证；**工期**：交接码 1 天 + 线下流程。
- 如果之后重新考虑认领验证，建议和“两层描述（公开摘要 + 私密特征）”一起做，不要单独做泛泛的问答。

### 第五优先：敏感内容打码

- 上传时提示人脸/证件/宿舍；可选 OpenCV 人脸或证件区域模糊。
- **工期**：2–3 天。**风险**：可能误伤物品细节，影响匹配。

### 小项

- **重复项合并 UI**：dHash/文本查重已经提示，但还没有“合并”动作；1–2 天。
- **保存搜索**：关键词/类型/地点的订阅；1–2 天。
- **事后修改公开/不公开**：`ReportMeta.set_public()` 已就绪，缺 UI；0.5 天。
- **管理员/审核**：报告审核、重复合并、保管点管理；2–3 天。
- **移动端/PWA**：Streamlit 的移动体验有限；2–4 周，属于 P2。

### 不建议优先做

- **CSS/JS 禁止复制/右键**：防不住截图、OCR、开发者工具，还会伤无障碍；最多加一句“请勿截图传播”。
- **单独的“问两个问题”认领验证**：如果答案能从公开帖找到，就是形式主义；只有私密特征、一次性挑战或线下核验才有意义。

---

## 七、怎么运行与演示

在仓库根目录：

```powershell
$env:HF_HUB_OFFLINE='1'
.\.venv\Scripts\streamlit.exe run app.py --server.port 8501
```

打开 **http://localhost:8501**。

演示账号：

| 用户名 | 密码 | 用途 |
| --- | --- | --- |
| `alice` | `demo-pass-alice` | 失主；有失物、已确认配对、通知、pending 请求 |
| `bob` | `demo-pass-bob` | 拾获者；有拾获、待确认请求 |
| `demo` | `Demo@1234` | 空账号 |

验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe evaluate.py --verbose
.\.venv\Scripts\python.exe .dsh\tools\check_links.py
```

---

## 八、环境与演示数据

- `.venv` 基于 `C:\condahome\envs\yolo\python.exe` 创建（`--system-site-packages`），复用 CUDA torch 2.9.1+cu128；`torch.cuda.is_available()` 为 True。
- 已下载 CLIP 图像/文本编码器与 flan-t5-small；因为使用 DeepSeek 视觉，跳过了 BLIP 与 opus-mt。
- `settings.yaml` 里有 DeepSeek key（gitignored）；修改后要重启进程。
- `config_auth.yaml` 是 `create_demo_users.py` 生成的演示账号（gitignored）。
- `items.db` 是本地演示库；已灌入 4 张演示照片，并有一条 pending 键盘请求、一条通知、若干演示失物（其中一条挂了鼠标照片）。
- `image_hashes` 已为 6 张有图物品回填 dHash。
- 模型缓存约 1.4 GB（CLIP + flan），`.venv` 约 0.4 GB；已删除一个 450 MB 的下载残留。

---

## 九、给后续开发者的注意事项

1. **先读 [`.dsh/agents/`](.dsh/agents/)**：排序、指纹、数据模型、隐私、通知、生命周期、请求、查重各有一份事实文档；动手前按 [`AGENTS.md`](AGENTS.md) 路由表读对应文档。
2. **只新增表**：不要改既有五张表的列；新能力用 `CREATE TABLE IF NOT EXISTS`。
3. **改排序公式要同步文档与测试**：尤其是 72/28、0.389 阈值、软先验 +0.05。
4. **联系方式门禁不能松**：任何展示邮箱的查询都必须带 `status='accepted'`。
5. **页面只做编排**：算法在 `matching/`，表访问在 `db_manager.py` / `matching/storage.py` / `matching/requests.py`。
6. **AppTest 的限制**：文件上传、`st.dialog` 内提交不能驱动；这两条路径要人工在浏览器验证。
7. **提交前**：跑 `pytest`、`compileall`、`check_links.py`；如果恢复 git，按 `AGENTS.md` 的 `dsh` 分支纪律执行。
8. **演示数据是本地信任边界**：`items.db` 用 pickle 存图片/向量，不要把外部数据库当可信来源直接加载。

---

## 十、一句话总结

这一轮把应用从“能匹配”推进到了“能发现、能通知、能结束、能重试、能评估、能展示双向帖子、能对复制留下痕迹”：

- **发现**：双向近期动态 + 发布时间/内容指纹
- **通知**：按失物订阅 + 顶栏未读
- **结束**：已归还/归档 + 撤销并存
- **重试**：pending 上限、拒绝冷却、接受自动关闭
- **排序**：时间/地点软先验 + 文本/图像混合向量
- **评估**：Recall@1/5、MRR，软先验开关对比
- **追溯**：dHash + 文本近似 + 水印（不假装能禁止截图）

下一步最值得做的是 **来源可信度**：让机器读错的属性不再和用户陈述同等扣分。
