"""Data structures for command parsing."""

from dataclasses import dataclass, field


@dataclass
class Phrase:
    """Represents a phrase-action mapping from a phrase file.

    Attributes:
        text: The spoken phrase that triggers the action.
        action: The action to perform when phrase is recognized.
        tags: Optional tags for special behavior (e.g., @transcribe, @cancel).
        source_file: Path to the phrase file where this was defined.
    """

    text: str
    action: str
    tags: list[str] = field(default_factory=list)
    source_file: str = ""


@dataclass
class ParsedCommand:
    """Represents a parsed command ready for execution.

    Attributes:
        action_type: The type of action (type, press, open, mouse).
        arguments: Arguments for the action (e.g., {"text": "hello"}).
        raw_phrase: The original transcribed text.
        from_fallback: True if matched via fallback pattern, False if exact phrase.
        phrase: The Phrase object if matched from phrase file.
    """

    action_type: str
    arguments: dict[str, str | int]
    raw_phrase: str
    from_fallback: bool = False
    phrase: Phrase | None = None

    def __repr__(self) -> str:
        """Return string representation of ParsedCommand."""
        source = "fallback" if self.from_fallback else "phrase"
        return f"ParsedCommand({self.action_type}, {self.arguments}, {source})"
