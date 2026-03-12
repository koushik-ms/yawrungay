"""Tests for command parsing module."""

import tempfile
from pathlib import Path

import pytest

from yawrungay.parsing.base import ParsedCommand, Phrase
from yawrungay.parsing.parser import CommandParser
from yawrungay.parsing.patterns import BUILTIN_PATTERNS
from yawrungay.parsing.phrases import PhraseFileLoader


class TestPhrase:
    """Test cases for Phrase dataclass."""

    def test_creation(self):
        """Test creating a phrase."""
        phrase = Phrase(text="hello world", action="type hello")
        assert phrase.text == "hello world"
        assert phrase.action == "type hello"
        assert phrase.tags == []
        assert phrase.source_file == ""

    def test_with_tags(self):
        """Test phrase with tags."""
        phrase = Phrase(
            text="test",
            action="type test",
            tags=["@transcribe"],
            source_file="/path/to/file.phrases",
        )
        assert phrase.tags == ["@transcribe"]
        assert phrase.source_file == "/path/to/file.phrases"


class TestParsedCommand:
    """Test cases for ParsedCommand dataclass."""

    def test_creation(self):
        """Test creating a parsed command."""
        cmd = ParsedCommand(
            action_type="type",
            arguments={"text": "hello"},
            raw_phrase="type hello",
        )
        assert cmd.action_type == "type"
        assert cmd.arguments == {"text": "hello"}
        assert cmd.raw_phrase == "type hello"
        assert cmd.from_fallback is False

    def test_from_fallback(self):
        """Test command from fallback matching."""
        cmd = ParsedCommand(
            action_type="type",
            arguments={"text": "hello"},
            raw_phrase="type hello",
            from_fallback=True,
        )
        assert cmd.from_fallback is True


class TestBuiltinPatterns:
    """Test cases for built-in patterns."""

    def test_type_pattern(self):
        """Test type command pattern."""
        pattern = [p for p in BUILTIN_PATTERNS if p.action_type == "type"][0]
        assert pattern.has_fallback is True

        match = pattern.pattern.match("type hello world")
        assert match is not None
        args = pattern.extract_args(match)
        assert args == {"text": "hello world"}

    def test_type_pattern_case_insensitive(self):
        """Test type pattern is case insensitive."""
        pattern = [p for p in BUILTIN_PATTERNS if p.action_type == "type"][0]
        match = pattern.pattern.match("TYPE hello")
        assert match is not None

    def test_press_pattern_no_fallback(self):
        """Test press command pattern has no fallback."""
        pattern = [p for p in BUILTIN_PATTERNS if p.action_type == "press"][0]
        assert pattern.has_fallback is False

        match = pattern.pattern.match("press ctrl+c")
        assert match is not None
        args = pattern.extract_args(match)
        assert args == {"keys": "ctrl+c"}

    def test_open_pattern(self):
        """Test open command pattern."""
        pattern = [p for p in BUILTIN_PATTERNS if p.action_type == "open"][0]
        assert pattern.has_fallback is True

        match = pattern.pattern.match("open firefox")
        assert match is not None
        args = pattern.extract_args(match)
        assert args == {"app": "firefox"}

    def test_run_pattern(self):
        """Test run command pattern (alias for open)."""
        pattern = [p for p in BUILTIN_PATTERNS if p.action_type == "run"][0]
        assert pattern.has_fallback is True

        match = pattern.pattern.match("run firefox")
        assert match is not None
        args = pattern.extract_args(match)
        assert args == {"app": "firefox"}

    def test_mouse_pattern_no_fallback(self):
        """Test mouse command pattern has no fallback."""
        pattern = [p for p in BUILTIN_PATTERNS if p.action_type == "mouse"][0]
        assert pattern.has_fallback is False

        match = pattern.pattern.match("mouse click left")
        assert match is not None
        args = pattern.extract_args(match)
        assert args == {"action": "click left"}


class TestPhraseFileLoader:
    """Test cases for PhraseFileLoader."""

    def test_parse_simple_line(self):
        """Test parsing a simple phrase line."""
        loader = PhraseFileLoader()
        phrase = loader._parse_line("hello: type hello", "test.phrases")
        assert phrase is not None
        assert phrase.text == "hello"
        assert phrase.action == "type hello"

    def test_parse_comment_line(self):
        """Test that comment lines are ignored."""
        loader = PhraseFileLoader()
        phrase = loader._parse_line("# this is a comment", "test.phrases")
        assert phrase is None

    def test_parse_empty_line(self):
        """Test that empty lines are ignored."""
        loader = PhraseFileLoader()
        phrase = loader._parse_line("", "test.phrases")
        assert phrase is None

    def test_parse_line_with_tags(self):
        """Test parsing line with tags."""
        loader = PhraseFileLoader()
        phrase = loader._parse_line("@transcribe scribe: type hello", "test.phrases")
        assert phrase is not None
        assert phrase.text == "scribe"
        assert phrase.action == "type hello"
        assert phrase.tags == ["@transcribe"]

    def test_parse_invalid_line(self):
        """Test parsing invalid line."""
        loader = PhraseFileLoader()
        phrase = loader._parse_line("no colon here", "test.phrases")
        assert phrase is None

    def test_join_continuation_lines(self):
        """Test joining lines ending with backslash."""
        loader = PhraseFileLoader()
        lines = ["hello: type hello \\", "world"]
        result = loader._join_continuation_lines(lines)
        assert result == ["hello: type hello world"]

    def test_load_file(self):
        """Test loading a phrase file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".phrases", delete=False) as f:
            f.write("# Test phrase file\n")
            f.write("hello: type hello\n")
            f.write("copy: press ctrl+c\n")
            f.flush()

            loader = PhraseFileLoader()
            phrases = loader.load_file(Path(f.name))

            assert len(phrases) == 2
            assert phrases[0].text == "hello"
            assert phrases[1].text == "copy"

            Path(f.name).unlink()


class TestCommandParser:
    """Test cases for CommandParser."""

    def test_exact_phrase_match(self):
        """Test matching an exact phrase."""
        phrases = {
            "hello": Phrase(text="hello", action="type hello"),
        }
        parser = CommandParser(phrases=phrases)

        result = parser.parse("hello")
        assert result is not None
        assert result.action_type == "type"
        assert result.arguments == {"text": "hello"}
        assert result.from_fallback is False

    def test_exact_phrase_match_case_insensitive(self):
        """Test phrase matching is case insensitive."""
        phrases = {
            "hello": Phrase(text="hello", action="type hello"),
        }
        parser = CommandParser(phrases=phrases)

        result = parser.parse("HELLO")
        assert result is not None
        assert result.action_type == "type"

    def test_type_fallback(self):
        """Test type command fallback when no phrase matches."""
        parser = CommandParser(phrases={})

        result = parser.parse("type hello world")
        assert result is not None
        assert result.action_type == "type"
        assert result.arguments == {"text": "hello world"}
        assert result.from_fallback is True

    def test_open_fallback(self):
        """Test open command fallback when no phrase matches."""
        parser = CommandParser(phrases={})

        result = parser.parse("open firefox")
        assert result is not None
        assert result.action_type == "open"
        assert result.arguments == {"app": "firefox"}
        assert result.from_fallback is True

    def test_press_no_fallback(self):
        """Test press command requires phrase definition."""
        parser = CommandParser(phrases={})

        result = parser.parse("press ctrl+c")
        assert result is None

    def test_mouse_no_fallback(self):
        """Test mouse command requires phrase definition."""
        parser = CommandParser(phrases={})

        result = parser.parse("mouse click left")
        assert result is None

    def test_no_match(self):
        """Test no match returns None."""
        parser = CommandParser(phrases={})

        result = parser.parse("random text that doesn't match")
        assert result is None

    def test_phrase_overrides_fallback(self):
        """Test phrase definition takes priority over fallback."""
        phrases = {
            "type hello": Phrase(text="type hello", action="type world"),
        }
        parser = CommandParser(phrases=phrases)

        result = parser.parse("type hello")
        assert result is not None
        assert result.arguments == {"text": "world"}
        assert result.from_fallback is False

    def test_add_phrase(self):
        """Test adding a phrase."""
        parser = CommandParser(phrases={})

        parser.add_phrase(Phrase(text="test", action="type tested"))
        assert "test" in parser.phrases

        result = parser.parse("test")
        assert result is not None
        assert result.arguments == {"text": "tested"}

    def test_remove_phrase(self):
        """Test removing a phrase."""
        phrases = {
            "hello": Phrase(text="hello", action="type hello"),
        }
        parser = CommandParser(phrases=phrases)

        removed = parser.remove_phrase("hello")
        assert removed is True
        assert "hello" not in parser.phrases

        # Now "hello" should match the fallback pattern (type command)
        result = parser.parse("hello")
        # "hello" alone doesn't match the "type <text>" pattern
        # because it's just "hello", not "type hello"
        # So it should return None
        assert result is None
