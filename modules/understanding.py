from __future__ import annotations

import json
import re
from typing import Any

from modules.command_schema import TikkiCommand
from modules.router import LocalRouter, RouteKind


class CommandUnderstanding:
    """
    Converts TIKKI input into the canonical TikkiCommand structure.

    Supports two input paths:

        Natural language -> deterministic router / regex -> TikkiCommand
        JSON             -> validation                 -> TikkiCommand
    """

    def __init__(self) -> None:
        self.router = LocalRouter()

    def understand(self, text: str | dict[str, Any]) -> TikkiCommand:

        # ---------------------------------------------------------
        # Structured JSON / dictionary command path
        # ---------------------------------------------------------

        if isinstance(text, dict):
            try:
                return TikkiCommand.model_validate(text)
            except ValueError:
                return TikkiCommand(
                    domain="unknown",
                    action="unknown",
                    operation="unknown",
                    original_text=json.dumps(text),
                    confidence=0.0,
                )

        # ---------------------------------------------------------
        # Normal text input
        # ---------------------------------------------------------

        normalized = " ".join(text.strip().split())
        normalized = normalized.rstrip(".,!?;:")
        normalized = re.sub(r"\bvoice\b", "volume", normalized, flags=re.I)

        # ---------------------------------------------------------
        # JSON string command path
        #
        # Allows:
        # {
        #   "domain": "audio",
        #   "action": "volume_set",
        #   "operation": "set",
        #   "parameters": {"value": 30}
        # }
        # ---------------------------------------------------------

        try:
            payload = json.loads(normalized)

            if isinstance(payload, dict):
                return TikkiCommand.model_validate(payload)

        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        if not normalized:
            return TikkiCommand(
                domain="unknown",
                action="unknown",
                operation="unknown",
                original_text=text,
                confidence=1.0,
            )

        # ---------------------------------------------------------
        # First: deterministic router
        # ---------------------------------------------------------

        intent = self.router.route(normalized)

        if intent.kind != RouteKind.UNKNOWN:
            return self._from_intent(intent)

        # ---------------------------------------------------------
        # Natural-language volume: SET
        # ---------------------------------------------------------

        value = self._extract_percentage(
            normalized,
            patterns=[
                r"(?:make|set|put)\s+(?:the\s+)?(?:my\s+)?(?:volume|sound)"
                r"\s+(?:to\s+|at\s+)?(\d{1,3})(?:\s*(?:%|percent))?",

                r"(?:make|set)\s+(?:the\s+)?(?:volume|sound)"
                r"\s+(?:to\s+|at\s+)?(\d{1,3})(?:\s*(?:%|percent))?",
            ],
        )

        if value is not None:
            return self._command(
                domain="audio",
                action="volume_set",
                operation="set",
                parameters={"value": value},
                original_text=normalized,
                confidence=0.96,
            )

        # ---------------------------------------------------------
        # Natural-language volume: UP
        # ---------------------------------------------------------

        if self._matches_any(
            normalized,
            [
                r"^(?:turn|make)\s+(?:the\s+)?(?:volume|sound)\s+(?:up|louder)$",
                r"^(?:increase|raise)\s+(?:the\s+)?(?:volume|sound)$",
                r"^(?:can\s+you\s+)?(?:turn|make)\s+(?:the\s+)?volume\s+up$",
            ],
        ):
            return self._command(
                domain="audio",
                action="volume_up",
                operation="increase",
                parameters={},
                original_text=normalized,
                confidence=0.96,
            )

        # ---------------------------------------------------------
        # Natural-language volume: DOWN
        # ---------------------------------------------------------

        if self._matches_any(
            normalized,
            [
                r"^(?:turn|make)\s+(?:the\s+)?(?:volume|sound)\s+(?:down|quieter)$",
                r"^(?:decrease|lower|reduce)\s+(?:the\s+)?(?:volume|sound)$",
                r"^(?:can\s+you\s+)?(?:turn|make)\s+(?:the\s+)?volume\s+down$",
            ],
        ):
            return self._command(
                domain="audio",
                action="volume_down",
                operation="decrease",
                parameters={},
                original_text=normalized,
                confidence=0.96,
            )

        # ---------------------------------------------------------
        # Natural-language brightness: SET
        # ---------------------------------------------------------

        value = self._extract_percentage(
            normalized,
            patterns=[
                r"(?:make|set|put)\s+(?:the\s+)?(?:brightness)"
                r"\s+(?:to\s+|at\s+)?(\d{1,3})(?:\s*%)?",
            ],
        )

        if value is not None:
            return self._command(
                domain="display",
                action="brightness_set",
                operation="set",
                parameters={"value": value},
                original_text=normalized,
                confidence=0.96,
            )

        # ---------------------------------------------------------
        # Natural-language brightness: UP
        # ---------------------------------------------------------

        if self._matches_any(
            normalized,
            [
                r"^(?:turn|make)\s+(?:the\s+)?brightness\s+(?:up|higher)$",
                r"^(?:increase|raise)\s+(?:the\s+)?brightness$",
            ],
        ):
            return self._command(
                domain="display",
                action="brightness_up",
                operation="increase",
                parameters={},
                original_text=normalized,
                confidence=0.96,
            )

        # ---------------------------------------------------------
        # Natural-language brightness: DOWN
        # ---------------------------------------------------------

        if self._matches_any(
            normalized,
            [
                r"^(?:turn|make)\s+(?:the\s+)?brightness\s+(?:down|lower)$",
                r"^(?:decrease|lower|reduce)\s+(?:the\s+)?brightness$",
            ],
        ):
            return self._command(
                domain="display",
                action="brightness_down",
                operation="decrease",
                parameters={},
                original_text=normalized,
                confidence=0.96,
            )

        # ---------------------------------------------------------
        # Unknown command
        # ---------------------------------------------------------

        return TikkiCommand(
            domain="unknown",
            action="unknown",
            operation="unknown",
            parameters={},
            original_text=normalized,
            confidence=0.2,
        )

    @staticmethod
    def _command(
        *,
        domain: str,
        action: str,
        operation: str,
        parameters: dict[str, Any],
        original_text: str,
        confidence: float,
    ) -> TikkiCommand:
        return TikkiCommand(
            domain=domain,
            action=action,
            operation=operation,
            parameters=parameters,
            original_text=original_text,
            confidence=confidence,
        )

    @staticmethod
    def _matches_any(text: str, patterns: list[str]) -> bool:
        return any(
            re.fullmatch(pattern, text, re.I)
            for pattern in patterns
        )

    @staticmethod
    def _extract_percentage(
        text: str,
        patterns: list[str],
    ) -> int | None:
        for pattern in patterns:
            match = re.fullmatch(pattern, text, re.I)

            if match:
                value = int(match.group(1))

                if not 0 <= value <= 100:
                    return None

                return value

        return None

    @staticmethod
    def _from_intent(intent) -> TikkiCommand:
        action = intent.action
        args = dict(intent.args or {})

        domain = "system"
        operation = "unknown"

        if action.startswith("volume_"):
            domain = "audio"

            if action == "volume_set":
                operation = "set"
            elif action == "volume_up":
                operation = "increase"
            elif action == "volume_down":
                operation = "decrease"
            elif action == "volume_mute":
                operation = "mute"
            elif action == "volume_unmute":
                operation = "unmute"

        elif action.startswith("brightness_"):
            domain = "display"

            if action == "brightness_set":
                operation = "set"
            elif action == "brightness_up":
                operation = "increase"
            elif action == "brightness_down":
                operation = "decrease"

        elif action == "launch_app":
            domain = "application"
            operation = "launch"

        elif action == "press_key":
            domain = "keyboard"
            operation = "press"

        elif action in {"copy", "paste", "undo", "redo"}:
            domain = "keyboard"
            operation = action

        elif action == "lock":
            domain = "system"
            operation = "lock"

        elif action == "show_desktop":
            domain = "system"
            operation = "show_desktop"

        elif intent.kind == RouteKind.VISION:
            domain = "vision"

        return TikkiCommand(
            domain=domain,
            action=action,
            operation=operation,
            parameters=args,
            original_text=intent.original_text,
            confidence=intent.confidence,
        )