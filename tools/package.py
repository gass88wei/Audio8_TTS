"""把 onnx_runtime + 启动器 + TUI + 模型全量打成一键包 zip（模型若缺失则首次运行自动下载）。"""

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

MODEL_EXCLUDES = {".cache", ".gitkeep"}
BIG_EXTENSIONS = {".onnx", ".data"}


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


def ignore_junk(directory: str, names: list[str]) -> list[str]:
    skipped = [n for n in names if n == "__pycache__"]
    if Path(directory).name == "model":
        skipped += [n for n in names if n in MODEL_EXCLUDES]
    return skipped


def copy_tree_or_file(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_junk)
    else:
        shutil.copy2(src, dst)


def main() -> None:
    version = resolve_version()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"非法版本号: {version!r}")

    model_src = RUNTIME_SRC / "model"
    model_missing = not model_src.is_dir()

    staging = ROOT / "dist" / "staging" / f"Audio8TTS-{version}"
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "runtime").mkdir(parents=True)
    (staging / "model").mkdir()
    (staging / "voices").mkdir()

    for item in RUNTIME_SRC.iterdir():
        if item.name == "model":
            continue
        copy_tree_or_file(item, staging / "runtime" / item.name)

    if not model_missing:
        copy_tree_or_file(model_src, staging / "model")

    for item in ("tui_app.py", "init.py", "run_cli.py", "tui.tcss"):
        shutil.copy2(PACK_DIR / item, staging / item)

    shutil.copy2(PACK_DIR / "启动TUI.bat", staging)
    shutil.copy2(PACK_DIR / "一键合成.bat", staging)
    shutil.copy2(PACK_DIR / "requirements.txt", staging)
    shutil.copy2(PACK_DIR / "README.txt", staging)

    for pycache in staging.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)

    def archive_item(path: Path) -> None:
        arcname = path.relative_to(staging)
        compress = (
            zipfile.ZIP_STORED
            if path.suffix.lower() in BIG_EXTENSIONS
            else zipfile.ZIP_DEFLATED
        )
        zf.write(path, arcname, compress_type=compress)

    DIST_DIR.mkdir(exist_ok=True)
    zip_name = DIST_DIR / f"Audio8TTS-Win64-v{version}.zip"
    with zipfile.ZipFile(zip_name, "w") as zf:
        for path in sorted(staging.rglob("*")):
            archive_item(path)
    size_mb = zip_name.stat().st_size / 1024 / 1024
    print(f"packaged: {zip_name} ({size_mb:.2f} MiB, model={'missing' if model_missing else 'included'})")


if __name__ == "__main__":
    main()