# 开发日志索引

`.dsh/logs/` 是**面向开发者的过程记录**：为什么这么做、试过哪些死路、根因分析。

- 每条日志是**当时的过程快照**，发现写错了**不回改正文**，在当天或新日志里说明
- 现行事实与设计在 [`../agents/`](../agents/)；本目录只解释「怎么变成现在这样的」
- 本索引是**手工维护的**（本仓库没有生成脚本）：新增日志后回来加一行

| 日期 | 日志 | 一句话 |
| --- | --- | --- |
| 2026-10-21 | [agent-system-bootstrap](2026-10-21-agent-system-bootstrap.md) | 建立 `.dsh/` 知识库、`AGENTS.md`、`backlog.md` 与链接校验脚本，把代码事实拆成七个主题文档。 |
| 2026-10-21 | [readme-rewrite](2026-10-21-readme-rewrite.md) | README 覆写为中文，补页面流程、模块地图、已知限制与常见问题，并核对旧表述。 |
| 2026-10-21 | [chinese-ui](2026-10-21-chinese-ui.md) | 前端文案全部中文化：页面标签、认证表单、状态/方法映射、错误消息，并更新烟测。 |
| 2026-10-21 | [registration-form](2026-10-21-registration-form.md) | 用自建中文注册表单替换认证库表单：支持中文姓名、无验证码、中文错误。 |
| 2026-10-21 | [caption-slow-hf](2026-10-21-caption-slow-hf.md) | 图注慢/加载失败：HF 不可达、缓存不完整、BLIP 在 CPU；改为本地优先 + GPU。 |
| 2026-10-21 | [localization-backlog](2026-10-21-localization-backlog.md) | 盘点剩余英文化（地点下拉、BLIP 图注、Streamlit 控件等）写入 backlog，本轮不改代码。 |
| 2026-10-21 | [demo-seed](2026-10-21-demo-seed.md) | 地点中文化；用 4 张照片灌入 bob 拾获 / alice 失物，4 条失物 top-1 全部命中。 |
| 2026-10-21 | [chinese-caption](2026-10-21-chinese-caption.md) | BLIP 英文图注后接 opus-mt-en-zh 中译；模型本地缓存，失败回退英文。 |
| 2026-10-21 | [model-bootstrap](2026-10-21-model-bootstrap.md) | 模型不入库；新增 download_models.py 与 run.sh，协作者一条命令拉齐并离线启动。 |
| 2026-10-21 | [auth-cookie-refresh](2026-10-21-auth-cookie-refresh.md) | 刷新掉登录：写 cookie 的组件被 st.rerun() 丢弃；改为下一轮补写，并用请求头 cookie 静默恢复。 |
| 2026-10-21 | [ui-redesign](2026-10-21-ui-redesign.md) | 界面重做：设计令牌 + 全局 CSS + 顶栏/卡片组件 + SVG 图标，登录改自建表单。 |
| 2026-10-21 | [intake-questions](2026-10-21-intake-questions.md) | 拾获侧改为登记前主动追问：双语图注、属性确认芯片、池上信息增益选题、无标记中性。 |
| 2026-10-21 | [merge-to-main](2026-10-21-merge-to-main.md) | 把 `dsh` 的 12 个提交 fast-forward 进 `main`：合并清单、验证结果与遗留项。 |
| 2026-10-21 | [deepseek-vision](2026-10-21-deepseek-vision.md) | 拾获登记接入 DeepSeek 视觉模型：VLM 优先、BLIP 兜底、图上文字进指纹。 |
| 2026-10-21 | [settings-file](2026-10-21-settings-file.md) | 手工配置收进 settings.yaml：环境变量优先、.env 方案放弃、run.sh 兜底 python -m。 |
| 2026-10-21 | [profile-enrichment](2026-10-21-profile-enrichment.md) | 失物也问登记前问题；追问答案以属性形式落库；候选卡与「补全信息」让双方看到同一份属性。 |
| 2026-10-21 | [withdraw-report](2026-10-21-withdraw-report.md) | 我的记录支持撤销失物/拾获：硬删除并级联清理请求、配对与指纹，已确认的配对拒绝撤销。 |
| 2026-10-21 | [family-and-intake](2026-10-21-family-and-intake.md) | 删掉失物登记追问；杯子/水瓶、圆形/圆柱形等同族取值改按一致计分，分数从 0.25 回到 0.39。 |
| 2026-10-21 | [release-checklist](2026-10-21-release-checklist.md) | 发布前检查：6 个提交的范围、从零交接清单、不入库文件、验证结果与已知限制。 |
| 2026-10-21 | [share-demo-data](2026-10-21-share-demo-data.md) | 演示账号生成脚本 + 提交 4 张演示照片，协作者克隆后能复现同一份数据。 |
| 2026-10-21 | [browse-and-e2e](2026-10-21-browse-and-e2e.md) | 新增「最近拾获」只读浏览与筛选；同天用 DeepSeek + CLIP 跑通真实端到端并记录结果。 |
| 2026-10-21 | [subscriptions-notifications](2026-10-21-subscriptions-notifications.md) | 订阅单件失物，新拾获入库时按证据分生成站内通知；顶栏未读数、通知页可重建候选。 |
| 2026-10-21 | [returned-lifecycle](2026-10-21-returned-lifecycle.md) | 新增已归还/归档：非破坏性结束报告，退出候选池，我的记录分流并可恢复；修复处理时间渲染 bug。 |
| 2026-10-21 | [unified-intake-feed](2026-10-21-unified-intake-feed.md) | 合并登记入口为「登记物品」，把「最近拾获」扩成双向「近期动态」；新增发布时间与公开开关。 |
| 2026-10-21 | [request-lifecycle](2026-10-21-request-lifecycle.md) | 请求 pending 上限 3、拒绝 24 小时冷却、接受自动关闭其他请求；新增 request_history 与页面状态。 |
| 2026-10-22 | [time-location-prior-and-eval](2026-10-22-time-location-prior-and-eval.md) | 排序加入时间/地点软先验（最多 +0.05，缺失中立）；新增 evaluate.py 对比 Recall/MRR。 |
| 2026-10-22 | [lost-photo-hybrid](2026-10-22-lost-photo-hybrid.md) | 失物可选照片；文本+图像混合向量存 items.emb；动态/记录/候选显示失物照片。 |
| 2026-10-22 | [publish-time-dedup-watermark](2026-10-22-publish-time-dedup-watermark.md) | 每帖显示发布时间+内容指纹；dHash 图片查重、文本近似提示、公开图水印；不能阻止截图但可追溯。 |
| 2026-10-22 | [restore-after-zip-merge](2026-10-22-restore-after-zip-merge.md) | 压缩包合并把整个源码树记成删除；回退到 3f17878，清理 Windows 残留，再用完整目录重新导入。 |
| 2026-10-22 | [demo-dataset-12](2026-10-22-demo-dataset-12.md) | 演示集扩到 12 对：8 张 Open Images（CC BY 2.0）照片 + 对应描述；临时库试灌 Recall@1 = 12/12。 |
| 2026-10-22 | [multi-user-demo](2026-10-22-multi-user-demo.md) | 本地库换成 6 个账号（密码=用户名）：每人 2 拾获 + 3 失物，文案改用户口吻；evaluate Recall@1 = 11/12。 |
| 2026-10-22 | [showcase-page](2026-10-22-showcase-page.md) | 独立静态展示页：11 屏 + 交互，新增语义/证据原理；数据由 build_demo.py 从真实引擎生成；离线可跑。 |
| 2026-10-22 | [showcase-principles](2026-10-22-showcase-principles.md) | 展示页补两屏原理：双塔对比学习 + 真实余弦热力图；多语文本塔把中文接上图像，中英两行同序；数据进 `principles`。 |
