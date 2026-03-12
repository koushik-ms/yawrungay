"""Keyboard actions using pynput."""

import logging
import time
from typing import Any, Optional

from pynput import keyboard

from yawrungay.actions.base import ActionContext, ActionResult, BaseAction

logger = logging.getLogger(__name__)

MODIFIER_KEYS = {
    "ctrl": keyboard.Key.ctrl,
    "control": keyboard.Key.ctrl,
    "alt": keyboard.Key.alt,
    "shift": keyboard.Key.shift,
    "super": keyboard.Key.cmd,
    "cmd": keyboard.Key.cmd,
    "win": keyboard.Key.cmd,
    "meta": keyboard.Key.cmd,
}

SPECIAL_KEYS = {
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


class KeyboardAction(BaseAction):
    """Keyboard simulation actions.

    Supports:
    - type: Type text character by character
    - press: Press key combinations (e.g., "ctrl+c")
    """

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
        """Type text character by character.

        Args:
            text: Text to type.
            context: Execution context.

        Returns:
            ActionResult indicating success.
        """
        try:
            controller = keyboard.Controller()
            delay_s = context.type_delay_ms / 1000.0

            for char in text:
                controller.type(char)
                if delay_s > 0:
                    time.sleep(delay_s)

            logger.info(f"Typed: {text}")
            return ActionResult(success=True, message=f"Typed: {text}")

        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return ActionResult(success=False, error=str(e))

    def _press_keys(self, keys_str: str, context: ActionContext) -> ActionResult:
        """Press key combination.

        Args:
            keys_str: Key combination string (e.g., "ctrl+c", "alt+tab").
            context: Execution context.

        Returns:
            ActionResult indicating success.
        """
        try:
            controller = keyboard.Controller()
            keys = self._parse_key_combination(keys_str)

            if not keys:
                return ActionResult(success=False, error=f"Invalid key combination: {keys_str}")

            hold_s = context.key_hold_ms / 1000.0

            for key in keys:
                controller.press(key)

            time.sleep(hold_s)

            for key in reversed(keys):
                controller.release(key)

            logger.info(f"Pressed: {keys_str}")
            return ActionResult(success=True, message=f"Pressed: {keys_str}")

        except Exception as e:
            logger.error(f"Failed to press keys: {e}")
            return ActionResult(success=False, error=str(e))

    def _parse_key_combination(self, keys_str: str) -> list[keyboard.Key | keyboard.KeyCode]:
        """Parse a key combination string.

        Args:
            keys_str: Key combination like "ctrl+c" or "alt+shift+tab".

        Returns:
            List of key objects to press.
        """
        keys = []
        parts = keys_str.lower().replace("-", "+").replace(" ", "+").split("+")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part in MODIFIER_KEYS:
                keys.append(MODIFIER_KEYS[part])
            elif part in SPECIAL_KEYS:
                keys.append(SPECIAL_KEYS[part])
            elif len(part) == 1:
                keys.append(keyboard.KeyCode.from_char(part))
            else:
                logger.warning(f"Unknown key: {part}")
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
