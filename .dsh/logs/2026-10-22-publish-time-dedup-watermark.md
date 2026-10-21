# 2026-10-22 — 发布时间置顶 + 内容指纹 + 图片/文本查重 + 水印

## 目标

用户担心“从 feed 保存拾获照片再上传成失物照片”制造虚假高相似度，要求：

1. 每个帖子显示发布时间；
2. 想办法让内容不可复制/图片不可保存。

## 决策

- **不假装能禁止复制**：浏览器截图、OCR、开发者工具、直接读本地 SQLite 都无法阻止。CSS 禁止选择/右键只能防顺手复制，不作为安全边界。
- **发布时间 + 内容指纹**：每个帖子底部显示「首次发布于：… · 内容指纹 …」。时间来自 `report_meta.published_at`；指纹是规范化描述的 SHA-256 前 10 位。显示在动态、我的记录、通知、候选卡。
- **图片 dHash 查重**：64-bit 感知哈希，Hamming ≤ 6 视为近似重复；上传时提示，不阻断。新表 `image_hashes`，撤销时删除。
- **文本近似**：规范化后 `SequenceMatcher`，长度 ≥ 12 且 ratio ≥ 0.92 提示；提交时写 `duplicate_notice`，匹配页显示一次。
- **公开图水印**：显示时加底部半透明条，写 `404NotFound · #帖子尾号 · 日期`；入库图片/向量/dHash 仍基于原图。
- **只提示不阻断**：误报/漏报都可能；让用户知情，而不是替用户判定归属。
- **不做 CSS/JS 禁止复制**：给不了安全保证，还会伤无障碍；需要时最多加一句“请勿截图传播”。

## 改了什么

- 新增 `matching/content_hash.py`：`text_fingerprint`、`image_dhash`、`hamming_distance`、`watermark`、`publication_text`、`find_similar_text`、`ImageHashes`。
- `state/lost.py` / `state/found.py`：上传时图片查重提示；提交时文本近似提示；入库后写 dHash。
- `state/browse.py` / `state/profile.py` / `state/notifications.py` / `state/interactive_match.py`：发布时间+内容指纹、水印。
- `state/profile._remove_report`：撤销时删除 dHash。
- `seed_demo.py`：为 4 张拾获照片写 dHash；当前演示库回填 6 张。
- 新增 `tests/test_content_hash.py`；页面烟测补 fake。
- 文档：新增 `.dsh/agents/anti-copy.md`，同步 README、architecture、data-model、privacy、ui、backlog、AGENTS、operations。

## 验证

- `pytest -q`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）→ **108 passed**。
- 真实数据：
  - 近期动态 9 条「首次发布于…内容指纹」；我的记录 7 条；通知 1 条。
  - 用 `demo/photos/鼠标.jpg` 查重：命中失物 `#942228599187412484` 与拾获 `#1517754286063885471`，距离都是 0。
  - 同一描述文本近似：`ratio=1.0`，命中对应帖子。
  - 页面文本不出现邮箱。
- `compileall` 通过；链接检查在收尾验证。

## 未做 / 留给后续

- 截图/保存无法禁止；水印被裁剪后无法追溯。
- dHash/文本阈值未用真实数据校准；换角度、强裁剪可能漏报，模板描述可能误报。
- 没有一次性交接码/线下核验；认领验证仍暂缓。
- 本地 `published_at` 与指纹可被有数据库权限的人修改，不是密码学证明。
- 本机工作副本没有 `.git` 且未安装 git，因此没有按 `dsh` 分支提交；改动只存在于工作区。
