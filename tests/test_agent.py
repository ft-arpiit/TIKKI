from agent import TikkiAgent


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def execute_local(self, action, args):
        self.calls.append((action, args))
        return f"FAKE: {action}"


def test_agent_routes_structured_command_to_executor():
    agent = TikkiAgent()
    fake = FakeExecutor()
    agent.executor = fake

    result = agent.run("volume 30")

    assert result == "FAKE: volume_set"
    assert fake.calls == [
        ("volume_set", {"value": 30, "operation": "set"})
    ]


def test_agent_rejects_unknown_command_safely():
    agent = TikkiAgent()

    result = agent.run("do something dangerous")

    assert result == "I don't have a safe local action for that request yet."