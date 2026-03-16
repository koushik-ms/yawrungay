"""Base classes for actions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionResult:
    """Result of an action execution.

    Attributes:
        success: Whether the action succeeded.
        message: Human-readable message about the result.
        error: Error message if action failed.
        data: Additional data returned by the action.
    """

    success: bool
    message: str = ""
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        """Return string representation of ActionResult."""
        status = "✓" if self.success else "✗"
        return f"ActionResult({status}, {self.message or self.error})"


@dataclass
class ActionContext:
    """Context for action execution.

    Attributes:
        key_delay_ms: Delay between key presses in milliseconds.
        key_hold_ms: How long to hold a key in milliseconds.
        type_delay_ms: Delay between typed characters.
        type_hold_ms: How long to hold a typed character.
        scroll_amount: Lines to scroll per scroll action.
        shell_timeout: Timeout for shell commands in seconds.
    """

    key_delay_ms: int = 50
    key_hold_ms: int = 50
    type_delay_ms: int = 30
    type_hold_ms: int = 50
    scroll_amount: int = 3
    shell_timeout: float = 5.0


class BaseAction(ABC):
    """Abstract base class for all actions.

    All action implementations must inherit from this class
    and implement the execute method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the action name."""
        pass

    @abstractmethod
    def execute(self, arguments: dict[str, Any], context: ActionContext) -> ActionResult:
        """Execute the action.

        Args:
            arguments: Arguments for the action.
            context: Execution context with configuration.

        Returns:
            ActionResult indicating success or failure.
        """
        pass

    def validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        """Validate action arguments.

        Override this method to provide argument validation.

        Args:
            arguments: Arguments to validate.

        Returns:
            Error message if validation fails, None if valid.
        """
        return None
