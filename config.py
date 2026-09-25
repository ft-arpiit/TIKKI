from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import pyautogui


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _json_dict(name: str, default: dict[str, str]) -> dict[str, str]:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("not an object")
        return {str(k).lower(): str(v) for k, v in value.items()}
    except (json.JSONDecodeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT

    tikki_name: str = os.getenv("TIKKI_NAME", "TIKKI")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    gemini_fallback_models: tuple[str, ...] = tuple(
        x.strip() for x in os.getenv(
            "GEMINI_FALLBACK_MODELS", "gemini-3.7-flash,gemini-3.6-flash"
        ).split(",") if x.strip()
    )
    gemini_max_retries: int = _int("GEMINI_MAX_RETRIES", 3)
    gemini_base_backoff: float = _float("GEMINI_BASE_BACKOFF", 0.5)

    screen_monitor: str = os.getenv("SCREEN_MONITOR", "primary")
    screen_max_width: int = _int("SCREEN_MAX_WIDTH", 1920)
    screen_max_height: int = _int("SCREEN_MAX_HEIGHT", 1080)
    screen_capture_scale: float = _float("SCREEN_CAPTURE_SCALE", 1.0)

    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    whisper_language: str = os.getenv("WHISPER_LANGUAGE", "en")
    whisper_cpu_threads: int = _int("WHISPER_CPU_THREADS", 12)

    sample_rate: int = _int("AUDIO_SAMPLE_RATE", 16000)
    audio_channels: int = _int("AUDIO_CHANNELS", 1)
    audio_chunk_seconds: float = _float("AUDIO_CHUNK_SECONDS", 0.25)
    max_listen_seconds: float = _float("AUDIO_MAX_LISTEN_SECONDS", 8.0)
    silence_seconds: float = _float("AUDIO_SILENCE_SECONDS", 1.0)
    start_rms: float = _float("AUDIO_START_RMS", 0.012)

    require_wake_word: bool = _bool("REQUIRE_WAKE_WORD", True)
    wake_word: str = os.getenv("WAKE_WORD", "tikki").strip().lower()

    tts_backend: str = os.getenv("TTS_BACKEND", "pyttsx3")
    tts_rate: int = _int("TTS_RATE", 185)
    tts_volume: float = _float("TTS_VOLUME", 0.9)
    tts_voice: str = os.getenv("TTS_VOICE", "")

    volume_step: float = _float("VOLUME_STEP", 0.05)

    pause_seconds: float = _float("PAUSE_SECONDS", 0.03)
    failsafe: bool = _bool("FAILSAFE", True)
    click_interval: float = _float("CLICK_INTERVAL", 0.03)
    max_type_chars: int = _int("MAX_TYPE_CHARS", 2000)
    max_scroll_units: int = _int("MAX_SCROLL_UNITS", 12)

    app_aliases: dict[str, str] = field(default_factory=lambda: _json_dict(
        "APP_ALIASES",
        {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "terminal": "wt.exe",
            "file explorer": "explorer.exe",
            "explorer": "explorer.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
        },
    ))

    def configure_pyautogui(self) -> None:
        pyautogui.PAUSE = max(0.0, self.pause_seconds)
        pyautogui.FAILSAFE = self.failsafe


settings = Settings()
settings.configure_pyautogui()
