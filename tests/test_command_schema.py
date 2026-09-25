from modules.command_schema import TikkiCommand


def test_volume_command_structure():
    command = TikkiCommand(
        domain="audio",
        action="volume_set",
        operation="set",
        parameters={"value": 50},
        original_text="volume 50",
    )

    assert command.domain == "audio"
    assert command.action == "volume_set"
    assert command.operation == "set"
    assert command.parameters["value"] == 50


def test_executor_conversion():
    command = TikkiCommand(
        domain="audio",
        action="volume_set",
        operation="set",
        parameters={"value": 50},
    )

    action, args = command.to_executor_args()

    assert action == "volume_set"
    assert args["value"] == 50
    assert args["operation"] == "set"