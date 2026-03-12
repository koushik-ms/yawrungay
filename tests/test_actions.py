"""Tests for actions module."""

from unittest.mock import MagicMock, patch

import pytest

from yawrungay.actions.base import ActionContext, ActionResult, BaseAction
from yawrungay.actions.executor import ActionExecutor
from yawrungay.actions.keyboard import KeyboardAction
from yawrungay.actions.mouse import MouseAction
from yawrungay.actions.shell import ShellAction, is_safe_command
from yawrungay.parsing.base import ParsedCommand


class TestActionResult:
    """Test cases for ActionResult."""

    def test_success_result(self):
        """Test successful result."""
        result = ActionResult(success=True, message="Done")
        assert result.success is True
        assert result.message == "Done"
        assert result.error is None

    def test_failure_result(self):
        """Test failure result."""
        result = ActionResult(success=False, error="Failed")
        assert result.success is False
        assert result.error == "Failed"

    def test_result_with_data(self):
        """Test result with data."""
        result = ActionResult(success=True, data={"key": "value"})
        assert result.data == {"key": "value"}


class TestActionContext:
    """Test cases for ActionContext."""

    def test_default_values(self):
        """Test default context values."""
        context = ActionContext()
        assert context.key_delay_ms == 50
        assert context.key_hold_ms == 50
        assert context.type_delay_ms == 30
        assert context.scroll_amount == 3
        assert context.shell_timeout == 5.0

    def test_custom_values(self):
        """Test custom context values."""
        context = ActionContext(
            key_delay_ms=100,
            shell_timeout=10.0,
        )
        assert context.key_delay_ms == 100
        assert context.shell_timeout == 10.0


class TestKeyboardAction:
    """Test cases for KeyboardAction."""

    def test_name(self):
        """Test action name."""
        action = KeyboardAction()
        assert action.name == "keyboard"

    def test_validate_missing_arguments(self):
        """Test validation with missing arguments."""
        action = KeyboardAction()
        error = action.validate_arguments({})
        assert error is not None
        assert "Missing" in error

    def test_validate_valid_arguments(self):
        """Test validation with valid arguments."""
        action = KeyboardAction()
        error = action.validate_arguments({"text": "hello"})
        assert error is None

    def test_parse_single_key_xdotool(self):
        """Test parsing single key for xdotool."""
        action = KeyboardAction()
        combo = action._parse_keys_for_xdotool("a")
        assert combo == "a"

    def test_parse_modifier_combo_xdotool(self):
        """Test parsing modifier + key combo for xdotool."""
        action = KeyboardAction()
        combo = action._parse_keys_for_xdotool("ctrl+c")
        assert combo == "ctrl+c"

    def test_parse_multiple_modifiers_xdotool(self):
        """Test parsing multiple modifiers for xdotool."""
        action = KeyboardAction()
        combo = action._parse_keys_for_xdotool("ctrl+shift+t")
        assert combo == "ctrl+shift+t"

    def test_parse_special_key_xdotool(self):
        """Test parsing special key for xdotool."""
        action = KeyboardAction()
        combo = action._parse_keys_for_xdotool("enter")
        assert combo == "Return"

    def test_parse_unknown_key_xdotool(self):
        """Test parsing unknown key returns empty for xdotool."""
        action = KeyboardAction()
        combo = action._parse_keys_for_xdotool("unknownkey")
        assert combo == ""

    def test_backend_detection(self):
        """Test that backend is detected."""
        action = KeyboardAction()
        assert action.backend in ["ydotool", "xdotool", "pynput"]


class TestMouseAction:
    """Test cases for MouseAction."""

    def test_name(self):
        """Test action name."""
        action = MouseAction()
        assert action.name == "mouse"

    def test_validate_missing_arguments(self):
        """Test validation with missing arguments."""
        action = MouseAction()
        error = action.validate_arguments({})
        assert error is not None

    def test_validate_valid_arguments(self):
        """Test validation with valid arguments."""
        action = MouseAction()
        error = action.validate_arguments({"action": "click left"})
        assert error is None


class TestShellAction:
    """Test cases for ShellAction."""

    def test_name(self):
        """Test action name."""
        action = ShellAction()
        assert action.name == "shell"

    def test_is_safe_command_valid(self):
        """Test safe command detection."""
        assert is_safe_command("firefox") is True
        assert is_safe_command("code") is True
        assert is_safe_command("/usr/bin/ls") is True

    def test_is_safe_command_blocked(self):
        """Test blocked command detection."""
        assert is_safe_command("sudo vim") is False
        assert is_safe_command("sudo rm -rf /") is False
        assert is_safe_command("su -") is False
        assert is_safe_command("doas command") is False

    def test_validate_missing_arguments(self):
        """Test validation with missing arguments."""
        action = ShellAction()
        error = action.validate_arguments({})
        assert error is not None

    def test_validate_valid_arguments(self):
        """Test validation with valid arguments."""
        action = ShellAction()
        error = action.validate_arguments({"app": "firefox"})
        assert error is None

    @patch("yawrungay.actions.shell.shutil.which")
    def test_open_blocked_command(self, mock_which):
        """Test opening blocked command."""
        action = ShellAction()
        result = action.execute({"app": "sudo vim"}, ActionContext())
        assert result.success is False
        assert "forbidden" in result.error.lower()

    @patch("yawrungay.actions.shell.shutil.which")
    def test_open_not_found(self, mock_which):
        """Test opening non-existent application."""
        mock_which.return_value = None
        action = ShellAction()
        result = action.execute({"app": "nonexistentapp"}, ActionContext())
        assert result.success is False
        assert "not found" in result.error.lower()

    @patch("yawrungay.actions.shell.subprocess.Popen")
    @patch("yawrungay.actions.shell.shutil.which")
    def test_open_success(self, mock_which, mock_popen):
        """Test successful application open."""
        mock_which.return_value = "/usr/bin/firefox"
        mock_popen.return_value = MagicMock()

        action = ShellAction()
        result = action.execute({"app": "firefox"}, ActionContext())
        assert result.success is True
        mock_popen.assert_called_once()


class TestActionExecutor:
    """Test cases for ActionExecutor."""

    def test_initialization(self):
        """Test executor initialization."""
        executor = ActionExecutor()
        assert "type" in executor.get_registered_actions()
        assert "press" in executor.get_registered_actions()
        assert "open" in executor.get_registered_actions()
        assert "mouse" in executor.get_registered_actions()

    def test_execute_type_command(self):
        """Test executing type command."""
        executor = ActionExecutor()
        cmd = ParsedCommand(
            action_type="type",
            arguments={"text": "hello"},
            raw_phrase="type hello",
            from_fallback=True,
        )

        # Mock subprocess.run for xdotool/ydotool backends
        with patch("yawrungay.actions.keyboard.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = executor.execute(cmd)
            assert result.success is True

    def test_execute_unknown_action(self):
        """Test executing unknown action type."""
        executor = ActionExecutor()
        cmd = ParsedCommand(
            action_type="unknown",
            arguments={},
            raw_phrase="test",
        )
        result = executor.execute(cmd)
        assert result.success is False
        assert "Unknown action" in result.error

    def test_execute_invalid_arguments(self):
        """Test executing with invalid arguments."""
        executor = ActionExecutor()
        cmd = ParsedCommand(
            action_type="type",
            arguments={},  # Missing 'text' or 'keys'
            raw_phrase="test",
        )
        result = executor.execute(cmd)
        assert result.success is False

    def test_custom_context(self):
        """Test executor with custom context."""
        context = ActionContext(key_delay_ms=100, shell_timeout=10.0)
        executor = ActionExecutor(context=context)
        assert executor.context.key_delay_ms == 100
        assert executor.context.shell_timeout == 10.0

    def test_set_context(self):
        """Test setting context after creation."""
        executor = ActionExecutor()
        new_context = ActionContext(scroll_amount=5)
        executor.set_context(new_context)
        assert executor.context.scroll_amount == 5


class TestActionIntegration:
    """Integration tests for action execution flow."""

    def test_open_command_blocked_sudo(self):
        """Test that open command blocks sudo."""
        executor = ActionExecutor()
        cmd = ParsedCommand(
            action_type="open",
            arguments={"app": "sudo vim"},
            raw_phrase="open sudo vim",
            from_fallback=True,
        )
        result = executor.execute(cmd)
        assert result.success is False
        assert "forbidden" in result.error.lower()

    def test_run_command_alias_for_open(self):
        """Test that run command is alias for open."""
        executor = ActionExecutor()

        with patch("yawrungay.actions.shell.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/firefox"
            with patch("yawrungay.actions.shell.subprocess.Popen") as mock_popen:
                mock_popen.return_value = MagicMock()

                cmd = ParsedCommand(
                    action_type="run",
                    arguments={"app": "firefox"},
                    raw_phrase="run firefox",
                    from_fallback=True,
                )
                result = executor.execute(cmd)
                assert result.success is True
