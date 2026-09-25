from __future__ import annotations

from modules.command_schema import TikkiCommand
from modules.router import Intent


class CommandBridge:
    """
    Converts the existing router Intent into TIKKI's
    canonical structured-command format.
    """

    @staticmethod
    def from_intent(intent: Intent) -> TikkiCommand:
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

        elif action.startswith("launch_"):
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

        elif action.startswith("vision_"):
            domain = "vision"

        return TikkiCommand(
            domain=domain,
            action=action,
            operation=operation,
            parameters=args,
            original_text=getattr(intent, "original_text", ""),
            confidence=1.0,
        )