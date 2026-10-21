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
