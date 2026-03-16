"""Shell command actions with security filtering."""

import logging
import shutil
import subprocess
from typing import Any

from yawrungay.actions.base import ActionContext, ActionResult, BaseAction

logger = logging.getLogger(__name__)

FORBIDDEN_COMMANDS = ["sudo", "su", "doas", "pkexec", "gksudo", "gksu", "kdesu", "ksu"]


class ShellAction(BaseAction):
    """Shell command execution actions.

    Supports:
    - open: Open/launch application by name
    - run: Run shell command (alias for open)

    Security: Commands containing forbidden words (sudo, su, etc.) are blocked.
    """

    @property
    def name(self) -> str:
        """Get the action name."""
        return "shell"

    def execute(self, arguments: dict[str, Any], context: ActionContext) -> ActionResult:
        """Execute shell action.

        Args:
            arguments: Must contain 'app' for open/run commands.
            context: Execution context.

        Returns:
            ActionResult indicating success or failure.
        """
        if "app" in arguments:
            return self._open_application(arguments["app"], context)
        elif "command" in arguments:
            return self._run_command(arguments["command"], context)
        else:
            return ActionResult(success=False, error="Missing 'app' or 'command' argument")

    def _open_application(self, app_name: str, context: ActionContext) -> ActionResult:
        """Open or launch an application.

        Args:
            app_name: Name of the application to open.
            context: Execution context.

        Returns:
            ActionResult indicating success or failure.
        """
        if not self._is_safe_command(app_name):
            logger.warning(f"Blocked forbidden command: {app_name}")
            return ActionResult(
                success=False,
                error=f"Command '{app_name}' contains forbidden word (sudo, su, etc.)",
            )

        app_path = shutil.which(app_name)
        if not app_path:
            logger.warning(f"Application not found in PATH: {app_name}")
            return ActionResult(
                success=False,
                error=f"Application '{app_name}' not found in PATH",
            )

        try:
            subprocess.Popen(
                [app_path],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            logger.info(f"Opened application: {app_name}")
            return ActionResult(success=True, message=f"Opened: {app_name}")

        except Exception as e:
            logger.error(f"Failed to open application: {e}")
            return ActionResult(success=False, error=str(e))

    def _run_command(self, command: str, context: ActionContext) -> ActionResult:
        """Run a shell command.

        Args:
            command: Shell command to run.
            context: Execution context.

        Returns:
            ActionResult indicating success or failure.
        """
        if not self._is_safe_command(command):
            logger.warning(f"Blocked forbidden command: {command}")
            return ActionResult(
                success=False,
                error="Command contains forbidden word (sudo, su, etc.)",
            )

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=context.shell_timeout,
            )

            if result.returncode == 0:
                logger.info(f"Ran command: {command}")
                return ActionResult(
                    success=True,
                    message="Command executed successfully",
                    data={"stdout": result.stdout, "stderr": result.stderr},
                )
            else:
                logger.warning(f"Command failed with code {result.returncode}: {command}")
                return ActionResult(
                    success=False,
                    error=f"Command exited with code {result.returncode}",
                    data={"stdout": result.stdout, "stderr": result.stderr},
                )

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            return ActionResult(success=False, error=f"Command timed out after {context.shell_timeout}s")
        except Exception as e:
            logger.error(f"Failed to run command: {e}")
            return ActionResult(success=False, error=str(e))

    def _is_safe_command(self, command: str) -> bool:
        """Check if a command is safe to execute.

        Args:
            command: Command to check.

        Returns:
            True if safe, False if contains forbidden words.
        """
        cmd_lower = command.lower()
        return not any(forbidden in cmd_lower for forbidden in FORBIDDEN_COMMANDS)

    def validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        """Validate shell action arguments.

        Args:
            arguments: Arguments to validate.

        Returns:
            Error message if validation fails, None if valid.
        """
        if "app" not in arguments and "command" not in arguments:
            return "Missing 'app' or 'command' argument"

        if "app" in arguments and not isinstance(arguments["app"], str):
            return "'app' must be a string"

        if "command" in arguments and not isinstance(arguments["command"], str):
            return "'command' must be a string"

        return None


def is_safe_command(command: str) -> bool:
    """Check if a command is safe to execute.

    Args:
        command: Command to check.

    Returns:
        True if safe, False if contains forbidden words.
    """
    cmd_lower = command.lower()
    return not any(forbidden in cmd_lower for forbidden in FORBIDDEN_COMMANDS)


def find_in_path(command: str) -> str | None:
    """Find an executable in PATH.

    Args:
        command: Command name to find.

    Returns:
        Full path to command if found, None otherwise.
    """
    return shutil.which(command)
