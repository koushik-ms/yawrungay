"""Base class for speech recognition engines."""

from abc import ABC, abstractmethod
from collections.abc import Iterator


class Utterance:
    """Represents a transcribed utterance from continuous listening.

    Attributes:
        text: The transcribed text.
        is_final: Whether this is a final result (vs partial/interim).
        confidence: Optional confidence score (0.0 to 1.0).
    """

    def __init__(
        self,
        text: str,
        is_final: bool = True,
        confidence: float | None = None,
    ) -> None:
        """Initialize Utterance.

        Args:
            text: Transcribed text.
            is_final: Whether this is a final transcription.
            confidence: Confidence score if available.
        """
        self.text = text
        self.is_final = is_final
        self.confidence = confidence

    def __repr__(self) -> str:
        """Return string representation of Utterance."""
        status = "final" if self.is_final else "partial"
        return f"Utterance(text={self.text!r}, {status})"


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

    def supports_streaming(self) -> bool:
        """Check if this recognizer supports streaming transcription.

        Returns:
            True if transcribe_stream is implemented for real-time use.
        """
        return False

    def transcribe_stream(
        self,
        audio_chunks: Iterator[bytes],
        silence_threshold_db: float = -35.0,
        min_silence_duration: float = 0.8,
        sample_rate: int = 16000,
    ) -> Iterator[Utterance]:
        """Transcribe audio stream, yielding utterances as detected.

        This is an optional method for real-time continuous transcription.
        Implementations should detect utterance boundaries based on silence
        and yield Utterance objects as speech is recognized.

        Args:
            audio_chunks: Iterator yielding audio chunks (16-bit PCM bytes).
            silence_threshold_db: dB threshold for silence detection.
            min_silence_duration: Seconds of silence to mark utterance end.
            sample_rate: Audio sample rate in Hz.

        Yields:
            Utterance objects containing transcribed text.

        Raises:
            NotImplementedError: If streaming is not supported by this engine.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support streaming transcription. "
            "Use transcribe() for batch processing."
        )

    def cleanup(self) -> None:  # noqa: B027
        """Clean up resources used by the recognizer.

        This method is called when the recognizer is no longer needed.
        Default implementation does nothing; subclasses should override if needed.
        """
