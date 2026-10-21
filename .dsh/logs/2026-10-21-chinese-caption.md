# 2026-10-21 — 图注自动中译（BLIP → opus-mt-en-zh）

## 目标

拾获照片的图注由 BLIP 生成，是英文。希望上传后直接得到中文描述，而不是让用户先看英文再手改。

## 方案

BLIP 只做英文 caption，不换模型；在后面接一个轻量英中翻译模型：

```text
照片 → BLIP → 英文图注 → opus-mt-en-zh → 中文图注 → 填进「物品描述」
```

选择 `Helsinki-NLP/opus-mt-en-zh`（约 300 MB，MarianMT）而不是中文 caption 模型的理由：

- 现有 BLIP 流程、缓存、GPU 加载都不用动；
- 中文 caption 模型缺少可靠的小模型，Qwen-VL 这类又太大；
- 短图注的机翻质量足够做初稿，用户仍可在表单里改。

## 做了什么

1. `matching/models.py`
   - 新增 `_caption_translator()`：本地 `models/opus-mt-en-zh/` 优先，缺失才联网；CUDA 可用时上 GPU。
   - 新增 `translate_caption()`：把 BLIP 英文图注翻成中文；失败时原样返回英文，不影响提交。
   - `caption_image()` 现在返回中文；同时把 `a close up of` 预替换成 `a photo of`，并去掉译文开头的 `a.` / `a `。
2. `requirements.txt` 增加 `sacremoses`（Marian 分词器的标点规范化依赖）。
3. 从 `hf-mirror.com` 下载模型到 `models/opus-mt-en-zh/`（`/models/` 已 gitignore，不入库）。
4. `tests/test_matching.py` 增加中译失败回退英文的测试。

## 下载踩坑

- 先用 `snapshot_download` 下载，`hf-mirror.com` 返回 **429 Too Many Requests**（shared quota）。
- 直接 `curl` 小文件可以；`pytorch_model.bin` 第一次不带 `?download=true` 卡在 0 字节。
- 改成：
  `https://hf-mirror.com/Helsinki-NLP/opus-mt-en-zh/resolve/main/pytorch_model.bin?download=true`
  后 23 秒下完 297 MB。

## 实测译文

| 照片 | 中文图注 |
| --- | --- |
| 充电宝 | 握着白色手机的手 |
| 水杯 | 绿色的杯子,绿色的盖子和白的盖子 |
| 键盘 | 带有白色键盘封面的计算机键盘 |
| 鼠标 | 一张黑色表面白电脑鼠标的照片 |

- 第一张包含 BLIP 加载与翻译器加载，约 2.45 s；之后每张约 0.2–0.4 s。
- 中文已经可用，但质量是机翻水平：充电宝被 BLIP 认成手机、鼠标译文少了「色」、水杯译文重复。**提交前仍需人工看一眼**。

## 验证

- `pytest` → **25 passed**（新增中译回退测试）。
- 4 张 `input/` 照片均能返回中文图注。
- 模型文件只在本地 `models/` 下，未进入 git。

## 未做（明确留给后续）

- 没有换更好的中文 caption 模型；机翻误译仍在 backlog。
- 没有在 UI 里完整走一遍「上传 → 中文图注 → 提交」；只测了 `caption_image`。
- 换机器/清缓存后需要重新下载中译模型；缺失时图注会回退英文。
