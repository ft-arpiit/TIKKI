from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


CommandDomain = Literal[
    "system",
    "audio",
    "display",
    "application",
    "keyboard",
    "mouse",
    "vision",
    "file",
    "unknown",
]

CommandOperation = Literal[
    "set",
    "increase",
    "decrease",
    "up",
    "down",
    "mute",
    "unmute",
    "launch",
    "press",
    "click",
    "type",
    "scroll",
    "copy",
    "paste",
    "undo",
    "redo",
    "lock",
    "show_desktop",
    "unknown",
]


class TikkiCommand(BaseModel):
    """
    Canonical structured command understood by TIKKI.

    Natural-language input should eventually be converted into
    this structure before execution.
    """

    domain: CommandDomain = "unknown"

    action: str = Field(
        min_length=1,
        description="Canonical action name."
    )

    operation: CommandOperation = "unknown"

    parameters: dict[str, Any] = Field(default_factory=dict)

    original_text: str = ""

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )

    def to_executor_args(self) -> tuple[str, dict[str, Any]]:
        """
        Convert the structured command into the format currently
        expected by WindowsExecutor.
        """

        args = dict(self.parameters)

        if self.operation != "unknown":
            args.setdefault("operation", self.operation)

        return self.action, args