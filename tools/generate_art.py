#!/usr/bin/env python3
"""Generate the archive plates used by the interface and the stage page.

The image model is any gateway that speaks the OpenAI image API
(`POST {base}/v1/images/generations`, returning `data[0].b64_json` or
`data[0].url`). Configuration comes from the environment, or from an
`.env`-style file passed with `--env-file`.

The key is read into memory only: it is never written to the repository, the
manifest or an error message. Point `--env-file` at the local pioneer-wiki
file when generating on this machine:

    python tools/generate_art.py \
        --env-file ../NEUP_protests/pioneer-wiki/.env.local

Prompts live in `tools/art-prompts.json`. Raw PNGs land in
`static/art/src/` (gitignored); `tools/prepare_art.py` cuts the paper ground
to alpha afterwards. Results are recorded in `static/art/manifest.json`.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "tools" / "art-prompts.json"
MANIFEST = ROOT / "static" / "art" / "manifest.json"
LICENSE = "CC BY 4.0"
TIMEOUT = 300
ATTEMPTS = 3

_print_lock = threading.Lock()
_manifest_lock = threading.Lock()
_queue_lock = threading.Lock()


def log(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def read_env_file(path: Path) -> dict:
    """Parse KEY = value lines, tolerating spaces around the sign as the local file has them."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def endpoint(base: str) -> str:
    base = base.rstrip("/")
    return f"{base}/images/generations" if base.endswith("/v1") else f"{base}/v1/images/generations"


def generate_one(job: dict, base: str, key: str, model: str, out_dir: Path) -> bool:
    target = out_dir / Path(job["out"]).name
    body = {
        "model": model,
        "prompt": job["prompt"],
        "quality": job.get("quality", "high"),
        "n": 1,
    }
    if job.get("size") and job["size"] != "auto":
        body["size"] = job["size"]

    for attempt in range(1, ATTEMPTS + 1):
        started = time.time()
        try:
            request = urllib.request.Request(
                endpoint(base),
                data=json.dumps(body).encode("utf-8"),
                headers={"content-type": "application/json", "authorization": f"Bearer {key}"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            item = (payload.get("data") or [{}])[0]
            if item.get("b64_json"):
                blob = base64.b64decode(item["b64_json"])
            elif item.get("url"):
                with urllib.request.urlopen(item["url"], timeout=TIMEOUT) as image:
                    blob = image.read()
            else:
                raise RuntimeError(f"no image in response: {json.dumps(payload)[:180]}")

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
            record(job, target, model, payload)
            log(f"ok   {target.relative_to(ROOT)}  {len(blob) // 1024} KB  {time.time() - started:.0f}s")
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, ValueError) as error:
            detail = str(error).replace(key, "***") if key else str(error)
            log(f"fail {job['slug']}  attempt {attempt}/{ATTEMPTS}: {detail[:180]}")
            time.sleep(4 * attempt)
    log(f"gave up on {job['slug']}; existing file (if any) was left untouched")
    return False


def record(job: dict, target: Path, model: str, payload: dict) -> None:
    with _manifest_lock:
        entries = []
        if MANIFEST.exists():
            try:
                entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                entries = []
        entries = [entry for entry in entries if entry.get("slug") != job["slug"]]
        item = (payload.get("data") or [{}])[0]
        entries.append({
            "slug": job["slug"],
            "file": "/" + str(target.relative_to(ROOT)).replace("\\", "/"),
            "model": model,
            "prompt": job["prompt"],
            "license": LICENSE,
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "generationId": item.get("generation_id", ""),
            "bytes": target.stat().st_size,
        })
        entries.sort(key=lambda entry: entry["slug"])
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, help="dotenv-style file with PW_IMAGE_BASE_URL / PW_IMAGE_API_KEY / PW_IMAGE_MODEL")
    parser.add_argument("--only", help="comma-separated slugs to regenerate")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "static" / "art" / "src")
    args = parser.parse_args(argv)

    config = read_env_file(args.env_file) if args.env_file else {}
    base = os.environ.get("PW_IMAGE_BASE_URL") or config.get("PW_IMAGE_BASE_URL", "")
    key = os.environ.get("PW_IMAGE_API_KEY") or config.get("PW_IMAGE_API_KEY", "")
    model = os.environ.get("PW_IMAGE_MODEL") or config.get("PW_IMAGE_MODEL", "gpt-image-2")
    if not base or not key:
        print("Set PW_IMAGE_BASE_URL and PW_IMAGE_API_KEY (or pass --env-file).", file=sys.stderr)
        return 1

    jobs = json.loads(JOBS.read_text(encoding="utf-8"))
    if args.only:
        wanted = {slug.strip() for slug in args.only.split(",")}
        jobs = [job for job in jobs if job["slug"] in wanted]
    if not jobs:
        print("No jobs selected.", file=sys.stderr)
        return 1

    log(f"generating {len(jobs)} plate(s) with {model} via {endpoint(base)}")
    queue = list(jobs)
    failures: list[str] = []

    def worker() -> None:
        while True:
            with _queue_lock:
                if not queue:
                    return
                job = queue.pop(0)
            if not generate_one(job, base, key, model, args.out_dir):
                with _queue_lock:
                    failures.append(job["slug"])

    threads = [
        threading.Thread(target=worker, daemon=True)
        for _ in range(max(1, min(args.concurrency, len(queue))))
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    if failures:
        print(f"failed: {', '.join(failures)}", file=sys.stderr)
        return 1
    print(f"done; manifest at {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
