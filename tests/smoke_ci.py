"""CI 冒烟测试：真实注册音色 + 真实合成语音，任何一步失败即构建失败。"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "onnx_runtime"))

from arktts_runtime.registration import VoiceRegistration  # noqa: E402
from arktts_runtime.runtime import ArkTtsRuntime  # noqa: E402

MODEL_DIR = ROOT / "onnx_runtime" / "model"


def make_reference_wav() -> bytes:
    """生成 2 秒 2kHz 正弦波作为参考音频（注册音色用）。"""
    rate = 44100
    t = np.arange(rate * 2) / rate
    audio = (0.3 * np.sin(2 * np.pi * 1200.0 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def main() -> None:
    manifest = json.loads((MODEL_DIR / "runtime_manifest.json").read_text())
    registration_manifest = json.loads(
        (MODEL_DIR / "registration" / "registration_manifest.json").read_text()
    )
    fingerprint = registration_manifest["model_fingerprint"]
    assert fingerprint == manifest["model_fingerprint"], "模型指纹不一致"

    with tempfile.TemporaryDirectory() as tmp:
        voices_dir = Path(tmp) / "voices"

        reg = VoiceRegistration(MODEL_DIR, voices_dir, fingerprint)
        assert reg.status()["available"], "注册 encoder 不可用"
        t0 = time.time()
        meta = reg.register(
            data=make_reference_wav(),
            filename="sine.wav",
            text="A simple test reference voice.",
            name="ci_voice",
            overwrite=True,
        )
        print(f"[ok] 音色注册成功: {meta['name']} ({time.time() - t0:.1f}s)")

        runtime = ArkTtsRuntime(MODEL_DIR, voices_dir)
        t0 = time.time()
        audio, codes = runtime.synthesize(
            text="你好，这是 Audio8 TTS 的 CI 冒烟测试。",
            voice="ci_voice",
            max_new_tokens=96,
            seed=42,
            threads=4,
        )
        elapsed = time.time() - t0
        sample_rate = int(runtime.manifest["sample_rate"])
        duration = audio.size / sample_rate

        assert codes.ndim == 2 and codes.shape[0] == int(runtime.manifest["num_codebooks"])
        assert audio.size > 0, "合成音频为空"
        assert audio.size / sample_rate > 0.3, "合成时长过短"
        assert np.isfinite(audio).all(), "合成音频含 NaN/Inf"

        out = Path(tmp) / "ci_output.wav"
        sf.write(str(out), audio, sample_rate)
        assert out.stat().st_size > 1000, "输出 wav 文件过小"

        print(f"[ok] 合成成功: {codes.shape[1]} 帧 / {duration:.2f}s / {elapsed:.1f}s")
        print(f"[ok] {sample_rate}Hz {audio.dtype} peak={np.abs(audio).max():.3f}")
        print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()