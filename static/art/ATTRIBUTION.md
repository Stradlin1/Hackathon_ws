# 生成插图（static/art/）

本目录的插图由生图模型生成，供 Picture is All You Need 的界面与上台展示页使用。
做法与 pioneer-wiki 的插图流程一致。

- 许可：CC BY 4.0（与 pioneer-wiki 的插图相同）
- 模型：gpt-image-2.5-sunburst
- 提示词、生成时间与 license 逐条记录在 manifest.json；这里是裁切后的 webp（纸底已转透明），原始 PNG 不入库。
- 重新生成：python tools/generate_art.py --env-file <含 PW_IMAGE_API_KEY 的文件>，再运行 python tools/prepare_art.py。

| 文件 | 尺寸 | 字节 |
| --- | --- | --- |
| card-found.webp | 900x600 | 156096 |
| card-lost.webp | 900x600 | 148266 |
| empty-bell.webp | 900x600 | 84230 |
| empty-box.webp | 900x600 | 154302 |
| empty-search.webp | 900x600 | 141788 |
| fleuron.webp | 900x304 | 104656 |
| frontispiece.webp | 1200x800 | 571968 |
| mark.webp | 640x427 | 82420 |
| vector-plane.webp | 900x600 | 52756 |
