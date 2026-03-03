"""Base class for speech recognition engines."""

from abc import ABC, abstractmethod


class BaseRecognizer(ABC):
    """Abstract base class for speech recognition engines.

    All speech recognition engine implementations must inherit from this class
    and implement the abstract methods.
    """

    @abstractmethod
    def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio data to text.

        Args:
            audio_data: Audio data as bytes in 16-bit PCM format.

        Returns:
            Transcribed text as a string.

        Raises:
            RuntimeError: If model is not loaded or transcription fails.
        """
        pass

    @abstractmethod
    def load_model(self) -> None:
        """Load the speech recognition model.

        This method may be called multiple times. Implementations should handle
        already-loaded models gracefully.

        Raises:
            RuntimeError: If model loading fails.
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if the model is loaded and ready for transcription.

        Returns:
            True if the model is ready, False otherwise.
        """
        pass

    def cleanup(self) -> None:  # noqa: B027
        """Clean up resources used by the recognizer.

        This method is called when the recognizer is no longer needed.
        Default implementation does nothing; subclasses should override if needed.
        """
