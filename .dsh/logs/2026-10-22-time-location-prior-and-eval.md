# 2026-10-22 — 时间/地点软先验 + 离线评估脚本

## 目标

收尾 P0 两项：

1. 让 `items.time` / `items.location` 参与排序，但只做**软先验**，不做硬过滤。
2. 提供一个可重复运行的评估脚本，输出 Recall@1/5、MRR，并对比软先验开关。

## 决策

- **不改 72/28 基础分**：`base = 0.72×semantic + 0.28×证据项` 原样保留。
- **软先验只加不减**：
  - 同地点 +0.02；
  - 时间接近最多 +0.03，按绝对天数、14 天半衰；
  - 缺失、空值、“未知/其他”地点一律 0，不扣分；
  - 最终 `score = clamp(base + time_bonus + loc_bonus, 0, 1)`。
- **最大 +0.05**：不足以单靠时间/地点翻掉一个证据全矛盾的候选；只是轻微抬升同地点/近日期的候选。
- **可关闭**：`rank_candidates(..., use_priors=False)` 用于评估对比；页面默认开启。
- **输出可解释**：每个候选多返回 `base_score` 与 `prior_bonus`；候选卡显示地点/日期，有加分时显示「时间/地点软先验 +x.xxx」。
- **评估用全部对侧报告**：`build_session(..., include_matched=True)` 只用于评估，避免已配对的历史样本被排除；实时匹配仍然只用未配对池。
- **评估默认用 4 对演示数据**：按 `seed_demo.SAMPLES` 的精确描述在 `items.db` 里找 id；支持 `--labels` 自定义 `[{"lost_id","found_id"}]`。

## 改了什么

- `matching/engine.py`：`TIME_PRIOR_WEIGHT=0.03`、`LOCATION_PRIOR_WEIGHT=0.02`、`TIME_DECAY_DAYS=14`、`NEUTRAL_LOCATIONS`；`rank_candidates` 新增 `query_time/query_location/use_priors`，输出 `base_score/prior_bonus`。
- `matching/workflow.py`：`build_session` 接收 `query_time/query_location/include_matched`；候选带 `time/location`；session 带查询时间/地点。
- `state/lost.py`、`state/found.py`、`state/notifications.py`：把查询物品的日期/地点传进会话。
- `state/interactive_match.py`：排序传软先验参数；候选卡显示地点/日期与加分；分数说明更新。
- `matching/notifications.py`：通知相关性计算也使用同一套软先验。
- 新增 `evaluate.py`：默认 4 对、`--labels`、`--verbose`、`--json`；同时输出 prior on/off。
- 新增 `tests/test_evaluate.py`；`tests/test_matching.py` 补软先验测试。
- 文档：matching-engine、architecture、data-model、ui、README、AGENTS、backlog、operations。

## 验证

- `pytest -q`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）→ **99 passed**。
- 真实评估（4 对演示数据）：

```text
prior=on   pairs=4  Recall@1=4/4  Recall@5=4/4  MRR=1.000  missed@1=0
  充电宝 0.561 / 水杯 0.565 / 键盘 0.554 / 鼠标 0.532
prior=off  pairs=4  Recall@1=4/4  Recall@5=4/4  MRR=1.000  missed@1=0
  充电宝 0.511 / 水杯 0.515 / 键盘 0.504 / 鼠标 0.482
```

- 软先验正好给每对 +0.05（同地点 +0.02、同日 +0.03），排序不变；关闭软先验后的分数与旧日志一致。
- `compileall` 通过；`check_links.py` 0 broken（最终计数见收尾验证）。

## 未做 / 留给后续

- 0.03/0.02/14 天未用真实数据校准；4 对样本只能做回归检查。
- 评估默认只覆盖“失物 → 拾获”方向；拾获 → 失物需要另外的标签。
- 地点只做精确字符串匹配，没有楼栋/楼层/相邻区域层级。
- 时间使用丢失/拾获日期，不是发布时间；迟到登记可能让时间先验失真。
- 本机工作副本没有 `.git` 且未安装 git，因此没有按 `dsh` 分支提交；改动只存在于工作区。
