"""Action executor for Yawrungay."""

import logging
from typing import Optional

from yawrungay.actions.base import ActionContext, ActionResult, BaseAction
from yawrungay.actions.keyboard import KeyboardAction
from yawrungay.actions.mouse import MouseAction
from yawrungay.actions.shell import ShellAction
from yawrungay.parsing.base import ParsedCommand

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes parsed commands using registered actions.

    The executor maintains a registry of action handlers and dispatches
    commands to the appropriate handler based on action type.
    """

    def __init__(self, context: Optional[ActionContext] = None):
        """Initialize the executor.

        Args:
            context: Execution context with configuration. Uses defaults if not provided.
        """
        self._context = context or ActionContext()
        self._actions: dict[str, BaseAction] = {}
        self._register_builtin_actions()

    def _register_builtin_actions(self) -> None:
        """Register built-in action handlers."""
        self.register_action(KeyboardAction())
        self.register_action(MouseAction())
        self.register_action(ShellAction())

    def register_action(self, action: BaseAction) -> None:
        """Register an action handler.

        Args:
            action: Action handler to register.
        """
        action_types = self._get_action_types(action)
        for action_type in action_types:
            self._actions[action_type] = action
            logger.debug(f"Registered action: {action_type}")

    def _get_action_types(self, action: BaseAction) -> list[str]:
        """Get the action types this handler supports.

        Args:
            action: Action handler.

        Returns:
            List of action types this handler supports.
        """
        name = action.name.lower()
        if name == "keyboard":
            return ["type", "press"]
        elif name == "mouse":
            return ["mouse"]
        elif name == "shell":
            return ["open", "run"]
        else:
            return [name]

    def execute(self, command: ParsedCommand) -> ActionResult:
        """Execute a parsed command.

        Args:
            command: ParsedCommand to execute.

        Returns:
            ActionResult indicating success or failure.
        """
        action_type = command.action_type.lower()
        action = self._actions.get(action_type)

        if not action:
            logger.error(f"Unknown action type: {action_type}")
            return ActionResult(success=False, error=f"Unknown action type: {action_type}")

        validation_error = action.validate_arguments(command.arguments)
        if validation_error:
            logger.error(f"Invalid arguments: {validation_error}")
            return ActionResult(success=False, error=validation_error)

        logger.info(f"Executing: {action_type} with {command.arguments}")
        result = action.execute(command.arguments, self._context)

        if result.success:
            logger.info(f"Action succeeded: {result.message}")
        else:
            logger.error(f"Action failed: {result.error}")

        return result

    def get_registered_actions(self) -> list[str]:
        """Get list of registered action types.

        Returns:
            List of action type names.
        """
        return list(self._actions.keys())

    def set_context(self, context: ActionContext) -> None:
        """Set the execution context.

        Args:
            context: New execution context.
        """
        self._context = context

    @property
    def context(self) -> ActionContext:
        """Get the current execution context."""
        return self._context
