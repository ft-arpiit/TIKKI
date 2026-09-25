from modules.understanding import CommandUnderstanding


def test_natural_language_volume_set():
    understanding = CommandUnderstanding()

    command = understanding.understand(
        "make my volume 50 percent"
    )

    assert command.domain == "audio"
    assert command.action == "volume_set"
    assert command.operation == "set"
    assert command.parameters["value"] == 50


def test_natural_language_volume_up():
    understanding = CommandUnderstanding()

    command = understanding.understand(
        "turn the volume up"
    )

    assert command.domain == "audio"
    assert command.action == "volume_up"
    assert command.operation == "increase"


def test_natural_language_volume_down():
    understanding = CommandUnderstanding()

    command = understanding.understand(
        "lower the volume"
    )

    assert command.domain == "audio"
    assert command.action == "volume_down"
    assert command.operation == "decrease"


def test_natural_language_brightness():
    understanding = CommandUnderstanding()

    command = understanding.understand(
        "make the brightness 40"
    )

    assert command.domain == "display"
    assert command.action == "brightness_set"
    assert command.operation == "set"
    assert command.parameters["value"] == 40


def test_existing_router_path_still_works():
    understanding = CommandUnderstanding()

    command = understanding.understand("volume 50")

    assert command.domain == "audio"
    assert command.action == "volume_set"
    assert command.parameters["value"] == 50

def test_invalid_volume_percentage_is_rejected():
    understanding = CommandUnderstanding()
    command = understanding.understand("make my volume 230 percent")

    assert command.domain == "unknown"
    assert command.action == "unknown"
    assert command.operation == "unknown"
    assert command.confidence == 0.2

def test_valid_volume_percentage_boundaries():
    understanding = CommandUnderstanding()

    zero = understanding.understand("make my volume 0 percent")
    hundred = understanding.understand("make my volume 100 percent")

    assert zero.action == "volume_set"
    assert zero.parameters["value"] == 0

    assert hundred.action == "volume_set"
    assert hundred.parameters["value"] == 100        