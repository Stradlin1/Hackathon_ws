# 2026-10-21 — 图片描述慢与 BLIP 加载失败

## 目标

用户上传照片时，图片描述生成很慢，随后报：

```text
自动图片描述不可用（Can't load image processor for 'Salesforce/blip-image-captioning-base' ...
preprocessor_config.json）。请手动描述物品。
```

查清是网络、缓存还是模型设备的问题，并让首次之外的加载不再卡住。

## 结论

三个原因叠加：

1. **huggingface.co 不可达**：本机 `huggingface.co:443` 连接超时，`hf-mirror.com` 返回 200。
2. **缓存不完整**：第一次下载被中断，BLIP 的 snapshot 一度缺少 `preprocessor_config.json`；即使后来补齐，`from_pretrained` 仍会向 huggingface.co 发 HEAD 并重试 5 次，卡住 30 秒以上。
3. **BLIP 跑在 CPU**：`_image_captioner()` 只做了 `from_pretrained`，从没 `.to("cuda")`，尽管本机 RTX 5070 可用。

## 做了什么

1. `matching/models.py`
   - 新增 `_sentence_transformer()`：先 `local_files_only=True` 读缓存，失败才联网。
   - BLIP 同样本地优先；加载后 CUDA 可用则 `.to("cuda")`，输入张量跟随模型设备。
2. `matching/fingerprint.py`
   - 文本生成器改为**先加载 tokenizer/model**（本地优先），再交给 `pipeline`，避免把 `local_files_only` 传进 `generate`。
   - CUDA 可用时 `device=0`。
3. 用 `hf-mirror.com` 补齐缓存：BLIP、CLIP 图像塔、CLIP 多语言文本塔、flan-t5-small（只取 PyTorch 权重，跳过 ONNX/OpenVINO）。
4. README / operations 增加镜像与离线启动说明。

## 关键证据

- `curl https://huggingface.co` → 5 秒后连接超时；`curl https://hf-mirror.com` → HTTP 200。
- 缓存完整后，BLIP 本地加载实测：
  - `device: cuda:0`
  - 模型加载：**9.01 s**
  - 首次图注：**2.74 s**
  - 第二次图注：**0.16 s**（800×800 图）
- CLIP 图像编码器：`device: cuda:0`，加载 **8.22 s**。
- CLIP 多语言文本塔：加 `HF_HUB_OFFLINE=1` 后加载 **0.7 s**；不加时 `local_files_only=True` 仍会卡 45 秒以上（子模块发 HEAD）。
- flan-t5-small：加载 **3.21 s**，32 token 推理 **5.51 s**（首次，含预热）。

## 中途改正过的地方

- 第一版把 `local_files_only=True` 直接传给 `pipeline(...)`。它能加载，但该参数被塞进 `model_kwargs`，推理时 `generate` 抛 `ValueError: model_kwargs ... ['local_files_only']`。改为先 `AutoTokenizer/AutoModelForSeq2SeqLM` 本地加载，再构造 pipeline。
- 最初只靠 `local_files_only`，CLIP 文本塔仍会卡；补了 `HF_HUB_OFFLINE=1` 的运行约定。
- 后台下载一开始拉全量 snapshot，把 ONNX/OpenVINO 也算进去；中断后用 `allow_patterns` 只取 PyTorch 权重与配置。

## 验证

- `pytest` → **24 passed**；`compileall` 通过。
- BLIP / CLIP 图像塔 / CLIP 文本塔 / flan-t5 均能从本地缓存加载并按预期使用 GPU。
- `streamlit run` 的登录页 AppTest 仍无异常（本次未改 UI 逻辑）。

## 未做（明确留给后续）

- 没有用真实物品照片跑完整「上传 → 图注 → 检索 → 追问 → 请求」；目前只验证了单模型加载与推理。
- 没有清理第一次中断留下的 BLIP `.incomplete` 大文件（约 975 MB，不被加载使用，磁盘足够）。
- 没有把 `HF_ENDPOINT` 写进代码；首次下载仍需在启动命令里设置，之后用 `HF_HUB_OFFLINE=1`。
- 未合并 `main`。
