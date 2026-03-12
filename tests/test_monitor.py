"""Tests for monitor command wake word detection."""

import pytest

from yawrungay.main import _extract_command_after_wake_word, _find_wake_word, MonitorState


class TestFindWakeWord:
    """Tests for _find_wake_word function."""

    def test_find_wake_word_at_start(self):
        """Test finding wake word at the beginning."""
        assert _find_wake_word("yawrungay type hello", "yawrungay") == 0

    def test_find_wake_word_in_middle(self):
        """Test finding wake word in the middle."""
        assert _find_wake_word("hey yawrungay type hello", "yawrungay") == 4

    def test_find_wake_word_case_insensitive(self):
        """Test case insensitive matching."""
        assert _find_wake_word("YAWRUNGAY type hello", "yawrungay") == 0
        assert _find_wake_word("Yawrungay type hello", "yawrungay") == 0
        assert _find_wake_word("yawrungay type hello", "YAWRUNGAY") == 0

    def test_find_wake_word_not_found(self):
        """Test when wake word is not present."""
        assert _find_wake_word("type hello world", "yawrungay") == -1

    def test_find_wake_word_custom(self):
        """Test with custom wake word."""
        assert _find_wake_word("computer type hello", "computer") == 0
        assert _find_wake_word("hello computer", "computer") == 6

    def test_find_wake_word_empty_text(self):
        """Test with empty text."""
        assert _find_wake_word("", "yawrungay") == -1

    def test_find_wake_word_partial_match(self):
        """Test that partial matches don't count."""
        # 'yaw' is a substring but not the full wake word
        assert _find_wake_word("yaw type hello", "yawrungay") == -1


class TestExtractCommandAfterWakeWord:
    """Tests for _extract_command_after_wake_word function."""

    def test_extract_command_simple(self):
        """Test extracting command after wake word."""
        result = _extract_command_after_wake_word("yawrungay type hello", "yawrungay")
        assert result == "type hello"

    def test_extract_command_with_leading_space(self):
        """Test that leading/trailing whitespace is stripped."""
        result = _extract_command_after_wake_word("yawrungay   type hello  ", "yawrungay")
        assert result == "type hello"

    def test_extract_command_no_command(self):
        """Test when only wake word is present."""
        result = _extract_command_after_wake_word("yawrungay", "yawrungay")
        assert result == ""

    def test_extract_command_wake_word_only_with_space(self):
        """Test wake word with trailing space but no command."""
        result = _extract_command_after_wake_word("yawrungay   ", "yawrungay")
        assert result == ""

    def test_extract_command_case_insensitive(self):
        """Test case insensitive extraction."""
        result = _extract_command_after_wake_word("YAWRUNGAY type hello", "yawrungay")
        assert result == "type hello"

    def test_extract_command_no_wake_word(self):
        """Test when wake word is not present."""
        result = _extract_command_after_wake_word("type hello", "yawrungay")
        assert result == ""

    def test_extract_command_wake_word_in_middle(self):
        """Test extracting command when wake word is not at start."""
        result = _extract_command_after_wake_word("hey yawrungay open firefox", "yawrungay")
        assert result == "open firefox"

    def test_extract_command_complex(self):
        """Test with more complex commands."""
        result = _extract_command_after_wake_word("yawrungay press control shift t", "yawrungay")
        assert result == "press control shift t"

    def test_extract_command_with_comma(self):
        """Test extracting command when comma follows wake word."""
        result = _extract_command_after_wake_word("Alexa, type hello world", "Alexa")
        assert result == "type hello world"

    def test_extract_command_with_exclamation(self):
        """Test extracting command when exclamation follows wake word."""
        result = _extract_command_after_wake_word("Alexa! type hello", "Alexa")
        assert result == "type hello"

    def test_extract_command_with_multiple_punctuation(self):
        """Test extracting command with multiple punctuation marks."""
        result = _extract_command_after_wake_word("Alexa!!! type hello", "Alexa")
        assert result == "type hello"

    def test_extract_command_with_period(self):
        """Test extracting command when period follows wake word."""
        result = _extract_command_after_wake_word("Alexa. type hello", "Alexa")
        assert result == "type hello"

    def test_extract_command_with_question_mark(self):
        """Test extracting command when question mark follows wake word."""
        result = _extract_command_after_wake_word("Alexa? type hello", "Alexa")
        assert result == "type hello"

    def test_extract_command_with_mixed_punctuation_and_space(self):
        """Test extracting command with mixed punctuation and spaces."""
        result = _extract_command_after_wake_word("Alexa,  type hello world", "Alexa")
        assert result == "type hello world"


class TestMonitorState:
    """Tests for MonitorState class."""

    def test_state_values(self):
        """Test state values."""
        assert MonitorState.WAITING == "waiting"
        assert MonitorState.LISTENING_FOR_COMMAND == "listening"
