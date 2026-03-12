"""Built-in command patterns with fallback behavior."""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class CommandPattern:
    """Represents a built-in command pattern.

    Attributes:
        action_type: The action type (type, press, open, mouse).
        pattern: Regex pattern to match the command.
        has_fallback: Whether this command can work without phrase definition.
        extract_args: Function to extract arguments from regex match.
    """

    action_type: str
    pattern: re.Pattern
    has_fallback: bool
    extract_args: Any


def _extract_type_args(match: re.Match) -> dict[str, str]:
    """Extract text argument from 'type <text>' command."""
    return {"text": match.group(1)}


def _extract_press_args(match: re.Match) -> dict[str, str]:
    """Extract keys argument from 'press <keys>' command."""
    return {"keys": match.group(1)}


def _extract_open_args(match: re.Match) -> dict[str, str]:
    """Extract app argument from 'open <app>' command."""
    return {"app": match.group(1)}


def _extract_run_args(match: re.Match) -> dict[str, str]:
    """Extract app argument from 'run <app>' command (alias for open)."""
    return {"app": match.group(1)}


def _extract_mouse_args(match: re.Match) -> dict[str, str]:
    """Extract action argument from 'mouse <action>' command."""
    return {"action": match.group(1)}


BUILTIN_PATTERNS: list[CommandPattern] = [
    CommandPattern(
        action_type="type",
        pattern=re.compile(r"^type\s+(.+)$", re.IGNORECASE),
        has_fallback=True,
        extract_args=_extract_type_args,
    ),
    CommandPattern(
        action_type="press",
        pattern=re.compile(r"^press\s+(.+)$", re.IGNORECASE),
        has_fallback=False,
        extract_args=_extract_press_args,
    ),
    CommandPattern(
        action_type="open",
        pattern=re.compile(r"^open\s+(.+)$", re.IGNORECASE),
        has_fallback=True,
        extract_args=_extract_open_args,
    ),
    CommandPattern(
        action_type="run",
        pattern=re.compile(r"^run\s+(.+)$", re.IGNORECASE),
        has_fallback=True,
        extract_args=_extract_run_args,
    ),
    CommandPattern(
        action_type="mouse",
        pattern=re.compile(r"^mouse\s+(.+)$", re.IGNORECASE),
        has_fallback=False,
        extract_args=_extract_mouse_args,
    ),
]
