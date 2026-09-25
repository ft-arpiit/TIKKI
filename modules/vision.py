from __future__ import annotations

import io
import logging
import time
from typing import Any

from PIL import Image
from pydantic import BaseModel, Field
from mss import MSS

from config import settings

logger = logging.getLogger(__name__)


class VisualAction(BaseModel):
    type: str
    x: int | None = None
    y: int | None = None
    text: str | None = None
    amount: int | None = None
    keys: list[str] = Field(default_factory=list)
    seconds: float | None = None


class GroundingPlan(BaseModel):
    done: bool = False
    explanation: str = ""
    actions: list[VisualAction] = Field(default_factory=list)


class ScreenGrabber:
    def __init__(self) -> None:
        self.sct = MSS()

    def capture(self) -> Image.Image:
        monitor = self.sct.primary_monitor
        shot = self.sct.grab(monitor)
        image = shot.to_pil("RGB")
        scale = max(0.1, min(1.0, settings.screen_capture_scale))
        if scale != 1.0:
            image = image.resize(
                (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                Image.Resampling.LANCZOS,
            )
        return image


class VisualGrounder:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    @staticmethod
    def _prompt(task: str) -> str:
        return f"""
You are TIKKI's visual grounding component.
Task: {task}

Inspect the supplied Windows screenshot and return ONLY JSON matching the schema.
Coordinate origin is the screenshot's top-left. Use absolute screenshot pixel coordinates.
Rules:
- Prefer the smallest number of actions.
- Never invent coordinates if the target is not visible.
- Use click/double_click only when the target is visually identifiable.
- Use type only for text explicitly required by the task.
- Use hotkey only for common safe shortcuts.
- Maximum 12 actions.
- Do not use shell commands, PowerShell, registry edits, credential entry, security settings,
  destructive actions, or file deletion.
- If the task is already satisfied, set done=true and actions=[].
"""

    def _models(self) -> list[str]:
        return [settings.gemini_model, *settings.gemini_fallback_models]

    def ground(self, task: str, image: Image.Image) -> GroundingPlan:
        client = self._get_client()
        prompt = self._prompt(task)

        last_error: Exception | None = None
        for model in self._models():
            for attempt in range(settings.gemini_max_retries):
                try:
                    from google.genai import types
                    response = client.models.generate_content(
                        model=model,
                        contents=[prompt, image],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=GroundingPlan,
                            temperature=0,
                        ),
                    )
                    if not response.parsed:
                        raise ValueError("Model returned no parsed structured output.")
                    plan = GroundingPlan.model_validate(response.parsed)
                    self._validate_plan(plan)
                    return plan
                except Exception as exc:
                    last_error = exc
                    delay = settings.gemini_base_backoff * (2 ** attempt)
                    logger.warning(
                        "Vision model %s attempt %d failed: %s; retrying in %.2fs",
                        model, attempt + 1, exc, delay,
                    )
                    time.sleep(delay)

        raise RuntimeError(f"All visual grounding models failed: {last_error}") from last_error

    @staticmethod
    def _validate_plan(plan: GroundingPlan) -> None:
        if len(plan.actions) > 12:
            raise ValueError("Too many actions.")
        allowed = {"move", "click", "double_click", "type", "scroll", "hotkey", "wait"}
        safe_keys = {
            "ctrl", "shift", "alt", "win", "tab", "enter", "esc", "space",
            "backspace", "delete", "home", "end", "up", "down", "left", "right",
        }

        for action in plan.actions:
            if action.type not in allowed:
                raise ValueError(f"Unsupported visual action: {action.type}")
            if action.type in {"move", "click", "double_click"}:
                if action.x is None or action.y is None:
                    raise ValueError("Coordinate action missing x/y.")
            if action.type == "type" and len(action.text or "") > settings.max_type_chars:
                raise ValueError("Typed text exceeds safety limit.")
            if action.type == "scroll" and abs(action.amount or 0) > settings.max_scroll_units:
                raise ValueError("Scroll exceeds safety limit.")
            if action.type == "hotkey":
                if not action.keys or any(k.lower() not in safe_keys for k in action.keys):
                    raise ValueError("Unsafe hotkey.")
