from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Any, Iterable

import pyautogui

from config import settings

logger = logging.getLogger(__name__)


class ExecutionError(RuntimeError):
    pass


SAFE_HOTKEYS = {
    ("ctrl", "c"), ("ctrl", "v"), ("ctrl", "x"), ("ctrl", "z"),
    ("ctrl", "y"), ("ctrl", "a"), ("ctrl", "f"), ("ctrl", "l"),
    ("alt", "tab"), ("alt", "f4"), ("win", "d"), ("ctrl", "shift", "esc"),
}


class WindowsExecutor:
    """Bounded Windows action driver.

    No arbitrary shell command is exposed to the model.
    """

    def _screen_size(self) -> tuple[int, int]:
        return pyautogui.size()

    def _validate_point(self, x: int, y: int) -> tuple[int, int]:
        width, height = self._screen_size()
        if not (0 <= x < width and 0 <= y < height):
            raise ExecutionError(f"Coordinate ({x}, {y}) outside {width}x{height}")
        return x, y

    def volume(self, direction: str = "set", value: int | None = None) -> None:
        """Adjust system volume using Windows Core Audio."""
        import comtypes
        from pycaw.pycaw import AudioUtilities

        comtypes.CoInitialize()
        try:
            device = AudioUtilities.GetSpeakers()
            endpoint = device.EndpointVolume

            if value is not None:
                level = max(0.0, min(100.0, float(value))) / 100.0
                endpoint.SetMasterVolumeLevelScalar(level, None)
                return

            current = endpoint.GetMasterVolumeLevelScalar()

            if direction == "up":
                new_level = min(1.0, current + settings.volume_step)
                endpoint.SetMasterVolumeLevelScalar(new_level, None)

            elif direction == "down":
                new_level = max(0.0, current - settings.volume_step)
                endpoint.SetMasterVolumeLevelScalar(new_level, None)

            elif direction == "mute":
                endpoint.SetMute(1, None)

            elif direction == "unmute":
                endpoint.SetMute(0, None)

            else:
                raise ValueError(f"Unsupported volume direction: {direction}")

        finally:
            comtypes.CoUninitialize()
    def brightness(self, direction: str | None = None, value: int | None = None) -> None:
        try:
            import screen_brightness_control as sbc
            current = int(sbc.get_brightness(display=0)[0] if isinstance(sbc.get_brightness(display=0), list) else sbc.get_brightness(display=0))
            if value is None:
                value = current + (10 if direction == "up" else -10)
            sbc.set_brightness(max(0, min(100, int(value))), display=0)
        except Exception as exc:
            raise ExecutionError(f"Brightness operation failed: {exc}") from exc

    def launch_app(self, command: str) -> None:
        if not command:
            raise ExecutionError("Empty application command")
        # The command comes only from the local alias map, never from model-generated shell text.
        subprocess.Popen(command, shell=False)

    def hotkey(self, keys: Iterable[str]) -> None:
        normalized = tuple(k.lower().strip() for k in keys)
        if normalized not in SAFE_HOTKEYS:
            raise ExecutionError(f"Hotkey not allowlisted: {normalized}")
        pyautogui.hotkey(*normalized)

    def press(self, key: str) -> None:
        allowed = {
            "enter", "esc", "tab", "space", "backspace", "delete",
            "home", "end", "up", "down", "left", "right",
        }
        if key not in allowed:
            raise ExecutionError(f"Key not allowlisted: {key}")
        pyautogui.press(key)

    def execute_local(self, action: str, args: dict[str, Any] | None = None) -> str:
        args = args or {}
        if action == "volume_up":
            self.volume("up")
            return "Volume increased."
        if action == "volume_down":
            self.volume("down")
            return "Volume decreased."
        if action == "volume_mute":
            self.volume("mute")
            return "Volume muted."
        if action == "volume_unmute":
            self.volume("unmute")
            return "Volume unmuted."
        if action == "volume_set":
            self.volume(value=int(args["value"]))
            return f"Volume set to {int(args['value'])}%."
        if action == "brightness_up":
            self.brightness("up")
            return "Brightness increased."
        if action == "brightness_down":
            self.brightness("down")
            return "Brightness decreased."
        if action == "brightness_set":
            self.brightness(value=int(args["value"]))
            return f"Brightness set to {int(args['value'])}%."
        if action == "alt_tab":
            self.hotkey(("alt", "tab"))
            return "Switched window."
        if action == "show_desktop":
            self.hotkey(("win", "d"))
            return "Desktop shown."
        if action == "copy":
            self.hotkey(("ctrl", "c"))
            return "Copied."
        if action == "paste":
            self.hotkey(("ctrl", "v"))
            return "Pasted."
        if action == "undo":
            self.hotkey(("ctrl", "z"))
            return "Undone."
        if action == "redo":
            self.hotkey(("ctrl", "y"))
            return "Redone."
        if action == "lock":
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"], shell=False)
            return "PC locked."
        if action == "launch_app":
            self.launch_app(str(args["command"]))
            return f"Launching {args.get('target', 'application')}."
        if action == "press_key":
            self.press(str(args["key"]))
            return f"Pressed {args['key']}."
        raise ExecutionError(f"Unknown local action: {action}")

    def execute_visual_actions(self, actions: list[dict[str, Any]]) -> str:
        if len(actions) > 12:
            raise ExecutionError("Visual plan contains too many actions.")

        width, height = self._screen_size()
        completed = 0

        for action in actions:
            kind = action.get("type")
            if kind == "move":
                x, y = self._validate_point(int(action["x"]), int(action["y"]))
                pyautogui.moveTo(x, y, duration=0.05)
            elif kind == "click":
                x, y = self._validate_point(int(action["x"]), int(action["y"]))
                pyautogui.click(x, y, clicks=1, interval=settings.click_interval)
            elif kind == "double_click":
                x, y = self._validate_point(int(action["x"]), int(action["y"]))
                pyautogui.doubleClick(x, y, interval=settings.click_interval)
            elif kind == "type":
                text = str(action.get("text", ""))
                if len(text) > settings.max_type_chars:
                    raise ExecutionError("Typed text exceeds safety limit.")
                pyautogui.write(text, interval=0.002)
            elif kind == "scroll":
                amount = int(action.get("amount", 0))
                if abs(amount) > settings.max_scroll_units:
                    raise ExecutionError("Scroll amount exceeds safety limit.")
                pyautogui.scroll(amount)
            elif kind == "hotkey":
                self.hotkey(tuple(action.get("keys", [])))
            elif kind == "wait":
                seconds = max(0.0, min(3.0, float(action.get("seconds", 0.2))))
                time.sleep(seconds)
            else:
                raise ExecutionError(f"Unsupported visual action: {kind}")
            completed += 1

        return f"Completed {completed} visual action(s) on a {width}x{height} screen."
