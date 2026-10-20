# 不变量（改代码前后逐条核对）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 每条都给出「为什么 / 怎么守 / 怎么机械检查」。检查命令都在仓库根目录执行。

**本文件状态：`【事实】`**——规则来自现有实现与测试（2026-10-21）。

## 1. 指纹值必须有原文证据

- **为什么**：模型会编造颜色/品牌；一旦进入排序，用户会看到"匹配"了一个不存在的特征，而分数依然很高。`fingerprint_from_text` 的校验是唯一闸门。
- **怎么守**：只允许在 `_has(source, proposal)` 成立、或提案与已观测值相等时写入属性；绝不把模型输出直接 `observed[field] = proposal`。
- **怎么查**：`grep -n "observed\[field\] = \|generated_verified = True" matching/fingerprint.py` —— 写入只应出现在校验分支内。

## 2. 缺失属性是中性，不是矛盾

- **为什么**：拾获照片的图注通常缺品牌/材质；把它们当矛盾会让真实失物排到后面。
- **怎么守**：`rank_candidates` 里 `if not query.get(key) or not other.get(key): continue`，比较前必须两边都有值。
- **怎么查**：`grep -n "if not query.get(key) or not other.get(key)" matching/engine.py` —— 应恰好 1 处。

## 3. 分数不是概率

- **为什么**：0.72×semantic + 0.28×evidence 是线性排序分，没有归一化含义；说成概率会误导用户交付联系方式。
- **怎么守**：页面、README、日志都写 "ranking metric"；不得新增"置信度/概率"文案。
- **怎么查**：`grep -rn "probability" --include=*.py --include=*.md .` —— 只应出现在否定句里。

## 4. 联系方式只在 accepted 之后可见

- **为什么**：这是产品唯一的隐私承诺；提前泄露邮箱不可撤回。
- **怎么守**：任何展示邮箱的查询都必须带 `status='accepted'`；不要把 `users.email` JOIN 进 `incoming`/`outgoing`。
- **怎么查**：`grep -n "contact_email\|u.email" matching/requests.py` —— 只应在 `accepted()` 的 SELECT 里。

## 5. 澄清答案不落库

- **为什么**：答案可能包含失主才知道的细节（划痕位置、贴纸内容），属于个人线索；落库会扩大泄露面。
- **怎么守**：答案只进 `session["answers"]`；不要给 `item_fingerprints` 或 `match_requests` 加 answers 列。
- **怎么查**：`grep -rn "answers" --include=*.py matching/storage.py matching/requests.py` —— 应无输出。

## 6. 只新增表，不改既有表

- **为什么**：用户的 `items.db` 里已有数据，`CREATE TABLE IF NOT EXISTS` 不会补列；改 `CREATE TABLE` 只对新库生效，旧库会静默缺列。
- **怎么守**：新能力用新表（现有 `item_fingerprints`、`match_requests` 就是范例）；真要改列必须配迁移脚本。
- **怎么查**：`grep -rn "CREATE TABLE" --include=*.py db_manager.py matching/ state/` —— 只查应用代码，7 处全部应为 `CREATE TABLE IF NOT EXISTS`；`tests/` 里的裸 `CREATE TABLE` 是测试夹具，不在此列。

## 7. 配对方向：item1 = 拾获，item2 = 失物

- **为什么**：未匹配查询按这个方向 LEFT JOIN；写反会让已配对物品继续出现在候选里，且不报错。
- **怎么守**：所有写 `matches` 的代码都传 `(found, lost)`；读方向见 [data-model](data-model.md)。
- **怎么查**：`grep -rn "insert_match\|INSERT OR IGNORE INTO matches" --include=*.py .` —— 实参顺序都应是 (found, lost)。

## 8. 上传图片先去 EXIF，模型失败要降级

- **为什么**：照片可能带 GPS；模型权重可能没下载。任一失败都不该让整页崩溃。
- **怎么守**：`clean_image` 是唯一入库前入口；模型调用包在 `try/except` 里，失败给 `st.warning` 并允许手填。
- **怎么查**：`grep -rn "exif_transpose\|MAX_IMAGE_PIXELS" matching/models.py state/found.py`；`grep -n "except (ImportError" state/found.py`。

## 9. 请求只能由报告所有者发起

- **为什么**：否则任何人都能替别人"认领"或骚扰对方。
- **怎么守**：`create` 中 `requester != username` 必须抛 `PermissionError`，且 requester 由**物品归属表**推导，不由调用方传入。
- **怎么查**：`grep -n "PermissionError" matching/requests.py` —— 应恰好 1 处；跑 `pytest tests/test_matching.py::test_request_needs_mutual_confirmation`。

## 10. 提交前确认分支

- **为什么**：`main` 是用户确认过的状态；共享工作区的 HEAD 可能被别的终端切走。
- **怎么守**：提交命令链里用 `[ "$(git branch --show-current)" = dsh ] || exit 1` 守卫，不靠记忆。
- **怎么查**：`git branch --show-current` 必须是 `dsh`。

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：10 条不变量与可执行的 grep 检查。 |
