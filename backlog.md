# 待追踪任务

按「卡住什么」分组。每条写清：**缺什么、找谁、解开之后能做什么**。做完的条目直接删掉，不在这里留痕（历史在 `.dsh/logs/`）。

## 卡住「真实模型下的可用性，目前无法在本机证明」

现状：全部测试都 mock 掉模型；2026-10-21 实测本机 `streamlit`/`torch` 未安装、`numpy` 导入报 `No module named 'numpy.core._multiarray_umath'`，因此 `python -m pytest` 与 `streamlit run` 都无法执行。证据见 [`.dsh/logs/2026-10-21-agent-system-bootstrap.md`](.dsh/logs/2026-10-21-agent-system-bootstrap.md)。

- [ ] **在干净 venv 里跑通测试并记录结果**
      找：任一队员，新建 `.venv`（Python 3.10/3.11）后 `pip install -r requirements-dev.txt`，跑 `python -m pytest -q` 与 `python -m compileall -q app.py matching state`。
      为什么卡：目前没有任何一次本机测试通过记录；系统级 numpy 已损坏，直接 `pip install` 会继续混用。

- [ ] **用真实权重完成一次端到端演示**（BLIP 图注 → CLIP 检索 → 追问 → 发请求 → 对方接受 → 看到联系方式），保存一条成功样例和一条失败样例。
      找：能联网下载权重或有 GPU 的人。
      为什么卡：README 明确「单元测试不能替代装了模型的端到端运行」，这是评审最可能追问的点。

## 卡住「排序与配对策略是否是想要的」

- [ ] **决定 time/location 是否参与排序或过滤**
      找：产品负责人 / 评分标准。
      为什么卡：README 声明两者当前不参与排序，但 UI 已经在采集；若评审要求按地点/时间缩小范围，需要改 `matching/engine.py` 与候选查询，而不只是改文案。

- [ ] **决定被拒绝的请求能否重新发起**
      找：产品决定。
      为什么卡：`match_requests` 主键是 `(found_item_id, lost_item_id)` 且用 `INSERT OR IGNORE`，一次 reject 后该对**永久**不可再请求；误拒一次就等于这一对再也配不上。

- [ ] **决定待处理请求是否从候选池隐藏**
      找：产品决定。
      为什么卡：只有 `matches` 表影响 `get_unmatched_*`；pending 请求不影响，同一对可被反复「发送」（实际幂等返回 pending）。

## 卡住「仓库整洁」

- [ ] **确认 `static/` 三张 png 的去留**
      找：作者。
      为什么卡：2026-10-21 全仓 `grep -rn "static"` 无任何引用；读者会误以为它们被页面使用。

## 小项 / 待决

- [ ] 比赛若有成文评分标准/提交要求，落成 `.dsh/agents/` 独立文档并在 `AGENTS.md` 路由表加一行；2026-10-21 询问未获答复。
- [ ] `Database.get_item()` 对不存在的 id 抛 `TypeError`（对 `None` 取下标）；决定改为返回 `None` 还是保持并加调用方检查。
- [ ] `users.password` 列始终存空字符串（登录/注册只写 `User(username, '', email)`），认证实际读 `config_auth.yaml`；确认是否删除该列或写入哈希。
- [ ] `.dsh/skills/` 尚未创建；若要把用户级技能软链进本仓库，再建目录并在结构表登记（软链接本身不入库，见 `.gitignore`）。

---

已修复、已论证放弃、或已转为现行事实的问题不留在本文件。记录位置：

- [`.dsh/agents/`](.dsh/agents/) — 项目当前事实、设计决定、不变量、排查流程
- [`.dsh/logs/`](.dsh/logs/) — 开发过程、根因分析、走过的死路
- [`AGENTS.md`](AGENTS.md) — 索引、红线、路由表
