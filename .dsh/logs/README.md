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
