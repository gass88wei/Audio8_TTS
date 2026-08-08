"""把 onnx_runtime + 启动器 + TUI 打成一键包 zip（模型不打包，首次运行自动下载）。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "pack"
DIST_DIR = ROOT / "dist"
RUNTIME_SRC = ROOT / "onnx_runtime"


def resolve_version() -> str:
    tag = os.environ.get("APP_VERSION", "")
    if tag.startswith("v"):
        return tag[1:]
    try:
        described = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True
        )
        if described.returncode == 0:
            return described.stdout.strip().lstrip("v")
    except OSError:
        pass
    return "0.1.0"


def main() -> None:
    version = resolve_version()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"非法版本号: {version!r}")

    staging = ROOT / "dist" / "staging" / f"Audio8TTS-{version}"
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "runtime").mkdir(parents=True)
    (staging / "model").mkdir()
    (staging / "voices").mkdir()

    for item in RUNTIME_SRC.iterdir():
        if item.name == "model":
            continue
        dst = staging / "runtime" / item.name
        (shutil.copytree(item, dst) if item.is_dir() else shutil.copy2(item, dst))

    for item in ("tui_app.py", "init.py", "run_cli.py", "tui.tcss"):
        shutil.copy2(PACK_DIR / item, staging / item)

    shutil.copy2(PACK_DIR / "启动TUI.bat", staging)
    shutil.copy2(PACK_DIR / "一键合成.bat", staging)
    shutil.copy2(PACK_DIR / "requirements.txt", staging)
    shutil.copy2(PACK_DIR / "README.txt", staging)

    for pycache in staging.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)

    DIST_DIR.mkdir(exist_ok=True)
    zip_name = DIST_DIR / f"Audio8TTS-Win64-v{version}.zip"
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(staging.rglob("*")):
            zf.write(path, path.relative_to(staging))
    print(f"packaged: {zip_name} ({zip_name.stat().st_size / 1024 / 1024:.2f} MiB)")


if __name__ == "__main__":
    main()