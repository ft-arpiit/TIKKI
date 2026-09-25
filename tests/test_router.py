from modules.router import LocalRouter, RouteKind


def test_volume_up():
    intent = LocalRouter().route("volume up")
    assert intent.kind == RouteKind.LOCAL
    assert intent.action == "volume_up"


def test_brightness_value():
    intent = LocalRouter().route("brightness 42%")
    assert intent.kind == RouteKind.LOCAL
    assert intent.action == "brightness_set"
    assert intent.args["value"] == 42


def test_visual_click():
    intent = LocalRouter().route("click the submit button")
    assert intent.kind == RouteKind.VISION
