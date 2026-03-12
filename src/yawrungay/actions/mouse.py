"""Mouse actions using pynput."""

import logging
import time
from typing import Any, Optional

from pynput import mouse

from yawrungay.actions.base import ActionContext, ActionResult, BaseAction

logger = logging.getLogger(__name__)

MOUSE_BUTTONS = {
    "left": mouse.Button.left,
    "middle": mouse.Button.middle,
    "right": mouse.Button.right,
}

SCROLL_DIRECTIONS = {
    "up": 1,
    "down": -1,
    "left": -1,
    "right": 1,
}


class MouseAction(BaseAction):
    """Mouse simulation actions.

    Supports:
    - click: Click mouse button (left, middle, right)
    - double: Double-click
    - scroll: Scroll up/down/left/right
    - move: Move cursor relative to current position
    - goto: Move cursor to absolute position (screen percentage)
    """

    @property
    def name(self) -> str:
        return "mouse"

    def execute(self, arguments: dict[str, Any], context: ActionContext) -> ActionResult:
        """Execute mouse action.

        Args:
            arguments: Must contain 'action' key with action specification.
            context: Execution context.

        Returns:
            ActionResult indicating success or failure.
        """
        action_str = arguments.get("action", "")
        if not action_str:
            return ActionResult(success=False, error="Missing 'action' argument")

        parts = action_str.lower().split()
        if not parts:
            return ActionResult(success=False, error="Empty action")

        action_type = parts[0]
        action_args = parts[1:] if len(parts) > 1 else []

        if action_type == "click":
            return self._click(action_args, context)
        elif action_type == "double":
            return self._double_click(action_args, context)
        elif action_type == "scroll":
            return self._scroll(action_args, context)
        elif action_type == "move":
            return self._move(action_args, context)
        elif action_type == "goto":
            return self._goto(action_args, context)
        else:
            return ActionResult(success=False, error=f"Unknown mouse action: {action_type}")

    def _click(self, args: list[str], context: ActionContext) -> ActionResult:
        """Click mouse button.

        Args:
            args: Button name (left, middle, right). Default: left.
            context: Execution context.

        Returns:
            ActionResult indicating success.
        """
        button_name = args[0] if args else "left"
        button = MOUSE_BUTTONS.get(button_name)

        if not button:
            return ActionResult(success=False, error=f"Unknown button: {button_name}")

        try:
            controller = mouse.Controller()
            controller.click(button)

            logger.info(f"Clicked: {button_name}")
            return ActionResult(success=True, message=f"Clicked: {button_name}")

        except Exception as e:
            logger.error(f"Failed to click: {e}")
            return ActionResult(success=False, error=str(e))

    def _double_click(self, args: list[str], context: ActionContext) -> ActionResult:
        """Double-click mouse button.

        Args:
            args: Button name (left, middle, right). Default: left.
            context: Execution context.

        Returns:
            ActionResult indicating success.
        """
        button_name = args[0] if args else "left"
        button = MOUSE_BUTTONS.get(button_name)

        if not button:
            return ActionResult(success=False, error=f"Unknown button: {button_name}")

        try:
            controller = mouse.Controller()
            controller.click(button, 2)

            logger.info(f"Double-clicked: {button_name}")
            return ActionResult(success=True, message=f"Double-clicked: {button_name}")

        except Exception as e:
            logger.error(f"Failed to double-click: {e}")
            return ActionResult(success=False, error=str(e))

    def _scroll(self, args: list[str], context: ActionContext) -> ActionResult:
        """Scroll mouse wheel.

        Args:
            args: Direction (up, down, left, right) and optional amount.
            context: Execution context.

        Returns:
            ActionResult indicating success.
        """
        if not args:
            return ActionResult(success=False, error="Missing scroll direction")

        direction = args[0]
        amount = context.scroll_amount

        if len(args) > 1:
            try:
                amount = int(args[1])
            except ValueError:
                pass

        if direction not in SCROLL_DIRECTIONS:
            return ActionResult(success=False, error=f"Unknown scroll direction: {direction}")

        try:
            controller = mouse.Controller()
            scroll_value = SCROLL_DIRECTIONS[direction] * amount

            if direction in ("up", "down"):
                controller.scroll(0, scroll_value)
            else:
                controller.scroll(scroll_value, 0)

            logger.info(f"Scrolled: {direction} by {amount}")
            return ActionResult(success=True, message=f"Scrolled: {direction}")

        except Exception as e:
            logger.error(f"Failed to scroll: {e}")
            return ActionResult(success=False, error=str(e))

    def _move(self, args: list[str], context: ActionContext) -> ActionResult:
        """Move mouse relative to current position.

        Args:
            args: dx and dy in pixels.
            context: Execution context.

        Returns:
            ActionResult indicating success.
        """
        if len(args) < 2:
            return ActionResult(success=False, error="Move requires dx and dy arguments")

        try:
            dx = int(args[0])
            dy = int(args[1])

            controller = mouse.Controller()
            controller.move(dx, dy)

            logger.info(f"Moved mouse: {dx}, {dy}")
            return ActionResult(success=True, message=f"Moved: {dx}, {dy}")

        except ValueError:
            return ActionResult(success=False, error="dx and dy must be integers")
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return ActionResult(success=False, error=str(e))

    def _goto(self, args: list[str], context: ActionContext) -> ActionResult:
        """Move mouse to absolute position (screen percentage).

        Args:
            args: x and y as percentages (0.0 to 1.0).
            context: Execution context.

        Returns:
            ActionResult indicating success.
        """
        if len(args) < 2:
            return ActionResult(success=False, error="Goto requires x and y arguments")

        try:
            x_pct = float(args[0])
            y_pct = float(args[1])

            if not (0.0 <= x_pct <= 1.0 and 0.0 <= y_pct <= 1.0):
                return ActionResult(success=False, error="x and y must be between 0.0 and 1.0")

            controller = mouse.Controller()
            screen_width, screen_height = controller.position

            x = int(screen_width * x_pct)
            y = int(screen_height * y_pct)

            controller.position = (x, y)

            logger.info(f"Moved mouse to: {x_pct:.2f}, {y_pct:.2f}")
            return ActionResult(success=True, message=f"Moved to: {x_pct:.2f}, {y_pct:.2f}")

        except ValueError:
            return ActionResult(success=False, error="x and y must be floats")
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return ActionResult(success=False, error=str(e))

    def validate_arguments(self, arguments: dict[str, Any]) -> Optional[str]:
        """Validate mouse action arguments.

        Args:
            arguments: Arguments to validate.

        Returns:
            Error message if validation fails, None if valid.
        """
        if "action" not in arguments:
            return "Missing 'action' argument"

        if not isinstance(arguments["action"], str):
            return "'action' must be a string"

        return None
