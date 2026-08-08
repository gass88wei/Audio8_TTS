"""Audio8 TTS 本地一键包 TUI（Textual）。

用法：python tui_app.py   （自动使用包内 model/ 与 voices/）
功能：合成语音 / 管理音色 / 注册新音色（复制声音克隆）
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "runtime"))

from arktts_runtime.registration import VoiceRegistration
from arktts_runtime.runtime import ArkTtsRuntime

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Log,
    OptionList,
    Static,
    TextArea,
)
from textual.widgets.option_list import Option

MODEL_DIR = ROOT / "model"
VOICES_DIR = ROOT / "voices"
OUTPUT_DIR = ROOT / "outputs"


class RegisterModal(ModalScreen):
    """注册音色对话框：wav 文件 + 原文 + 音色名。"""

    BINDINGS = [Binding("escape", "dismiss_modal", "取消")]

    def compose(self) -> ComposeResult:
        yield Static("注册新音色（复制声音）", id="modal-title")
        yield Input(placeholder="wav 文件完整路径（0.5-30 秒）", id="reg-file", classes="reg-in")
        yield Input(placeholder="该录音的准确原文", id="reg-text", classes="reg-in")
        yield Input(placeholder="音色名（英文/数字）", id="reg-name", classes="reg-in")
        yield Horizontal(
            Button("注册", id="reg-ok", variant="success"),
            Button("取消", id="reg-cancel", variant="error"),
            classes="reg-btns",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reg-cancel":
            self.dismiss(None)
            return
        if event.button.id == "reg-ok":
            file_in = self.query_one("#reg-file", Input)
            text_in = self.query_one("#reg-text", Input)
            name_in = self.query_one("#reg-name", Input)
            self.dismiss(
                {
                    "file": file_in.value.strip(),
                    "text": text_in.value.strip(),
                    "name": name_in.value.strip(),
                }
            )


class TTSApp(App):
    TITLE = "Audio8 TTS 本地版"
    CSS_PATH = "tui.tcss"
    BINDINGS = [
        Binding("ctrl+n", "open_register", "注册音色"),
        Binding("ctrl+r", "refresh_voices", "刷新音色"),
        Binding("ctrl+s", "synthesize", "合成"),
        Binding("ctrl+q", "quit", "退出"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.runtime: ArkTtsRuntime | None = None
        self.runtime_lock = threading.Lock()
        self.selected_voice: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(classes="main-grid"):
            with VerticalScroll(id="voice-column"):
                yield Static("音色列表", classes="section-title")
                yield Button("刷新 / 新建音色", id="btn-voices", classes="toolbar")
                yield OptionList(id="voice-list")
            with VerticalScroll():
                yield Static("文本 (Ctrl+S 合成)", classes="section-title")
                yield TextArea("你好，这里是语音合成测试。", id="text-area")
                with VerticalScroll(id="param-panel"):
                    yield Input(value="512", placeholder="max-new-tokens", id="p-tokens", classes="param")
                    yield Input(value="0.7", placeholder="temperature", id="p-temp", classes="param")
                    yield Input(value="0.9", placeholder="top-p", id="p-top-p", classes="param")
                    yield Input(value="50", placeholder="top-k", id="p-top-k", classes="param")
                    yield Input(value="42", placeholder="seed", id="p-seed", classes="param")
                yield Horizontal(
                    Button("合成", id="btn-synth", variant="primary"),
                    Button("播放", id="btn-play", variant="default"),
                    Button("打开输出目录", id="btn-outdir", variant="default"),
                    classes="action-row",
                )
                yield Static("状态", classes="section-title")
                yield Log(id="log-view", highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        self.log_line(f"模型: {MODEL_DIR}")
        self.log_line(f"音色目录: {VOICES_DIR}")
        self.check_runtime()

    # ---------- 工具 ----------

    def log_line(self, text: str) -> None:
        self.query_one("#log-view", Log).write_line(text)

    def _load_runtime(self) -> ArkTtsRuntime:
        """带锁加载模型，避免多线程重复加载。"""
        with self.runtime_lock:
            if self.runtime is None:
                threads = max(2, os.cpu_count() or 4)
                self.call_from_thread(self.log_line, "加载模型（首次约几秒）...")
                self.runtime = ArkTtsRuntime(MODEL_DIR, VOICES_DIR, threads=threads)
                self.call_from_thread(self.log_line, "模型已加载")
        return self.runtime

    def check_runtime(self) -> None:
        if not (MODEL_DIR / "runtime_manifest.json").is_file():
            self.log_line("提示：模型未初始化，请先运行 init.py 下载模型")
        self.refresh_voices()

    def refresh_voices(self) -> None:
        if not VOICES_DIR.is_dir():
            self.log_line("暂无音色。按 Ctrl+N 注册一个。")
            return
        names = sorted(
            p.name for p in VOICES_DIR.iterdir() if (p / "meta.json").is_file()
        )
        option_list = self.query_one("#voice-list", OptionList)
        option_list.clear_options()
        if names:
            option_list.add_options([Option(id=name, prompt=name) for name in names])
            if self.selected_voice in names:
                try:
                    option_list.highlight_option(self.selected_voice or "")
                except ValueError:
                    pass

    # ---------- 事件 ----------

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.selected_voice = str(event.option.prompt)
        self.log_line(f"已选择音色: {self.selected_voice}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-voices":
            self.refresh_voices()
        elif button_id == "btn-synth":
            self.synthesize()
        elif button_id == "btn-play":
            self.play_last()
        elif button_id == "btn-outdir":
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(str(OUTPUT_DIR))  # noqa: S606

    # ---------- 动作 ----------

    def action_register_voice(self) -> None:
        self.push_screen(RegisterModal(), self.on_register_result)

    def on_register_result(self, data: dict | None) -> None:
        if not data:
            return
        self.register_voice(data)

    @work(exclusive=False, thread=True)
    def register_voice(self, data: dict) -> None:
        try:
            runtime = self._load_runtime()
            manifest = runtime.manifest
            fp = manifest["model_fingerprint"]
            reg = VoiceRegistration(MODEL_DIR, VOICES_DIR, fp)
            state = reg.status()
            if not state["available"]:
                self.call_from_thread(
                    self.log_line,
                    f"注册不可用: {state['reason']}\n请确认模型已下载完整（含 registration/）",
                )
                return
            path = Path(data["file"])
            if not path.is_file():
                self.call_from_thread(self.log_line, f"文件不存在: {path}")
                return
            meta = reg.register(
                data=path.read_bytes(),
                filename=path.name,
                text=data["text"],
                name=data["name"],
                overwrite=False,
            )
            self.call_from_thread(self.refresh_voices)
            self.call_from_thread(self.log_line, f"音色注册成功: {meta['name']}")
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(self.log_line, f"注册失败: {exc}")

    def action_refresh_voices(self) -> None:
        self.refresh_voices()

    def action_synthesize(self) -> None:
        self.synthesize()

    @work(exclusive=False, thread=True)
    def do_synthesize(self, text: str, voice: str, params: dict) -> None:
        try:
            self.call_from_thread(self.log_line, f"合成中: {voice} / {len(text)} 字")
            runtime = self._load_runtime()
            params.setdefault("max_new_tokens", 512)
            audio, codes = runtime.synthesize(
                text=text,
                voice=voice,
                max_new_tokens=int(params["max_new_tokens"]),
                temperature=float(params.get("temperature", 0.7)),
                top_p=float(params.get("top_p", 0.9)),
                top_k=int(params.get("top_k", 50)),
                seed=int(params.get("seed", 42)),
            )
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out = OUTPUT_DIR / f"{voice}_{params.get('seed', 42)}.wav"
            import soundfile as sf

            sf.write(str(out), audio, int(runtime.manifest["sample_rate"]))
            self.call_from_thread(
                self.log_line,
                f"已保存: {out} ({audio.size / int(runtime.manifest['sample_rate']):.1f}s)",
            )
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(self.log_line, f"合成失败: {exc}")

    def synthesize(self) -> None:
        if not self.selected_voice:
            self.notify("请先在左侧选择一个音色（Ctrl+R 刷新）", severity="error", timeout=4)
            return
        text_widget = self.query_one("#text-area", TextArea)
        text = text_widget.text or ""
        if not text.strip():
            self.notify("请输入文本", severity="error", timeout=4)
            return
        params = {
            "max-new-tokens": int(self.query_one("#p-tokens", Input).value or 512),
            "temperature": float(self.query_one("#p-temp", Input).value or 0.7),
            "top_p": float(self.query_one("#p-top-p", Input).value or 0.9),
            "top_k": int(self.query_one("#p-top-k", Input).value or 50),
            "seed": int(self.query_one("#p-seed", Input).value or 42),
        }
        self.do_synthesize(text.strip(), self.selected_voice, params)

    def play_last(self) -> None:
        if not OUTPUT_DIR.is_dir():
            self.notify("还没有生成的音频")
            return
        wavs = sorted(OUTPUT_DIR.glob("*.wav"))
        if not wavs:
            self.notify("还没有生成的音频")
            return

        def _play() -> None:
            import winsound

            winsound.PlaySound(str(wavs[-1]), winsound.SND_FILENAME)

        threading.Thread(target=_play, daemon=True).start()
        self.log_line(f"播放: {wavs[-1].name}")


if __name__ == "__main__":
    TTSApp().run()