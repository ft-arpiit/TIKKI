from modules.command_schema import TikkiCommand
from modules.validator import CommandValidator


def test_valid_command():
    command = TikkiCommand(
        domain="audio",
        action="volume_set",
        operation="set",
        parameters={"value": 30},
        confidence=1.0,
    )

    valid, reason = CommandValidator().validate(command)

    assert valid is True
    assert reason == ""


def test_unknown_command_rejected():
    command = TikkiCommand(
        domain="unknown",
        action="unknown",
        confidence=0.2,
    )

    valid, reason = CommandValidator().validate(command)

    assert valid is False
    assert reason == "Unknown command."


def test_low_confidence_command_rejected():
    command = TikkiCommand(
        domain="audio",
        action="volume_set",
        operation="set",
        parameters={"value": 30},
        confidence=0.2,
    )

    valid, reason = CommandValidator().validate(command)

    assert valid is False
    assert reason == "Command confidence is too low."