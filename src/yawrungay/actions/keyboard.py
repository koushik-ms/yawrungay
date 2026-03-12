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

# ydotool uses different key names (evdev keycodes or key names)
YDOTOOL_SPECIAL_KEYS = {
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "escape": "esc",
    "esc": "esc",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "insert": "insert",
    "home": "home",
    "end": "end",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "space": "space",
    "f1": "f1",
    "f2": "f2",
    "f3": "f3",
    "f4": "f4",
    "f5": "f5",
    "f6": "f6",
    "f7": "f7",
    "f8": "f8",
    "f9": "f9",
    "f10": "f10",
    "f11": "f11",
    "f12": "f12",
    "ctrl": "leftctrl",
    "control": "leftctrl",
    "alt": "leftalt",
    "shift": "leftshift",
    "super": "leftmeta",
    "cmd": "leftmeta",
    "win": "leftmeta",
    "meta": "leftmeta",
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
            # ydotool type --delay <ms> "text"
            delay_ms = int(context.type_delay_ms)
            cmd = ["ydotool", "type", "--delay", str(delay_ms), "--", text]

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
            # Parse key combination
            key_names = self._parse_keys_for_ydotool(keys_str)
            if not key_names:
                return ActionResult(success=False, error=f"Invalid key combination: {keys_str}")

            # ydotool key <key1> <key2> ...
            # For combinations, use key1+key2+key3 format
            key_combo = "+".join(key_names)
            cmd = ["ydotool", "key", key_combo]

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

    def _parse_keys_for_ydotool(self, keys_str: str) -> list[str]:
        """Parse key combination for ydotool."""
        keys = []
        parts = keys_str.lower().replace("-", "+").replace(" ", "+").split("+")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part in YDOTOOL_SPECIAL_KEYS:
                keys.append(YDOTOOL_SPECIAL_KEYS[part])
            elif len(part) == 1 and part.isalnum():
                keys.append(part)
            else:
                logger.warning(f"Unknown key for ydotool: {part}")
                return []

        return keys

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
            # Parse key combination for xdotool format
            key_combo = self._parse_keys_for_xdotool(keys_str)
            if not key_combo:
                return ActionResult(success=False, error=f"Invalid key combination: {keys_str}")

            # xdotool key <key1+key2+key3>
            cmd = ["xdotool", "key", key_combo]

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

    def _parse_keys_for_xdotool(self, keys_str: str) -> str:
        """Parse key combination for xdotool format.

        Returns xdotool format: "ctrl+shift+a" or "ctrl+Return"
        """
        keys = []
        parts = keys_str.lower().replace("-", "+").replace(" ", "+").split("+")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part in XDOTOOL_MODIFIERS:
                keys.append(XDOTOOL_MODIFIERS[part])
            elif part in XDOTOOL_SPECIAL_KEYS:
                keys.append(XDOTOOL_SPECIAL_KEYS[part])
            elif len(part) == 1:
                keys.append(part)
            else:
                logger.warning(f"Unknown key for xdotool: {part}")
                return ""

        return "+".join(keys)

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
