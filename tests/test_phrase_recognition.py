"""Tests for phrase recognition with wake word extraction and punctuation handling.

This test suite verifies that:
1. Wake word extraction correctly removes trailing punctuation
2. All 29 default phrases are recognized correctly
3. Phrases work with various punctuation patterns
4. Command parsing works end-to-end after wake word extraction
"""

import pytest

from yawrungay.main import _extract_command_after_wake_word, _find_wake_word
from yawrungay.parsing import CommandParser, PhraseFileLoader


class TestWakeWordExtraction:
    """Test wake word detection and command extraction."""

    WAKE_WORD = "Hey Jarvis"

    def test_find_wake_word_exact(self):
        """Test finding exact wake word."""
        text = "Hey Jarvis copy"
        assert _find_wake_word(text, self.WAKE_WORD) == 0

    def test_find_wake_word_with_prefix(self):
        """Test finding wake word with text before it."""
        text = "Please Hey Jarvis copy"
        idx = _find_wake_word(text, self.WAKE_WORD)
        assert idx == 7

    def test_find_wake_word_case_insensitive(self):
        """Test wake word detection is case insensitive."""
        text = "hey jarvis copy"
        assert _find_wake_word(text, self.WAKE_WORD) >= 0

    def test_find_wake_word_not_found(self):
        """Test wake word not found returns -1."""
        text = "please repeat that"
        assert _find_wake_word(text, self.WAKE_WORD) == -1

    def test_extract_simple_command(self):
        """Test extracting simple command after wake word."""
        text = "Hey Jarvis copy"
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == "copy"

    def test_extract_with_trailing_period(self):
        """Test trailing period is removed."""
        text = "Hey Jarvis, double click."
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == "double click"
        assert not cmd.endswith(".")

    def test_extract_with_trailing_exclamation(self):
        """Test trailing exclamation mark is removed."""
        text = "Hey Jarvis, save!"
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == "save"

    def test_extract_with_multiple_trailing_punctuation(self):
        """Test multiple trailing punctuation marks are removed."""
        text = "Hey Jarvis, undo!!"
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == "undo"

    def test_extract_with_leading_punctuation(self):
        """Test leading punctuation after wake word is removed."""
        text = "Hey Jarvis, copy"
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == "copy"

    def test_extract_with_leading_and_trailing_punctuation(self):
        """Test both leading and trailing punctuation are removed."""
        text = "Hey Jarvis, new tab."
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == "new tab"

    def test_extract_with_multiple_spaces(self):
        """Test multiple spaces are handled correctly."""
        text = "Hey Jarvis,  paste  "
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == "paste"

    def test_extract_empty_after_punctuation(self):
        """Test extraction returns empty string for just wake word + punctuation."""
        text = "Hey Jarvis,"
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == ""

    def test_extract_with_question_mark(self):
        """Test question mark is removed."""
        text = "Hey Jarvis, refresh?"
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == "refresh"

    def test_extract_with_comma_and_semicolon(self):
        """Test various punctuation marks are removed."""
        text = "Hey Jarvis, open terminal;"
        cmd = _extract_command_after_wake_word(text, self.WAKE_WORD)
        assert cmd == "open terminal"


class TestPhraseRecognitionWithPunctuation:
    """Test phrase recognition after punctuation-aware wake word extraction."""

    WAKE_WORD = "Hey Jarvis"

    @pytest.fixture
    def parser(self):
        """Load phrase parser with default phrases."""
        phrase_loader = PhraseFileLoader()
        return CommandParser(phrase_loader=phrase_loader)

    def _simulate_utterance(self, parser, utterance):
        """Simulate complete flow: wake word extraction → parsing."""
        command_text = _extract_command_after_wake_word(utterance, self.WAKE_WORD)
        if not command_text:
            return None
        return parser.parse(command_text)

    def test_double_click_with_punctuation(self, parser):
        """Test 'double click' phrase with trailing period."""
        utterance = "Hey Jarvis, double click."
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is not None
        assert parsed.action_type == "mouse"
        assert parsed.arguments == {"action": "double left"}

    def test_copy_with_punctuation(self, parser):
        """Test 'copy' phrase with trailing period."""
        utterance = "Hey Jarvis, copy."
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is not None
        assert parsed.action_type == "press"
        assert parsed.arguments == {"keys": "ctrl+c"}

    def test_new_tab_with_punctuation(self, parser):
        """Test 'new tab' phrase with punctuation."""
        utterance = "Hey Jarvis, new tab!"
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is not None
        assert parsed.action_type == "press"
        assert parsed.arguments == {"keys": "ctrl+t"}

    def test_paste_with_multiple_punctuation(self, parser):
        """Test 'paste' phrase with multiple trailing punctuation."""
        utterance = "Hey Jarvis, paste!!"
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is not None
        assert parsed.action_type == "press"
        assert parsed.arguments == {"keys": "ctrl+v"}

    def test_right_click_with_comma(self, parser):
        """Test 'right click' phrase with comma and period."""
        utterance = "Hey Jarvis, right click."
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is not None
        assert parsed.action_type == "mouse"
        assert parsed.arguments == {"action": "click right"}

    def test_scroll_down_with_question_mark(self, parser):
        """Test 'scroll down' phrase with question mark."""
        utterance = "Hey Jarvis, scroll down?"
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is not None
        assert parsed.action_type == "mouse"
        assert parsed.arguments == {"action": "scroll down"}

    def test_switch_window_with_exclamation(self, parser):
        """Test 'switch window' phrase with exclamation."""
        utterance = "Hey Jarvis, switch window!"
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is not None
        assert parsed.action_type == "press"
        assert parsed.arguments == {"keys": "alt+tab"}

    def test_open_browser_with_punctuation(self, parser):
        """Test 'open browser' phrase with period."""
        utterance = "Hey Jarvis, open browser."
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is not None
        assert parsed.action_type == "open"
        assert parsed.arguments == {"app": "firefox"}

    def test_case_insensitivity_with_punctuation(self, parser):
        """Test case insensitivity works with punctuation."""
        utterance = "Hey Jarvis, COPY."
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is not None
        assert parsed.action_type == "press"

    def test_unknown_phrase_not_recognized(self, parser):
        """Test unknown phrase returns None."""
        utterance = "Hey Jarvis, blah blah."
        parsed = self._simulate_utterance(parser, utterance)
        assert parsed is None


class TestAllDefaultPhrases:
    """Test all 29 default phrases are recognized correctly."""

    WAKE_WORD = "Hey Jarvis"

    # Expected 29 phrases
    EXPECTED_PHRASES = {
        # Keyboard shortcuts (10)
        "copy": ("press", "ctrl+c"),
        "paste": ("press", "ctrl+v"),
        "undo": ("press", "ctrl+z"),
        "redo": ("press", "ctrl+shift+z"),
        "select all": ("press", "ctrl+a"),
        "save": ("press", "ctrl+s"),
        "find": ("press", "ctrl+f"),
        "new": ("press", "ctrl+n"),
        "close": ("press", "ctrl+w"),
        "quit": ("press", "ctrl+q"),
        # Browser shortcuts (7)
        "new tab": ("press", "ctrl+t"),
        "close tab": ("press", "ctrl+w"),
        "next tab": ("press", "ctrl+tab"),
        "previous tab": ("press", "ctrl+shift+tab"),
        "refresh": ("press", "ctrl+r"),
        "back": ("press", "alt+left"),
        "forward": ("press", "alt+right"),
        # Window management (3)
        "switch window": ("press", "alt+tab"),
        "minimize": ("press", "super+down"),
        "maximize": ("press", "super+up"),
        # Application aliases (4)
        "open browser": ("open", "firefox"),
        "open editor": ("open", "code"),
        "open terminal": ("open", "gnome-terminal"),
        "open files": ("open", "nautilus"),
        # Mouse actions (5)
        "click": ("mouse", "click left"),
        "right click": ("mouse", "click right"),
        "double click": ("mouse", "double left"),
        "scroll up": ("mouse", "scroll up"),
        "scroll down": ("mouse", "scroll down"),
    }

    @pytest.fixture
    def parser(self):
        """Load phrase parser with default phrases."""
        phrase_loader = PhraseFileLoader()
        return CommandParser(phrase_loader=phrase_loader)

    def test_all_phrases_loaded(self, parser):
        """Test that all 29 expected phrases are loaded."""
        assert len(parser.phrases) == 29
        for phrase_text in self.EXPECTED_PHRASES.keys():
            assert phrase_text in parser.phrases, f"Phrase '{phrase_text}' not found"

    @pytest.mark.parametrize(
        "phrase_text,expected_action_type,expected_arg",
        [(phrase, action_type, arg_value) for phrase, (action_type, arg_value) in EXPECTED_PHRASES.items()],
    )
    def test_phrase_with_period(self, parser, phrase_text, expected_action_type, expected_arg):
        """Test each phrase is recognized correctly with trailing period."""
        utterance = f"Hey Jarvis, {phrase_text}."
        command_text = _extract_command_after_wake_word(utterance, self.WAKE_WORD)
        parsed = parser.parse(command_text)

        assert parsed is not None, f"Failed to parse phrase: {phrase_text}"
        assert parsed.action_type == expected_action_type, f"Phrase '{phrase_text}' has wrong action type"

    @pytest.mark.parametrize(
        "phrase_text,expected_action_type,expected_arg",
        [(phrase, action_type, arg_value) for phrase, (action_type, arg_value) in EXPECTED_PHRASES.items()],
    )
    def test_phrase_with_exclamation(self, parser, phrase_text, expected_action_type, expected_arg):
        """Test each phrase is recognized correctly with trailing exclamation."""
        utterance = f"Hey Jarvis, {phrase_text}!"
        command_text = _extract_command_after_wake_word(utterance, self.WAKE_WORD)
        parsed = parser.parse(command_text)

        assert parsed is not None, f"Failed to parse phrase: {phrase_text}"
        assert parsed.action_type == expected_action_type, f"Phrase '{phrase_text}' has wrong action type"

    @pytest.mark.parametrize(
        "phrase_text",
        list(EXPECTED_PHRASES.keys()),
    )
    def test_phrase_without_punctuation(self, parser, phrase_text):
        """Test each phrase is recognized correctly without trailing punctuation."""
        utterance = f"Hey Jarvis, {phrase_text}"
        command_text = _extract_command_after_wake_word(utterance, self.WAKE_WORD)
        parsed = parser.parse(command_text)

        assert parsed is not None, f"Failed to parse phrase: {phrase_text}"


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    WAKE_WORD = "Hey Jarvis"

    @pytest.fixture
    def parser(self):
        """Load phrase parser with default phrases."""
        phrase_loader = PhraseFileLoader()
        return CommandParser(phrase_loader=phrase_loader)

    def test_multiple_spaces_around_phrase(self, parser):
        """Test phrase with multiple spaces around it."""
        utterance = "Hey Jarvis,  copy  ."
        command_text = _extract_command_after_wake_word(utterance, self.WAKE_WORD)
        parsed = parser.parse(command_text)
        assert parsed is not None

    def test_phrase_with_all_punctuation_types(self, parser):
        """Test phrase with various punctuation combinations."""
        punctuation_tests = [
            "Hey Jarvis, copy.",
            "Hey Jarvis, copy!",
            "Hey Jarvis, copy?",
            "Hey Jarvis, copy,",
            "Hey Jarvis, copy;",
            "Hey Jarvis, copy:",
        ]
        for utterance in punctuation_tests:
            command_text = _extract_command_after_wake_word(utterance, self.WAKE_WORD)
            parsed = parser.parse(command_text)
            assert parsed is not None, f"Failed on utterance: {utterance}"

    def test_no_wake_word_returns_none(self, parser):
        """Test that utterance without wake word extracts empty command."""
        utterance = "just type copy"
        command_text = _extract_command_after_wake_word(utterance, self.WAKE_WORD)
        assert command_text == ""

    def test_wake_word_only_with_punctuation(self, parser):
        """Test wake word alone with punctuation."""
        utterance = "Hey Jarvis."
        command_text = _extract_command_after_wake_word(utterance, self.WAKE_WORD)
        assert command_text == ""
        parsed = parser.parse(command_text) if command_text else None
        assert parsed is None

    def test_phrase_recognition_works_with_type_command(self, parser):
        """Test that 'type' command works through wake word extraction."""
        utterance = "Hey Jarvis, type hello world."
        command_text = _extract_command_after_wake_word(utterance, self.WAKE_WORD)
        parsed = parser.parse(command_text)
        assert parsed is not None
        assert parsed.action_type == "type"
        assert parsed.arguments["text"] == "hello world"
