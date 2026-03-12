"""Phrase file loading for Yawrungay."""

import logging
import re
from pathlib import Path
from typing import Optional

from yawrungay.parsing.base import Phrase

logger = logging.getLogger(__name__)

DEFAULT_PHRASE_DIRS = [
    Path.home() / ".config" / "yawrungay" / "phrases",
    Path("/etc") / "yawrungay" / "phrases",
]

TAG_PATTERN = re.compile(r"^(@\w+)\s*")


class PhraseFileLoader:
    """Loads and parses phrase files.

    Phrase files contain lines in the format:
        [@TAG...] PHRASE: ACTION

    Lines starting with # are comments.
    Empty lines are ignored.
    Lines ending with backslash continue to the next line.
    """

    def __init__(self, phrase_dirs: list[Path] | None = None):
        """Initialize the phrase loader.

        Args:
            phrase_dirs: Directories to search for .phrases files.
                        Default: ~/.config/yawrungay/phrases and /etc/yawrungay/phrases
        """
        self._phrase_dirs = phrase_dirs or DEFAULT_PHRASE_DIRS
        self._phrases: dict[str, Phrase] = {}

    def load_all(self) -> dict[str, Phrase]:
        """Load all phrase files from configured directories.

        Returns:
            Dictionary mapping phrase text to Phrase objects.
        """
        self._phrases = {}

        for phrase_dir in self._phrase_dirs:
            if phrase_dir.exists() and phrase_dir.is_dir():
                self._load_directory(phrase_dir)

        logger.info(f"Loaded {len(self._phrases)} phrases")
        return self._phrases

    def load_file(self, file_path: Path) -> list[Phrase]:
        """Load phrases from a single file.

        Args:
            file_path: Path to the phrase file.

        Returns:
            List of Phrase objects from the file.
        """
        phrases = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = self._join_continuation_lines(content.split("\n"))

            for line in lines:
                phrase = self._parse_line(line, str(file_path))
                if phrase:
                    phrases.append(phrase)

            logger.debug(f"Loaded {len(phrases)} phrases from {file_path}")

        except OSError as e:
            logger.error(f"Failed to load phrase file {file_path}: {e}")

        return phrases

    def _load_directory(self, directory: Path) -> None:
        """Load all .phrases files from a directory.

        Args:
            directory: Directory to scan for phrase files.
        """
        for file_path in sorted(directory.glob("*.phrases")):
            phrases = self.load_file(file_path)
            for phrase in phrases:
                self._phrases[phrase.text.lower()] = phrase

    def _join_continuation_lines(self, lines: list[str]) -> list[str]:
        """Join lines that end with backslash.

        Args:
            lines: Original lines from file.

        Returns:
            Lines with continuations joined.
        """
        result = []
        current = ""

        for line in lines:
            if line.rstrip().endswith("\\"):
                current += line.rstrip()[:-1]
            else:
                current += line
                if current.strip():
                    result.append(current)
                current = ""

        if current.strip():
            result.append(current)

        return result

    def _parse_line(self, line: str, source_file: str) -> Optional[Phrase]:
        """Parse a single phrase line.

        Args:
            line: Line to parse.
            source_file: Path to source file (for error messages).

        Returns:
            Phrase object, or None if line is empty/comment.
        """
        line = line.strip()

        if not line or line.startswith("#"):
            return None

        tags = []
        match = TAG_PATTERN.match(line)
        while match:
            tags.append(match.group(1))
            line = line[match.end() :].strip()
            match = TAG_PATTERN.match(line)

        if ":" not in line:
            logger.warning(f"Invalid phrase line in {source_file}: missing ':' in '{line}'")
            return None

        parts = line.split(":", 1)
        if len(parts) != 2:
            logger.warning(f"Invalid phrase line in {source_file}: '{line}'")
            return None

        phrase_text = parts[0].strip()
        action = parts[1].strip()

        if not phrase_text or not action:
            logger.warning(f"Empty phrase or action in {source_file}: '{line}'")
            return None

        return Phrase(
            text=phrase_text,
            action=action,
            tags=tags,
            source_file=source_file,
        )

    @property
    def phrases(self) -> dict[str, Phrase]:
        """Get loaded phrases."""
        return self._phrases

    def get_phrase(self, text: str) -> Optional[Phrase]:
        """Get a phrase by text (case-insensitive).

        Args:
            text: The phrase text to look up.

        Returns:
            Phrase object if found, None otherwise.
        """
        return self._phrases.get(text.lower())
