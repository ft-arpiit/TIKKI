from __future__ import annotations

import logging
from typing import TypedDict
from modules.understanding import CommandUnderstanding
from langgraph.graph import END, START, StateGraph

from modules.executor import ExecutionError, WindowsExecutor
from modules.vision import ScreenGrabber, VisualGrounder
from modules.command_schema import TikkiCommand
from modules.router import RouteKind


logger = logging.getLogger(__name__)


class TikkiState(TypedDict, total=False):
    text: str
    command: TikkiCommand
    result: str
    screenshot: object
    plan: object


class TikkiAgent:
    def __init__(self) -> None:
        self.understanding = CommandUnderstanding()
        self.executor = WindowsExecutor()
        self.grabber = ScreenGrabber()
        self.grounder = VisualGrounder()
        self.graph = self._build_graph()

    def _route(self, state: TikkiState) -> TikkiState:
        command = self.understanding.understand(state["text"])

        return {
            "command": command,
        }
    def _validate_command(self, state: TikkiState) -> TikkiState:
        command = state["command"]

        if command.domain == "unknown":
            return {
                "result": "I don't have a safe local action for that request yet."
            }

        if command.confidence < 0.5:
            return {
                "result": "I'm not confident enough to execute that command safely."
            }

        return {}        
    def _execute_local(self, state: TikkiState) -> TikkiState:
        command = state["command"]

        try:
            action, args = command.to_executor_args()
            result = self.executor.execute_local(action, args)
        except ExecutionError as exc:
            logger.exception("Local execution failed")
            result = f"I couldn't complete that local action: {exc}"

        return {"result": result}
    
    def _capture(self, state: TikkiState) -> TikkiState:
        return {"screenshot": self.grabber.capture()}

    def _ground(self, state: TikkiState) -> TikkiState:
        plan = self.grounder.ground(state["text"], state["screenshot"])
        return {"plan": plan}

    def _execute_visual(self, state: TikkiState) -> TikkiState:
        plan = state["plan"]
        if plan.done:
            return {"result": plan.explanation or "Done."}
        try:
            result = self.executor.execute_visual_actions(
                [a.model_dump() for a in plan.actions]
            )
            return {"result": result}
        except ExecutionError as exc:
            logger.exception("Visual execution failed")
            return {"result": f"I stopped the visual action safely: {exc}"}

    def _unknown(self, state: TikkiState) -> TikkiState:
        return {"result": "I don't have a safe local action for that request yet."}

    @staticmethod
    def _after_route(state: TikkiState) -> str:
        command = state["command"]

        if command.domain == "vision":
            return "vision"

        if command.domain != "unknown":
            return "local"

        return "unknown"

    def _build_graph(self):
        graph = StateGraph(TikkiState)
        graph.add_node("route", self._route)
        graph.add_node("local", self._execute_local)
        graph.add_node("capture", self._capture)
        graph.add_node("ground", self._ground)
        graph.add_node("visual", self._execute_visual)
        graph.add_node("unknown", self._unknown)

        graph.add_edge(START, "route")
        graph.add_conditional_edges(
            "route",
            self._after_route,
            {"local": "local", "vision": "capture", "unknown": "unknown"},
        )
        graph.add_edge("capture", "ground")
        graph.add_edge("ground", "visual")
        graph.add_edge("local", END)
        graph.add_edge("visual", END)
        graph.add_edge("unknown", END)
        return graph.compile()

    def run(self, text: str) -> str:
        state = self.graph.invoke({"text": text})
        return state.get("result", "No result.")
