"""一键包命令行合成入口：python run_cli.py --text "你好" --voice 音色名"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(ROOT))

import soundfile as sf  # noqa: E402

from arktts_runtime.runtime import ArkTtsRuntime  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Audio8 TTS 一键合成")
    parser.add_argument("--text", required=True, help="要合成的文本")
    parser.add_argument("--voice", required=True, help="音色名（先注册）")
    parser.add_argument("--output", type=Path, default=None, help="输出 wav 路径（默认 outputs/xxx.wav）")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=0, help="0=自动")
    args = parser.parse_args()

    model_dir = ROOT / "model"
    voices_dir = ROOT / "voices"
    if not (model_dir / "runtime_manifest.json").is_file():
        print("模型未初始化，请先运行 启动TUI.bat 或 init.py")
        raise SystemExit(1)

    import os

    threads = args.threads or max(2, os.cpu_count() or 4)
    runtime = ArkTtsRuntime(model_dir, voices_dir, threads=threads)
    audio, codes = runtime.synthesize(
        text=args.text,
        voice=args.voice,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        seed=args.seed,
    )
    out_dir = args.output or (ROOT / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.voice}_{args.seed}.wav"
    sf.write(str(out), audio, int(runtime.manifest["sample_rate"]))
    print(f"已生成: {out.resolve()}")


if __name__ == "__main__":
    main()