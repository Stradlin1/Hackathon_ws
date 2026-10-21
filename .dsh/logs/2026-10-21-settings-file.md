# 2026-10-21 把手工配置收进 settings.yaml

## 为什么

接入 DeepSeek 后，用户问「`DEEPSEEK_API_KEY` 存在哪个配置文件里」。答案是：**哪里都没存**——之前只有环境变量，`.env.example` 模板写了但没有任何代码去读它，复制成 `.env` 也不会生效。环境变量对"每次打开新终端"的演示不友好。

## 做了什么

- 新增 `matching/settings.py`：读仓库根目录的 `settings.yaml`，支持点号路径、布尔、数字；优先级 **环境变量 > 文件 > 默认值**。
- 新增 `settings.example.yaml` 模板；`settings.yaml` 进 `.gitignore`。
- `matching/vlm.py` 与 `matching/fingerprint.py` 改成从 settings 取值；环境变量仍然有效，方便临时覆盖。
- 删掉 `.env.example` 与 run.sh 里的 .env 加载——两种机制并存只会让人搞不清哪份生效。
- `run.sh` 增加 `python -m streamlit` 兜底：当前 shell 里没有 `streamlit` 可执行文件时不再直接 exit 127。

## 验证

- 新增 `tests/test_settings.py`（9 个用例）：缺文件回退默认、文件生效、环境变量覆盖、`enabled: false` 关掉集成、`off/false/0` 各种写法、YAML 解析失败被忽略、超时填垃圾回退默认。
- 端到端：写一份 `settings.yaml`（假 key 指向本地假 API），用 `./run.sh` 启动，上传 `input/水杯.jpg`，页面显示"由 DeepSeek 视觉模型识别"，假服务器收到 `model=deepseek-flash`。
- `pytest` 55 passed。

## 踩到的坑

- **YAML 把裸写的 `off` 读成布尔 `false`**：`fingerprint.text_model: off` 会让 `name.lower()` 直接 AttributeError。已在 `_load_generator` 里把非字符串值当"关闭"处理。
- **`./run.sh` 在未激活 conda 时 exit 127**：`streamlit` 不在 PATH。现在回退到 `python -m streamlit`，但 python 也必须是对的环境。

## 留下的

- `settings.yaml` 只在进程启动时读一次，改完要重启。
- 端口、HF 镜像等仍然走环境变量/命令行参数，没有收进 settings。
