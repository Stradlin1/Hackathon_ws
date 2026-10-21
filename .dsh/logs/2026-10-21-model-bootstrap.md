# 2026-10-21 — 模型权重与协作者首次启动

## 目标

用户指出：`models/opus-mt-en-zh/` 被 gitignore 后，其他协作者拿到项目还得自己拉模型。确认这个取舍，并把「自己拉」变成一条命令。

## 决策

模型权重**继续不入库**：

- 中译模型约 300 MB，BLIP/CLIP/flan-t5 合计约 2 GB；放进 git 会让 clone 变慢、历史膨胀，且权重更新与代码版本并不同步。
- Git LFS 需要额外配置与配额，对黑客松项目不划算。
- 正确做法是「权重不入库 + 一键下载脚本」，而不是把二进制塞进仓库。

## 做了什么

1. 新增 `download_models.py`
   - 默认 `HF_ENDPOINT=https://hf-mirror.com`（可用环境变量覆盖）。
   - 按 `allow_patterns` 只取 PyTorch 权重与配置，跳过 ONNX/OpenVINO。
   - 已缓存的文件直接复用；失败重试 3 次、退避 15/30 秒。
   - 若本地 `models/opus-mt-en-zh/` 已存在，中译模型直接跳过。
2. 新增 `run.sh`
   - `cd` 到仓库根目录；
   - 默认 `HF_HUB_OFFLINE=1`，启动 `streamlit run app.py`；
   - 额外参数原样透传（例如 `./run.sh --server.port 8502`）。
3. README 增加「5. 下载模型」与「6. 启动」，原来的流程顺延为 7；目录同步更新。
4. `AGENTS.md` 结构表、operations 的「协作者首次使用」记录这两个入口。
5. backlog 删除已完成的「把启动环境变量固化」。

## 协作者现在怎么做

```bash
python download_models.py   # 一次性，约 2.3 GB；走镜像；重复运行会跳过缓存
./run.sh                    # 日常启动，自动离线
```

不跑 `download_models.py` 也可以：应用在缺模型时会尝试从 HF 下载；但这依赖网络与镜像，不适合演示前临时赌。

## 验证

- `python download_models.py` 在已缓存环境运行：4 个 HF 模型显示 `ok`，中译模型显示 `skip (local ...)`，没有重复下载。
- `bash -n run.sh` 与 `py_compile download_models.py` 通过。
- `pytest` → **25 passed**。
- `check_links.py` → 0 broken（README 目录已同步新编号）。

## 未做（明确留给后续）

- 没有把权重放进 Git LFS 或共享网盘；协作者首次仍需联网约 2.3 GB。
- `run.sh` 不负责激活 conda；需要先 `conda activate aquacore`。
- 中译质量仍是机翻水平，另见 backlog。
