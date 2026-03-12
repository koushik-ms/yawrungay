"""Command parser for Yawrungay."""

import logging
import re
from typing import Optional

from yawrungay.parsing.base import ParsedCommand, Phrase
from yawrungay.parsing.patterns import BUILTIN_PATTERNS
from yawrungay.parsing.phrases import PhraseFileLoader

logger = logging.getLogger(__name__)


class CommandParser:
    """Parses transcribed text into commands.

    Priority:
    1. Exact phrase match from phrase files
    2. Built-in pattern match with fallback
    3. No match -> None
    """

    def __init__(self, phrases: dict[str, Phrase] | None = None, phrase_loader: PhraseFileLoader | None = None):
        """Initialize the parser.

        Args:
            phrases: Pre-loaded phrases dictionary.
            phrase_loader: Phrase loader to use if phrases not provided.
        """
        if phrases is not None:
            self._phrases = phrases
        elif phrase_loader is not None:
            self._phrases = phrase_loader.load_all()
        else:
            self._phrases = {}

    def parse(self, text: str) -> Optional[ParsedCommand]:
        """Parse transcribed text into a command.

        Args:
            text: Transcribed text to parse.

        Returns:
            ParsedCommand if matched, None otherwise.
        """
        text = text.strip()
        text_lower = text.lower()

        phrase_match = self._phrases.get(text_lower)
        if phrase_match:
            logger.debug(f"Matched phrase: {phrase_match.text} -> {phrase_match.action}")
            return self._parse_action(phrase_match.action, raw_phrase=text, phrase=phrase_match)

        for pattern in BUILTIN_PATTERNS:
            match = pattern.pattern.match(text_lower)
            if match:
                if not pattern.has_fallback:
                    logger.debug(f"Pattern '{pattern.action_type}' requires phrase definition")
                    return None

                arguments = pattern.extract_args(match)
                logger.debug(f"Matched pattern: {pattern.action_type} -> {arguments}")

                return ParsedCommand(
                    action_type=pattern.action_type,
                    arguments=arguments,
                    raw_phrase=text,
                    from_fallback=True,
                )

        logger.debug(f"No match for: {text}")
        return None

    def _parse_action(self, action: str, raw_phrase: str, phrase: Phrase) -> Optional[ParsedCommand]:
        """Parse an action string into a ParsedCommand.

        Action strings can be:
        - "type <text>" -> type action
        - "press <keys>" -> press action
        - "open <app>" -> open action
        - "run <app>" -> run action
        - "mouse <action>" -> mouse action

        Args:
            action: The action string to parse.
            raw_phrase: The original transcribed text.
            phrase: The Phrase object that matched.

        Returns:
            ParsedCommand if valid action, None otherwise.
        """
        for pattern in BUILTIN_PATTERNS:
            match = pattern.pattern.match(action.lower())
            if match:
                arguments = pattern.extract_args(match)
                return ParsedCommand(
                    action_type=pattern.action_type,
                    arguments=arguments,
                    raw_phrase=raw_phrase,
                    from_fallback=False,
                    phrase=phrase,
                )

        logger.warning(f"Unknown action format: {action}")
        return None

    def add_phrase(self, phrase: Phrase) -> None:
        """Add a phrase to the parser.

        Args:
            phrase: Phrase to add.
        """
        self._phrases[phrase.text.lower()] = phrase

    def remove_phrase(self, text: str) -> bool:
        """Remove a phrase from the parser.

        Args:
            text: Phrase text to remove (case-insensitive).

        Returns:
            True if phrase was removed, False if not found.
        """
        text_lower = text.lower()
        if text_lower in self._phrases:
            del self._phrases[text_lower]
            return True
        return False

    @property
    def phrases(self) -> dict[str, Phrase]:
        """Get all loaded phrases."""
        return self._phrases

    def reload_phrases(self, phrase_loader: PhraseFileLoader) -> int:
        """Reload phrases from the loader.

        Args:
            phrase_loader: Loader to use for reloading.

        Returns:
            Number of phrases loaded.
        """
        self._phrases = phrase_loader.load_all()
        return len(self._phrases)
