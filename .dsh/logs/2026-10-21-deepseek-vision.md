# 2026-10-21 接入 DeepSeek 视觉模型

## 为什么

用户反馈：放一张水杯照片，系统说它是鼓风机。查下去发现，说错话的是 **BLIP**（图注），CLIP 只算相似度、不产出文字；规则再把 BLIP 的错误当类别用。

实测四张演示照片，BLIP 把充电宝说成 `a hand holding a white cell phone`，而同一张图上 CLIP 零样本分类给出"充电宝 3.58 / 手机 2.87"。结论：**看图说话这一环需要换更强的模型**，而不是换检索。

## 做了什么

- 新增 `matching/vlm.py`：调 DeepSeek 多模态对话接口（`deepseek-flash`，OpenAI 兼容格式），照片以 base64 data URL 传入，要求返回 json 的 `description` / `visible_text` / `attributes`。
- `state/found.py` 改成 **VLM 优先**：有 key 时用视觉模型的描述和图上文字；没 key、超时、HTTP 错误、JSON 不合法都回退本地 BLIP。
- 图上文字（型号、品牌、序列号）拼进描述，规则抽取就能拿到之前永远看不到的细节。
- 隐私说明随开关变化：开启时写"照片会发送到 DeepSeek API 一次"，关闭时写"不联网"。
- 新增 `.env.example`；只用标准库 `urllib`，没有引入 openai SDK，`requirements.txt` 未变。

## 验证

- 起了一个本地假 API（`/tmp/fake_vlm.py`），把 `DEEPSEEK_API_URL` 指过去，用无头 Chromium 上传 `input/水杯.jpg`：
  - 假服务器日志收到 `model=deepseek-flash`、含 image 块、`Bearer fake-key`；
  - 页面显示"由 DeepSeek 视觉模型识别"，描述被预填成假服务器返回的那句，并带"可见文字：FUGUANG"。
- 不设 key 时同一路径回退 BLIP，页面显示"由本地 BLIP 生成"。
- `pytest` 42 passed（新增 10 个用例：无 key、显式关闭、JSON 解析、失败回退、请求体形状）。

## 踩到的坑

- **旧进程占着 8599**：第一次验证连到的是没有环境变量的旧 Streamlit 进程，于是看到"没有用视觉模型"的假阴性。查了 `job_list` 才发现上一个测试服务器还在跑；杀掉重启后才对。
- **JSON Output 有硬性要求**：prompt 里必须出现 json 字样并给出结构示例，`max_tokens` 要够，否则可能被截断或返回空 content。代码里对空 content 已经返回 `None` 走回退。

## 留下的

- 真实 key 下的延迟与计费没有实测（本机没有 key），已写进 backlog。
- 不联网时仍只有 BLIP 的通用图注；本地 OCR 兜底还没做。
