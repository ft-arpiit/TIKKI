from __future__ import annotations

from modules.command_schema import TikkiCommand


class CommandValidator:
    """Validates commands before TIKKI executes them."""

    MIN_CONFIDENCE = 0.5

    def validate(self, command: TikkiCommand) -> tuple[bool, str]:
        if command.domain == "unknown":
            return False, "Unknown command."

        if command.confidence < self.MIN_CONFIDENCE:
            return False, "Command confidence is too low."

        if not command.action:
            return False, "Command has no action."

        return True, ""