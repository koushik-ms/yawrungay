"""Keyboard actions with ydotool/xdotool backends.

Uses ydotool for Wayland, xdotool for X11, with pynput as fallback.
"""

import logging
import os
import shutil
import subprocess
from typing import Any, Optional

from yawrungay.actions.base import ActionContext, ActionResult, BaseAction

logger = logging.getLogger(__name__)

# Key name mappings for xdotool/ydotool
XDOTOOL_MODIFIERS = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "super": "super",
    "cmd": "super",
    "win": "super",
    "meta": "super",
}

XDOTOOL_SPECIAL_KEYS = {
    "enter": "Return",
    "return": "Return",
    "tab": "Tab",
    "escape": "Escape",
    "esc": "Escape",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "insert": "Insert",
    "home": "Home",
    "end": "End",
    "pageup": "Page_Up",
    "pagedown": "Page_Down",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "space": "space",
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
    "f6": "F6",
    "f7": "F7",
    "f8": "F8",
    "f9": "F9",
    "f10": "F10",
    "f11": "F11",
    "f12": "F12",
    "capslock": "Caps_Lock",
    "numlock": "Num_Lock",
    "scrolllock": "Scroll_Lock",
}

# ydotool uses evdev keycodes (numeric values)
YDOTOOL_KEYCODES = {
    # Modifiers
    "ctrl": 29,
    "control": 29,
    "leftctrl": 29,
    "rightctrl": 97,
    "alt": 56,
    "leftalt": 56,
    "rightalt": 100,
    "shift": 42,
    "leftshift": 42,
    "rightshift": 54,
    "super": 125,
    "meta": 125,
    "leftmeta": 125,
    "rightmeta": 127,
    "cmd": 125,
    "win": 125,
    "capslock": 58,
    "numlock": 69,
    "scrolllock": 70,
    # Numbers (top row)
    "1": 2,
    "2": 3,
    "3": 4,
    "4": 5,
    "5": 6,
    "6": 7,
    "7": 8,
    "8": 9,
    "9": 10,
    "0": 11,
    # Letters (lowercase)
    "a": 30,
    "b": 48,
    "c": 46,
    "d": 32,
    "e": 18,
    "f": 33,
    "g": 34,
    "h": 35,
    "i": 23,
    "j": 36,
    "k": 37,
    "l": 38,
    "m": 50,
    "n": 49,
    "o": 24,
    "p": 25,
    "q": 16,
    "r": 19,
    "s": 31,
    "t": 20,
    "u": 22,
    "v": 47,
    "w": 17,
    "x": 45,
    "y": 21,
    "z": 44,
    # Letters (uppercase - same as lowercase)
    "A": 30,
    "B": 48,
    "C": 46,
    "D": 32,
    "E": 18,
    "F": 33,
    "G": 34,
    "H": 35,
    "I": 23,
    "J": 36,
    "K": 37,
    "L": 38,
    "M": 50,
    "N": 49,
    "O": 24,
    "P": 25,
    "Q": 16,
    "R": 19,
    "S": 31,
    "T": 20,
    "U": 22,
    "V": 47,
    "W": 17,
    "X": 45,
    "Y": 21,
    "Z": 44,
    # Special keys
    "escape": 1,
    "esc": 1,
    "enter": 28,
    "return": 28,
    "tab": 15,
    "backspace": 14,
    "space": 57,
    "minus": 12,
    "-": 12,
    "equal": 13,
    "=": 13,
    "leftbrace": 26,
    "[": 26,
    "rightbrace": 27,
    "]": 27,
    "backslash": 43,
    "\\": 43,
    "semicolon": 39,
    ";": 39,
    "apostrophe": 40,
    "'": 40,
    "grave": 41,
    "`": 41,
    "comma": 51,
    ",": 51,
    "dot": 52,
    ".": 52,
    "slash": 53,
    "/": 53,
    # Function keys
    "f1": 59,
    "f2": 60,
    "f3": 61,
    "f4": 62,
    "f5": 63,
    "f6": 64,
    "f7": 65,
    "f8": 66,
    "f9": 67,
    "f10": 68,
    "f11": 87,
    "f12": 88,
    # Navigation keys
    "home": 102,
    "end": 107,
    "pageup": 104,
    "pagedown": 109,
    "up": 105,
    "down": 108,
    "left": 106,
    "right": 107,
    "insert": 110,
    "delete": 111,
    "del": 111,
    # Keypad
    "kp0": 82,
    "kp1": 79,
    "kp2": 80,
    "kp3": 81,
    "kp4": 75,
    "kp5": 76,
    "kp6": 77,
    "kp7": 71,
    "kp8": 72,
    "kp9": 83,
    "kpminus": 74,
    "kpplus": 78,
    "kpdot": 83,
    "kpslash": 98,
    "kpenter": 96,
    "kpnumlock": 76,
    # Other
    "pause": 119,
    "sysrq": 99,
    "printscreen": 99,
}


def _detect_backend() -> str:
    """Detect the best available keyboard backend.

    Returns:
        Backend name: 'ydotool', 'xdotool', or 'pynput'
    """
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    display = os.environ.get("DISPLAY", "")
    wayland_display = os.environ.get("WAYLAND_DISPLAY", "")

    # Check if ydotool is available (preferred for Wayland)
    if shutil.which("ydotool"):
        # Check if ydotoold daemon is running
        try:
            result = subprocess.run(
                ["pgrep", "-x", "ydotoold"],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                logger.info("Using ydotool backend (ydotoold running)")
                return "ydotool"
            else:
                logger.debug("ydotool found but ydotoold not running")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Check if xdotool is available (works on X11 and XWayland)
    if shutil.which("xdotool") and display:
        logger.info(f"Using xdotool backend (DISPLAY={display})")
        return "xdotool"

    # Fallback to pynput
    logger.info("Using pynput backend (fallback)")
    return "pynput"


class KeyboardAction(BaseAction):
    """Keyboard simulation actions.

    Supports:
    - type: Type text character by character
    - press: Press key combinations (e.g., "ctrl+c")

    Uses ydotool on Wayland, xdotool on X11, pynput as fallback.
    """

    def __init__(self):
        """Initialize keyboard action with best available backend."""
        self._backend: Optional[str] = None

    @property
    def backend(self) -> str:
        """Get the keyboard backend, detecting on first use."""
        if self._backend is None:
            self._backend = _detect_backend()
        return self._backend

    @property
    def name(self) -> str:
        return "keyboard"

    def execute(self, arguments: dict[str, Any], context: ActionContext) -> ActionResult:
        """Execute keyboard action.

        Args:
            arguments: Must contain either 'text' for typing or 'keys' for pressing.
            context: Execution context.

        Returns:
            ActionResult indicating success or failure.
        """
        if "text" in arguments:
            return self._type_text(arguments["text"], context)
        elif "keys" in arguments:
            return self._press_keys(arguments["keys"], context)
        else:
            return ActionResult(success=False, error="Missing 'text' or 'keys' argument")

    def _type_text(self, text: str, context: ActionContext) -> ActionResult:
        """Type text using the appropriate backend.

        Args:
            text: Text to type.
            context: Execution context.

        Returns:
            ActionResult indicating success.
        """
        backend = self.backend

        if backend == "ydotool":
            return self._type_text_ydotool(text, context)
        elif backend == "xdotool":
            return self._type_text_xdotool(text, context)
        else:
            return self._type_text_pynput(text, context)

    def _press_keys(self, keys_str: str, context: ActionContext) -> ActionResult:
        """Press key combination using the appropriate backend.

        Args:
            keys_str: Key combination string (e.g., "ctrl+c", "alt+tab").
            context: Execution context.

        Returns:
            ActionResult indicating success.
        """
        backend = self.backend

        if backend == "ydotool":
            return self._press_keys_ydotool(keys_str, context)
        elif backend == "xdotool":
            return self._press_keys_xdotool(keys_str, context)
        else:
            return self._press_keys_pynput(keys_str, context)

    # ===== ydotool backend =====

    def _type_text_ydotool(self, text: str, context: ActionContext) -> ActionResult:
        """Type text using ydotool."""
        try:
            # ydotool type --key-delay <ms> "text"
            delay_ms = int(context.type_delay_ms)
            cmd = ["ydotool", "type", "--key-delay", str(delay_ms), "--", text]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                error = result.stderr.strip() or f"ydotool exited with code {result.returncode}"
                logger.error(f"ydotool type failed: {error}")
                return ActionResult(success=False, error=error)

            logger.info(f"Typed (ydotool): {text}")
            return ActionResult(success=True, message=f"Typed: {text}")

        except subprocess.TimeoutExpired:
            logger.error("ydotool type timed out")
            return ActionResult(success=False, error="ydotool timed out")
        except Exception as e:
            logger.error(f"ydotool type failed: {e}")
            return ActionResult(success=False, error=str(e))

    def _press_keys_ydotool(self, keys_str: str, context: ActionContext) -> ActionResult:
        """Press key combination using ydotool."""
        try:
            key_parts = self._parse_keys_for_ydotool(keys_str)
            if not key_parts:
                return ActionResult(success=False, error=f"Invalid key combination: {keys_str}")

            keys = key_parts["keys"]

            key_events = []
            for key in keys:
                key_events.append(f"{key}:1")
            for key in reversed(keys):
                key_events.append(f"{key}:0")

            cmd = ["ydotool", "key", *key_events]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                error = result.stderr.strip() or f"ydotool exited with code {result.returncode}"
                logger.error(f"ydotool key failed: {error}")
                return ActionResult(success=False, error=error)

            logger.info(f"Pressed (ydotool): {keys_str}")
            return ActionResult(success=True, message=f"Pressed: {keys_str}")

        except subprocess.TimeoutExpired:
            logger.error("ydotool key timed out")
            return ActionResult(success=False, error="ydotool timed out")
        except Exception as e:
            logger.error(f"ydotool key failed: {e}")
            return ActionResult(success=False, error=str(e))

    def _parse_keys_for_ydotool(self, keys_str: str) -> dict[str, list[str]]:
        """Parse key combination for ydotool using evdev keycodes.

        Returns:
            Dict with 'keys' (list of keycode strings) and 'modifiers' (list of modifier keycodes).
        """
        keys = []
        modifiers = []
        parts = keys_str.lower().replace("-", "+").replace(" ", "+").split("+")

        modifier_keycodes = {29, 56, 42, 125, 97, 100, 54, 127}

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part in YDOTOOL_KEYCODES:
                keycode = YDOTOOL_KEYCODES[part]
                keys.append(str(keycode))
                if keycode in modifier_keycodes:
                    modifiers.append(str(keycode))
            else:
                logger.warning(f"Unknown key for ydotool: {part}")
                return {}

        return {"keys": keys, "modifiers": modifiers}

    # ===== xdotool backend =====

    def _type_text_xdotool(self, text: str, context: ActionContext) -> ActionResult:
        """Type text using xdotool."""
        try:
            # xdotool type --delay <ms> "text"
            delay_ms = int(context.type_delay_ms)
            cmd = ["xdotool", "type", "--delay", str(delay_ms), "--", text]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                error = result.stderr.strip() or f"xdotool exited with code {result.returncode}"
                logger.error(f"xdotool type failed: {error}")
                return ActionResult(success=False, error=error)

            logger.info(f"Typed (xdotool): {text}")
            return ActionResult(success=True, message=f"Typed: {text}")

        except subprocess.TimeoutExpired:
            logger.error("xdotool type timed out")
            return ActionResult(success=False, error="xdotool timed out")
        except Exception as e:
            logger.error(f"xdotool type failed: {e}")
            return ActionResult(success=False, error=str(e))

    def _press_keys_xdotool(self, keys_str: str, context: ActionContext) -> ActionResult:
        """Press key combination using xdotool."""
        try:
            key_parts = self._parse_keys_for_xdotool(keys_str)
            if not key_parts["keys"]:
                return ActionResult(success=False, error=f"Invalid key combination: {keys_str}")

            keys = key_parts["keys"]
            modifiers = key_parts["modifiers"]

            cmd_parts = []
            for key in keys:
                cmd_parts.extend(["keydown", key])
            for key in reversed(keys):
                cmd_parts.extend(["keyup", key])

            cmd = ["xdotool", *cmd_parts]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                error = result.stderr.strip() or f"xdotool exited with code {result.returncode}"
                logger.error(f"xdotool key failed: {error}")
                return ActionResult(success=False, error=error)

            logger.info(f"Pressed (xdotool): {keys_str}")
            return ActionResult(success=True, message=f"Pressed: {keys_str}")

        except subprocess.TimeoutExpired:
            logger.error("xdotool key timed out")
            return ActionResult(success=False, error="xdotool timed out")
        except Exception as e:
            logger.error(f"xdotool key failed: {e}")
            return ActionResult(success=False, error=str(e))

    def _parse_keys_for_xdotool(self, keys_str: str) -> dict[str, list[str]]:
        """Parse key combination for xdotool format.

        Returns:
            Dict with 'keys' (list of key names) and 'modifiers' (list of modifier key names).
        """
        keys = []
        modifiers = []
        parts = keys_str.lower().replace("-", "+").replace(" ", "+").split("+")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part in XDOTOOL_MODIFIERS:
                key_name = XDOTOOL_MODIFIERS[part]
                keys.append(key_name)
                modifiers.append(key_name)
            elif part in XDOTOOL_SPECIAL_KEYS:
                keys.append(XDOTOOL_SPECIAL_KEYS[part])
            elif len(part) == 1:
                keys.append(part)
            else:
                logger.warning(f"Unknown key for xdotool: {part}")
                return {"keys": [], "modifiers": []}

        return {"keys": keys, "modifiers": modifiers}

    # ===== pynput backend (fallback) =====

    def _type_text_pynput(self, text: str, context: ActionContext) -> ActionResult:
        """Type text using pynput (fallback)."""
        try:
            import time

            from pynput import keyboard

            controller = keyboard.Controller()
            delay_s = context.type_delay_ms / 1000.0

            for char in text:
                controller.type(char)
                if delay_s > 0:
                    time.sleep(delay_s)

            logger.info(f"Typed (pynput): {text}")
            return ActionResult(success=True, message=f"Typed: {text}")

        except Exception as e:
            logger.error(f"pynput type failed: {e}")
            return ActionResult(success=False, error=str(e))

    def _press_keys_pynput(self, keys_str: str, context: ActionContext) -> ActionResult:
        """Press key combination using pynput (fallback)."""
        try:
            import time

            from pynput import keyboard

            controller = keyboard.Controller()
            keys = self._parse_keys_for_pynput(keys_str)

            if not keys:
                return ActionResult(success=False, error=f"Invalid key combination: {keys_str}")

            hold_s = context.key_hold_ms / 1000.0

            for key in keys:
                controller.press(key)

            time.sleep(hold_s)

            for key in reversed(keys):
                controller.release(key)

            logger.info(f"Pressed (pynput): {keys_str}")
            return ActionResult(success=True, message=f"Pressed: {keys_str}")

        except Exception as e:
            logger.error(f"pynput key press failed: {e}")
            return ActionResult(success=False, error=str(e))

    def _parse_keys_for_pynput(self, keys_str: str) -> list:
        """Parse key combination for pynput."""
        from pynput import keyboard

        PYNPUT_MODIFIERS = {
            "ctrl": keyboard.Key.ctrl,
            "control": keyboard.Key.ctrl,
            "alt": keyboard.Key.alt,
            "shift": keyboard.Key.shift,
            "super": keyboard.Key.cmd,
            "cmd": keyboard.Key.cmd,
            "win": keyboard.Key.cmd,
            "meta": keyboard.Key.cmd,
        }

        PYNPUT_SPECIAL_KEYS = {
            "enter": keyboard.Key.enter,
            "return": keyboard.Key.enter,
            "tab": keyboard.Key.tab,
            "escape": keyboard.Key.esc,
            "esc": keyboard.Key.esc,
            "backspace": keyboard.Key.backspace,
            "delete": keyboard.Key.delete,
            "del": keyboard.Key.delete,
            "insert": keyboard.Key.insert,
            "home": keyboard.Key.home,
            "end": keyboard.Key.end,
            "pageup": keyboard.Key.page_up,
            "pagedown": keyboard.Key.page_down,
            "up": keyboard.Key.up,
            "down": keyboard.Key.down,
            "left": keyboard.Key.left,
            "right": keyboard.Key.right,
            "space": keyboard.Key.space,
            "f1": keyboard.Key.f1,
            "f2": keyboard.Key.f2,
            "f3": keyboard.Key.f3,
            "f4": keyboard.Key.f4,
            "f5": keyboard.Key.f5,
            "f6": keyboard.Key.f6,
            "f7": keyboard.Key.f7,
            "f8": keyboard.Key.f8,
            "f9": keyboard.Key.f9,
            "f10": keyboard.Key.f10,
            "f11": keyboard.Key.f11,
            "f12": keyboard.Key.f12,
            "capslock": keyboard.Key.caps_lock,
            "numlock": keyboard.Key.num_lock,
            "scrolllock": keyboard.Key.scroll_lock,
        }

        keys = []
        parts = keys_str.lower().replace("-", "+").replace(" ", "+").split("+")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part in PYNPUT_MODIFIERS:
                keys.append(PYNPUT_MODIFIERS[part])
            elif part in PYNPUT_SPECIAL_KEYS:
                keys.append(PYNPUT_SPECIAL_KEYS[part])
            elif len(part) == 1:
                keys.append(keyboard.KeyCode.from_char(part))
            else:
                logger.warning(f"Unknown key for pynput: {part}")
                return []

        return keys

    def validate_arguments(self, arguments: dict[str, Any]) -> Optional[str]:
        """Validate keyboard action arguments.

        Args:
            arguments: Arguments to validate.

        Returns:
            Error message if validation fails, None if valid.
        """
        if "text" not in arguments and "keys" not in arguments:
            return "Missing 'text' or 'keys' argument"

        if "text" in arguments and not isinstance(arguments["text"], str):
            return "'text' must be a string"

        if "keys" in arguments and not isinstance(arguments["keys"], str):
            return "'keys' must be a string"

        return None
