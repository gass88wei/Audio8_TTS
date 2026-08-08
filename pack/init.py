"""一键包首次运行引导：自动补依赖、下载模型到包内 model/。

不硬编码任何绝对路径，全部相对本文件所在目录。
模型下载走 hf-mirror（国内镜像），可被 ARKTTS_HF_ENDPOINT 环境变量覆盖。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "model"
REQUIREMENTS = ROOT / "requirements.txt"
REPO_ID = "Audio8/Audio8-TTS-Preview-0.6B-ONNX-INT4"
MANIFEST = "runtime_manifest.json"


REQUIRED_IMPORTS = [
    "numpy",
    "onnxruntime",
    "soundfile",
    "scipy",
    "tokenizers",
    "huggingface_hub",
    "textual",
    "fastapi",
    "uvicorn",
    "pydantic",
    "multipart",
]


def need_pip_install() -> bool:
    import importlib

    missing = []
    for name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    if missing:
        print(f"[1/2] 缺少依赖: {', '.join(missing)}")
        return True
    return False


def install_deps() -> None:
    if not need_pip_install():
        print("[1/2] 依赖已就绪")
        return
    print("[1/2] 安装依赖（首次约 1-2 分钟，之后秒过）...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQUIREMENTS)]
    )


def ensure_model() -> None:
    if (MODEL_DIR / MANIFEST).is_file():
        print("[2/2] 模型已就绪")
        return
    print("[2/2] 下载模型（约 968 MiB，首次一次，之后离线使用）...")
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "huggingface_hub"]
        )
        from huggingface_hub import snapshot_download

    endpoint = os.environ.get("ARKTTS_HF_ENDPOINT", "https://hf-mirror.com")
    if endpoint:
        os.environ.setdefault("HF_ENDPOINT", endpoint)
    snapshot_download(
        repo_id=REPO_ID,
        local_dir=str(MODEL_DIR),
        local_dir_use_symlinks=False,
    )
    if not (MODEL_DIR / MANIFEST).is_file():
        raise SystemExit("模型下载失败：缺少 runtime_manifest.json，请检查网络后重试")


def main() -> None:
    print(f"包目录: {ROOT}")
    install_deps()
    ensure_model()
    print("初始化完成，可以正常使用了。")


if __name__ == "__main__":
    main()