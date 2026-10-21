# 2026-10-22 — 失物可选照片 + 文本/图像混合向量

## 目标

P1 第一项：失物登记也能上传照片；有照片时同时用文字和图像匹配，并让近期动态、我的记录、匹配候选显示失物照片。

## 决策

- **照片可选**：没有照片时只用文本向量，行为与之前完全一致。
- **不新增表/列**：照片存 `items.image`，混合向量存 `items.emb`；失物和拾获复用同一列。
- **混合方式**：`normalize(0.5 × text_embedding + 0.5 × image_embedding)`。两个编码器本来就在同一 CLIP 空间，加权平均后再归一化，`semantic_search` 仍然按余弦比较。
- **照片清洗**：`clean_image` 去 EXIF、缩放到最长边 1600、转 RGB；与拾获照片同一入口。
- **展示**：近期动态、我的记录、匹配候选在 `item.image` 非空时显示；没有照片就不显示。
- **不自动生成失物指纹**：失物照片只参与向量与展示；属性仍来自用户描述，避免模型读图凭空加属性。

## 改了什么

- `state/lost.py`：可选 `file_uploader`（png/jpg/jpeg，≤8 MB）、预览、EXIF 清洗；提交时 `encode_text` + 可选 `encode_image` → `combine_text_image`；`Item.image` 存照片。
- `matching/models.py`：新增 `combine_text_image()`（校验维度、归一化、拒绝无效向量）。
- `state/browse.py`：失物卡片也显示照片（原来只显示拾获）。
- `state/profile.py`：进行中/已处理的失物卡片也显示照片。
- 测试：`tests/test_matching.py` 混合向量；`tests/test_pages_smoke.py` 失物带照片提交。
- 文档：README、architecture、data-model、privacy、ui、report-and-feed、backlog、AGENTS、operations。

## 验证

- `pytest -q`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）→ **102 passed**。
- 真实模型检查（鼠标照片 + 失物描述）：
  - 文本/图像/混合向量都是 512 维；混合后范数 1.0；
  - `cos(combined, text)=0.7409`、`cos(combined, image)=0.8439`。
- 把鼠标照片挂到一条演示失物上：
  - 登记页出现「上传物品照片（可选）」；
  - 近期动态仍包含该失物描述，图片数量增加；
  - 「我的记录」的失物卡片显示照片。
- `compileall` 通过；链接检查在收尾验证。

## 未做 / 留给后续

- 0.5/0.5 混合权重未校准；演示失物默认没有照片，评估只覆盖文本路径。
- 失物照片可以从 feed 保存拾获照片再上传，制造虚假高相似度；与“照抄描述”同属认领验证要解决的问题。
- 失物照片不生成图注/属性，只用于向量与展示。
- 本机工作副本没有 `.git` 且未安装 git，因此没有按 `dsh` 分支提交；改动只存在于工作区。
