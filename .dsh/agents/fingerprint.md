# 指纹（把自由文本压成可比较的结构化属性）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[匹配与追问](matching-engine.md) 消费这里的属性；[数据模型](data-model.md) 说明指纹如何落库。

**本文件状态：`【事实】`**——全部读自 `matching/fingerprint.py`（2026-10-21），未做行为改动。

## 属性集合与词表

- 【事实】六个字段，顺序固定：`FIELDS = ("category", "color", "material", "shape", "brand", "mark")`。
- 【事实】中英别名都在 `VOCAB`（category/color/material/shape/brand/mark 六个子表）。**闭集**：只有词表里的规范值才能从文本里抽出来；排序时用 `casefold()` 完全相等比较，没有同义词。
- 【设计】新增可识别品牌/颜色应只改 `VOCAB`，不要另建第二份识别词表——抽取与排序都读同一处。
- 【事实】规范值以英文存储（指纹 JSON、数据库、比较逻辑都不变）；界面通过 `VALUE_ZH` / `display_value()` 翻成中文。
- 【设计】**新增规范值时必须同时补 `VALUE_ZH`**，否则界面回退显示英文值。组合标记（如 `red sticker`）按「颜色 + 标记」拼成「红色贴纸」；词表外的自由文本（例如用户自填品牌）原样显示。

## 规则抽取（`extract_known`）

| 条件 | 行为 |
| --- | --- |
| 文本先 `.lower()` | 输出值一律小写 |
| ASCII 别名 | 词边界匹配 `(?<![a-z])alias(?![a-z])`：`key` 不命中 `keyboard`，`glass` 不命中 `glasses` |
| 中文别名 | 纯子串包含（`"耳机" in text`） |
| 同字段多个别名命中 | 取**最长别名**；长度相同则保留词表遍历中先出现的那个 |
| mark 否定句 | `没有特殊标记 / 无特殊标记 / no special marks` → 值置为 `no special mark` |
| mark 前 3 字符内有颜色 | 拼成 `<color> <mark>`，例如 `充电盒有红色贴纸` → `red sticker` |
| mark 颜色邻接的搜索窗口 | 标记位置前 15 字符，颜色别名必须**紧邻**（间隔 0–3 字符） |

- 【事实】mark 的颜色只取**紧邻**颜色，取整句主色会把"黑色包上有红色贴纸"错误压成 `black sticker`。
- 【事实】`no special mark` 是一个**真实值**，会参与比较：与"有标记"的候选比较产生矛盾（按 [matching-engine](matching-engine.md) 的权重表扣分），而不是中性。想中性只能不作答。

## 生成式提案的校验（`fingerprint_from_text`）

1. 【事实】描述取前 1000 字符、图注取前 500 字符；`observed = {**visual, **main}`，即**用户描述按字段覆盖图注**（不是整条覆盖）。
2. 【事实】生成器可以是注入的（测试）、`_load_generator()`（`generate=True`）或 `None`（`generate=False`，索引旧数据时用）。
3. 【事实】prompt 要求只抽取显式属性并输出 JSON；`_extract_json_object` 取第一个 `{` 到最后一个 `}` 之间的内容解析。
4. 【事实】逐字段校验提案，满足任一才接受：
   - 提案值不在 `UNKNOWN`（`"" / "unknown" / "none" / "n/a" / "未知" / "不详" / "不记得" / "不知道"` 等）；
   - 用 `extract_known(proposal)` 抽出的规范值**等于**已观测值 → 只把 `method` 标成 `generative_verified`，不改属性；
   - 该字段本来缺失、提案 ≤ 50 字符、且提案字面出现在 `description + ". " + caption` 里 → 才写入属性（支持词表外的品牌等开放词）。
5. 【事实】不满足就丢弃：与已观测值冲突的提案**不会覆盖**规则抽取结果（`tests/test_matching.py::test_fingerprint_rejects_hallucinated_attributes`）。
6. 【事实】`method` 取值：`generative_verified` / `vision_caption_rules`（有图注）/ `rules`。它只表示"是否有提案通过校验"，不表示数量。

## 文本生成器

- 【事实】环境变量 `FINGERPRINT_TEXT_MODEL`，默认 `google/flan-t5-small`；设为 `off`/`none`/`disabled` 关闭。
- 【事实】`_load_generator` 带 `lru_cache(maxsize=1)`；任何 `ImportError/OSError/RuntimeError/ValueError` 都被吞掉并返回 `None`（静默降级到规则抽取）。
- 【事实】生成调用 `max_new_tokens=112, do_sample=False, truncation=True`；异常同样被吞掉，返回空提案。

## 回答归一化（`normalize_answer`）

| 输入 | 结果 |
| --- | --- |
| 空白、`不记得`、`跳过`、`unknown`、`skip` 等 | `None` |
| mark：`没有特殊标记` / `无标记` / `no mark` | `no special mark` |
| mark：`没有划痕` / `没有贴纸` | `None`（当作跳过，不是"无标记"） |
| 能从文本识别出的字段 | 规范值 |
| mark 的其他内容 | 原文小写、截断到 80 字符 |
| brand 的 ASCII 自由文本（2–40 字符，允许空格/点/下划线/横线） | 小写原文 |
| color/shape/category 未识别 | `None`（**不猜**，页面提示"按跳过处理"） |
| 非六字段 | `ValueError("Unsupported attribute")` |

## 已知边界与坑

- 【事实】`keychain` 同时出现在 category（keys）与 mark 词表里，所以含它的句子会同时得到 `category=keys` 与 `mark=keychain`；排序时两个权重都参与。
- 【事实】`logo` 的中文别名是 `图案`，范围很宽，容易把普通装饰误判成特殊标记。
- 【事实】词表是闭集：`vintage`、`titanium` 之类没有别名，只能靠生成式提案 + 字面证据进入属性。
- 【事实】`extract_colors`（返回全句所有颜色）目前**没有调用方**：2026-10-21 全仓 `grep -rn "extract_colors" --include='*.py' .` 只有定义处。它是未使用工具，不要误以为主流程会用它。

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：词表规则、提案校验、method 语义、normalize 表、已知坑。 |
