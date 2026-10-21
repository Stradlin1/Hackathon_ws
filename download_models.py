"""Download all model weights used by the app (run once on a new machine).

    python download_models.py

Weights are deliberately not stored in git. The script uses the HF mirror by
default; pass HF_ENDPOINT to override. It is safe to re-run: cached files are
reused.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

from huggingface_hub import snapshot_download  # noqa: E402

LOCAL_TRANSLATION = Path(__file__).resolve().parent / 'models' / 'opus-mt-en-zh'
MODELS = {
    'Salesforce/blip-image-captioning-base': ['*.json', '*.txt', '*.bin'],
    'sentence-transformers/clip-ViT-B-32': [
        '*.json', '*.txt', '*.bin', '*.safetensors', '*.model', '*.spm',
    ],
    'sentence-transformers/clip-ViT-B-32-multilingual-v1': [
        '*.json', '*.txt', '*.bin', '*.safetensors', '*.model', '*.spm',
    ],
    'google/flan-t5-small': ['*.json', '*.txt', '*.model', '*.bin', '*.safetensors'],
    'Helsinki-NLP/opus-mt-en-zh': [
        '*.json', '*.txt', '*.model', '*.spm', '*.bin', '*.safetensors',
    ],
}


def fetch(name: str, patterns: list[str]) -> None:
    if name == 'Helsinki-NLP/opus-mt-en-zh' and (LOCAL_TRANSLATION / 'config.json').exists():
        print(f'skip     {name} (local: {LOCAL_TRANSLATION})')
        return
    for attempt in range(1, 4):
        try:
            path = snapshot_download(name, allow_patterns=patterns)
            print(f'ok       {name} -> {path}')
            return
        except Exception as exc:  # network/rate-limit errors: retry with backoff
            if attempt == 3:
                raise
            print(f'retry {attempt} {name}: {type(exc).__name__}')
            time.sleep(15 * attempt)


def main() -> None:
    print(f'HF_ENDPOINT={os.environ["HF_ENDPOINT"]}')
    for name, patterns in MODELS.items():
        fetch(name, patterns)
    print('完成。之后可以用 ./run.sh 离线启动。')


if __name__ == '__main__':
    main()
