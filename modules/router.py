from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from config import settings


class RouteKind(str, Enum):
    LOCAL = "local"
    VISION = "vision"
    UNKNOWN = "unknown"


class Intent(BaseModel):
    kind: RouteKind
    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    original_text: str


@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern[str]
    action: str


class LocalRouter:
    """Deterministic, dependency-light intent router.

    The router never calls a network service or language model.
    """

    def __init__(self) -> None:
        self.rules = [
            # ---------------------------------------------------------
            # Volume
            # ---------------------------------------------------------
            Rule(
                re.compile(
                    r"^(?:volume|sound)\s+(?:up|increase|louder)$",
                    re.I,
                ),
                "volume_up",
            ),
            Rule(
                re.compile(
                    r"^(?:volume|sound)\s+(?:down|decrease|quieter)$",
                    re.I,
                ),
                "volume_down",
            ),
            Rule(
                re.compile(
                    r"^(?:mute|mute volume|silence)$",
                    re.I,
                ),
                "volume_mute",
            ),
            Rule(
                re.compile(
                    r"^(?:unmute|restore sound)$",
                    re.I,
                ),
                "volume_unmute",
            ),

            # ---------------------------------------------------------
            # Brightness
            # ---------------------------------------------------------
            Rule(
                re.compile(
                    r"^(?:brightness)\s+(?:up|increase|higher)$",
                    re.I,
                ),
                "brightness_up",
            ),
            Rule(
                re.compile(
                    r"^(?:brightness)\s+(?:down|decrease|lower)$",
                    re.I,
                ),
                "brightness_down",
            ),

            # ---------------------------------------------------------
            # Windows
            # ---------------------------------------------------------
            Rule(
                re.compile(
                    r"^(?:alt[\s-]?tab|switch window|next window)$",
                    re.I,
                ),
                "alt_tab",
            ),
            Rule(
                re.compile(
                    r"^(?:lock|lock pc|lock computer)$",
                    re.I,
                ),
                "lock",
            ),
            Rule(
                re.compile(
                    r"^(?:show desktop|desktop)$",
                    re.I,
                ),
                "show_desktop",
            ),

            # ---------------------------------------------------------
            # Clipboard / editing
            # ---------------------------------------------------------
            Rule(
                re.compile(r"^(?:copy)$", re.I),
                "copy",
            ),
            Rule(
                re.compile(r"^(?:paste)$", re.I),
                "paste",
            ),
            Rule(
                re.compile(r"^(?:undo)$", re.I),
                "undo",
            ),
            Rule(
                re.compile(r"^(?:redo)$", re.I),
                "redo",
            ),
        ]

    def route(self, text: str) -> Intent:
        normalized = " ".join(text.strip().split())

        if not normalized:
            return Intent(
                kind=RouteKind.UNKNOWN,
                action="empty",
                original_text=text,
                confidence=1.0,
            )

        # ---------------------------------------------------------
        # Exact local rules
        # ---------------------------------------------------------
        for rule in self.rules:
            if rule.pattern.fullmatch(normalized):
                return Intent(
                    kind=RouteKind.LOCAL,
                    action=rule.action,
                    original_text=normalized,
                )

        # ---------------------------------------------------------
        # Relative volume control
        #
        # Examples:
        #   volume up 10
        #   volume down 15%
        #   increase volume by 10
        #   decrease sound by 5
        # ---------------------------------------------------------
        m = re.fullmatch(
            r"(?:volume|sound)\s+(up|increase|down|decrease)\s+"
            r"(?:by\s+)?(\d{1,3})(?:\s*%)?",
            normalized,
            re.I,
        )

        if m:
            direction = m.group(1).lower()
            amount = max(0, min(100, int(m.group(2))))

            action = (
                "volume_up"
                if direction in {"up", "increase"}
                else "volume_down"
            )

            return Intent(
                kind=RouteKind.LOCAL,
                action=action,
                args={"amount": amount},
                original_text=normalized,
            )

        # ---------------------------------------------------------
        # Exact volume percentage
        #
        # Supports:
        #   volume 50
        #   volume 50%
        #   set volume 50
        #   set volume 50%
        #   set volume to 50
        #   set volume to 50%
        # ---------------------------------------------------------
        m = re.fullmatch(
            r"(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})(?:\s*%)?",
            normalized,
            re.I,
        )

        if m:
            value = max(0, min(100, int(m.group(1))))

            return Intent(
                kind=RouteKind.LOCAL,
                action="volume_set",
                args={"value": value},
                original_text=normalized,
            )

        # ---------------------------------------------------------
        # Exact brightness percentage
        # ---------------------------------------------------------
        m = re.fullmatch(
            r"(?:set\s+)?brightness\s+(?:to\s+)?(\d{1,3})(?:\s*%)?",
            normalized,
            re.I,
        )

        if m:
            value = max(0, min(100, int(m.group(1))))

            return Intent(
                kind=RouteKind.LOCAL,
                action="brightness_set",
                args={"value": value},
                original_text=normalized,
            )

        # ---------------------------------------------------------
        # Application launching
        #
        # Examples:
        #   open Chrome
        #   launch Chrome
        #   start Chrome
        # ---------------------------------------------------------
        m = re.fullmatch(
            r"(?:open|launch|start)\s+(.+)",
            normalized,
            re.I,
        )

        if m:
            target = m.group(1).strip().lower()

            if target in settings.app_aliases:
                return Intent(
                    kind=RouteKind.LOCAL,
                    action="launch_app",
                    args={
                        "target": target,
                        "command": settings.app_aliases[target],
                    },
                    original_text=normalized,
                )

        # ---------------------------------------------------------
        # Google / web search
        #
        # Supports:
        #   search Google for OpenAI
        #   search for OpenAI
        #   Google search for OpenAI
        #   google OpenAI
        #   search google OpenAI
        # ---------------------------------------------------------
        search_patterns = [
            r"^search\s+(?:google\s+)?for\s+(.+)$",
            r"^search\s+google\s+(.+)$",
            r"^google\s+search\s+for\s+(.+)$",
            r"^google\s+(.+)$",
        ]

        for pattern in search_patterns:
            m = re.fullmatch(pattern, normalized, re.I)

            if m:
                query = m.group(1).strip()

                if query:
                    return Intent(
                        kind=RouteKind.LOCAL,
                        action="google_search",
                        args={"query": query},
                        original_text=normalized,
                        confidence=0.99,
                    )

        # ---------------------------------------------------------
        # Keyboard keys
        # ---------------------------------------------------------
        m = re.fullmatch(
            r"(?:press|hit)\s+(.+)",
            normalized,
            re.I,
        )

        if m:
            key = m.group(1).strip().lower()

            allowed_keys = {
                "enter",
                "esc",
                "escape",
                "tab",
                "space",
                "backspace",
                "delete",
                "home",
                "end",
                "up",
                "down",
                "left",
                "right",
            }

            if key in allowed_keys:
                return Intent(
                    kind=RouteKind.LOCAL,
                    action="press_key",
                    args={
                        "key": "esc" if key == "escape" else key,
                    },
                    original_text=normalized,
                )

        # ---------------------------------------------------------
        # Common screen-grounded verbs → visual agent
        # ---------------------------------------------------------
        vision_prefixes = (
            "click ",
            "double click ",
            "type ",
            "write ",
            "scroll ",
            "find ",
            "select ",
            "press the ",
            "open the ",
            "click the ",
        )

        if normalized.lower().startswith(vision_prefixes):
            return Intent(
                kind=RouteKind.VISION,
                action="visual_task",
                original_text=normalized,
                confidence=0.85,
            )

        # ---------------------------------------------------------
        # Unknown
        # ---------------------------------------------------------
        return Intent(
            kind=RouteKind.UNKNOWN,
            action="needs_reasoning",
            original_text=normalized,
            confidence=0.2,
        )