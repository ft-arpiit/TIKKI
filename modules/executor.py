from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Any, Iterable
from urllib.parse import quote_plus

import pyautogui

from config import settings

logger = logging.getLogger(__name__)


class ExecutionError(RuntimeError):
    pass


SAFE_HOTKEYS = {
    ("ctrl", "c"),
    ("ctrl", "v"),
    ("ctrl", "x"),
    ("ctrl", "z"),
    ("ctrl", "y"),
    ("enter",),
    ("ctrl", "a"),
    ("ctrl", "f"),
    ("ctrl", "l"),
    ("alt", "tab"),
    ("alt", "f4"),
    ("win", "d"),
    ("ctrl", "shift", "esc"),
}


class WindowsExecutor:
    """Bounded deterministic Windows action driver."""

    # ---------------------------------------------------------
    # Basic screen helpers
    # ---------------------------------------------------------

    def _screen_size(self) -> tuple[int, int]:
        return pyautogui.size()

    def _validate_point(self, x: int, y: int) -> tuple[int, int]:
        width, height = self._screen_size()

        if not (0 <= x < width and 0 <= y < height):
            raise ExecutionError(
                f"Coordinate ({x}, {y}) outside {width}x{height}"
            )

        return x, y

    # ---------------------------------------------------------
    # Volume
    # ---------------------------------------------------------

    def volume(
        self,
        direction: str = "set",
        value: int | None = None,
    ) -> None:
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
                new_level = min(
                    1.0,
                    current + settings.volume_step,
                )
                endpoint.SetMasterVolumeLevelScalar(
                    new_level,
                    None,
                )

            elif direction == "down":
                new_level = max(
                    0.0,
                    current - settings.volume_step,
                )
                endpoint.SetMasterVolumeLevelScalar(
                    new_level,
                    None,
                )

            elif direction == "mute":
                endpoint.SetMute(1, None)

            elif direction == "unmute":
                endpoint.SetMute(0, None)

            else:
                raise ValueError(
                    f"Unsupported volume direction: {direction}"
                )

        finally:
            comtypes.CoUninitialize()

    # ---------------------------------------------------------
    # Brightness
    # ---------------------------------------------------------

    def brightness(
        self,
        direction: str | None = None,
        value: int | None = None,
    ) -> None:
        try:
            import screen_brightness_control as sbc

            current_raw = sbc.get_brightness(display=0)

            if isinstance(current_raw, list):
                current = int(current_raw[0])
            else:
                current = int(current_raw)

            if value is None:
                if direction == "up":
                    value = current + 10
                elif direction == "down":
                    value = current - 10
                else:
                    raise ValueError(
                        "Brightness requires a direction or value."
                    )

            value = max(0, min(100, int(value)))

            sbc.set_brightness(
                value,
                display=0,
            )

        except Exception as exc:
            raise ExecutionError(
                f"Brightness operation failed: {exc}"
            ) from exc

    # ---------------------------------------------------------
    # Application launching
    # ---------------------------------------------------------

    def launch_app(self, command: str) -> None:
        command = command.strip().lower()

        if not command:
            raise ExecutionError(
                "No application specified."
            )

        app_commands = {
            "chrome": [
                os.path.expandvars(
                    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
                ),
                os.path.expandvars(
                    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
                ),
                os.path.expandvars(
                    r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
                ),
                "chrome.exe",
            ],
            "chrome.exe": [
                os.path.expandvars(
                    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
                ),
                os.path.expandvars(
                    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
                ),
                os.path.expandvars(
                    r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
                ),
                "chrome.exe",
            ],
            "notepad": ["notepad.exe"],
            "notepad.exe": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "calc": ["calc.exe"],
            "calc.exe": ["calc.exe"],
            "explorer": ["explorer.exe"],
            "explorer.exe": ["explorer.exe"],
            "terminal": ["wt.exe"],
            "edge": ["msedge.exe"],
            "msedge.exe": ["msedge.exe"],
        }

        candidates = app_commands.get(
            command,
            [command],
        )

        for candidate in candidates:
            if not candidate:
                continue

            try:
                if os.path.isabs(candidate):
                    if not os.path.exists(candidate):
                        continue

                subprocess.Popen(
                    [candidate],
                    shell=False,
                )

                logger.info(
                    "Launched application: %s",
                    candidate,
                )

                return

            except FileNotFoundError:
                continue

            except OSError as exc:
                logger.warning(
                    "Failed launching %s: %s",
                    candidate,
                    exc,
                )

        raise ExecutionError(
            f"Could not find or launch application '{command}'."
        )

    # ---------------------------------------------------------
    # Google search
    # ---------------------------------------------------------

    def google_search(self, query: str) -> None:
        query = str(query).strip()

        if not query:
            raise ExecutionError(
                "Google search query is empty."
            )

        url = (
            "https://www.google.com/search?q="
            + quote_plus(query)
        )

        chrome_candidates = [
            os.path.expandvars(
                r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
            ),
            os.path.expandvars(
                r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
            ),
            os.path.expandvars(
                r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
            ),
            "chrome.exe",
        ]

        # Directly open the search URL in Chrome.
        for chrome in chrome_candidates:
            try:
                if os.path.isabs(chrome):
                    if not os.path.exists(chrome):
                        continue

                subprocess.Popen(
                    [chrome, url],
                    shell=False,
                )

                logger.info(
                    "Google search opened: %s",
                    query,
                )

                return

            except FileNotFoundError:
                continue

            except OSError as exc:
                logger.warning(
                    "Chrome launch failed for %s: %s",
                    chrome,
                    exc,
                )

        raise ExecutionError(
            "Chrome executable could not be found."
        )

    # ---------------------------------------------------------
    # Keyboard
    # ---------------------------------------------------------

    def hotkey(self, keys: Iterable[str]) -> None:
        normalized = tuple(
            k.lower().strip()
            for k in keys
        )

        if normalized not in SAFE_HOTKEYS:
            raise ExecutionError(
                f"Hotkey not allowlisted: {normalized}"
            )

        pyautogui.hotkey(*normalized)

    def press(self, key: str) -> None:
        allowed = {
            "enter",
            "esc",
            "tab",
            "space",
            "backspace",
            "delete",
            "home",
            "end",
            "up",
            "down",
            "left",
            "right",
        }

        key = key.lower().strip()

        if key not in allowed:
            raise ExecutionError(
                f"Key not allowlisted: {key}"
            )

        pyautogui.press(key)

    # ---------------------------------------------------------
    # Local execution
    # ---------------------------------------------------------

    def execute_local(
        self,
        action: str,
        args: dict[str, Any] | None = None,
    ) -> str:
        args = args or {}

        # ---------------- AUDIO ----------------

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
            value = int(args["value"])
            self.volume(value=value)
            return f"Volume set to {value}%."

        # ---------------- DISPLAY ----------------

        if action == "brightness_up":
            self.brightness("up")
            return "Brightness increased."

        if action == "brightness_down":
            self.brightness("down")
            return "Brightness decreased."

        if action == "brightness_set":
            value = int(args["value"])
            self.brightness(value=value)
            return f"Brightness set to {value}%."

        # ---------------- WINDOWS ----------------

        if action == "alt_tab":
            self.hotkey(("alt", "tab"))
            return "Switched window."

        if action == "show_desktop":
            self.hotkey(("win", "d"))
            return "Desktop shown."

        if action == "lock":
            subprocess.Popen(
                [
                    "rundll32.exe",
                    "user32.dll,LockWorkStation",
                ],
                shell=False,
            )
            return "PC locked."

        # ---------------- CLIPBOARD ----------------

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

        # ---------------- APPLICATION ----------------

        if action == "launch_app":
            command = str(
                args.get("command", "")
            )

            self.launch_app(command)

            return (
                f"Launching "
                f"{args.get('target', command)}."
            )

        # ---------------- GOOGLE SEARCH ----------------

        if action == "google_search":
            query = str(
                args.get("query", "")
            ).strip()

            self.google_search(query)

            return f"Searching Google for: {query}"

        # ---------------- KEYBOARD ----------------

        if action == "press_key":
            key = str(args["key"])
            self.press(key)
            return f"Pressed {key}."

        raise ExecutionError(
            f"Unknown local action: {action}"
        )

    # ---------------------------------------------------------
    # Visual execution
    # ---------------------------------------------------------

    def execute_visual_actions(
        self,
        actions: list[dict[str, Any]],
    ) -> str:
        if len(actions) > 12:
            raise ExecutionError(
                "Visual plan contains too many actions."
            )

        width, height = self._screen_size()
        completed = 0

        for action in actions:
            kind = action.get("type")

            if kind == "move":
                x, y = self._validate_point(
                    int(action["x"]),
                    int(action["y"]),
                )

                pyautogui.moveTo(
                    x,
                    y,
                    duration=0.05,
                )

            elif kind == "click":
                x, y = self._validate_point(
                    int(action["x"]),
                    int(action["y"]),
                )

                pyautogui.click(
                    x,
                    y,
                    clicks=1,
                    interval=settings.click_interval,
                )

            elif kind == "double_click":
                x, y = self._validate_point(
                    int(action["x"]),
                    int(action["y"]),
                )

                pyautogui.doubleClick(
                    x,
                    y,
                    interval=settings.click_interval,
                )

            elif kind == "type":
                text = str(
                    action.get("text", "")
                )

                if len(text) > settings.max_type_chars:
                    raise ExecutionError(
                        "Typed text exceeds safety limit."
                    )

                pyautogui.write(
                    text,
                    interval=0.002,
                )

            elif kind == "scroll":
                amount = int(
                    action.get("amount", 0)
                )

                if abs(amount) > settings.max_scroll_units:
                    raise ExecutionError(
                        "Scroll amount exceeds safety limit."
                    )

                pyautogui.scroll(amount)

            elif kind == "hotkey":
                self.hotkey(
                    tuple(
                        action.get("keys", [])
                    )
                )

            elif kind == "wait":
                seconds = max(
                    0.0,
                    min(
                        3.0,
                        float(
                            action.get(
                                "seconds",
                                0.2,
                            )
                        ),
                    ),
                )

                time.sleep(seconds)

            else:
                raise ExecutionError(
                    f"Unsupported visual action: {kind}"
                )

            completed += 1

        return (
            f"Completed {completed} visual action(s) "
            f"on a {width}x{height} screen."
        )