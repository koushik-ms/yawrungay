"""Speech recognition using faster-whisper (OpenAI Whisper optimized)."""

import logging
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

from yawrungay.recognition.base import BaseRecognizer

logger = logging.getLogger(__name__)

VALID_MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]


class FasterWhisperRecognizer(BaseRecognizer):
    """Speech recognition using faster-whisper library.

    faster-whisper is an optimized implementation of OpenAI's Whisper model
    that provides faster inference and lower memory usage compared to the
    official implementation.

    Attributes:
        model_size: Size of the model (tiny, base, small, medium, large).
        cache_dir: Directory to cache downloaded models.
    """

    def __init__(
        self,
        model_size: str = "small",
        cache_dir: str | None = None,
    ) -> None:
        """Initialize the faster-whisper recognizer.

        Args:
            model_size: Size of the model to use. Default is 'small'.
                Options: 'tiny', 'base', 'small', 'medium', 'large'
            cache_dir: Directory to cache downloaded models.
                Default: ~/.cache/yawrungay/models

        Raises:
            ValueError: If model_size is not valid.
        """
        if model_size not in VALID_MODEL_SIZES:
            raise ValueError(f"Invalid model size '{model_size}'. Must be one of: {', '.join(VALID_MODEL_SIZES)}")

        self.model_size = model_size
        self._model: WhisperModel | None = None

        # Set cache directory
        if cache_dir is None:
            cache_dir = str(Path.home() / ".cache" / "yawrungay" / "models")
        self.cache_dir = cache_dir

        logger.debug(f"Initialized FasterWhisperRecognizer with model_size={model_size}, cache_dir={cache_dir}")

    def load_model(self) -> None:
        """Load the faster-whisper model.

        Downloads the model if not already cached. This method is idempotent
        and can be called multiple times safely.

        Raises:
            RuntimeError: If model loading fails.
        """
        if self._model is not None:
            logger.debug("Model already loaded, skipping")
            return

        try:
            logger.info(f"Loading faster-whisper model: {self.model_size}")

            # Create cache directory if it doesn't exist
            cache_path = Path(self.cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)

            # Load the model with caching
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="default",
                download_root=self.cache_dir,
            )

            logger.info(f"Successfully loaded faster-whisper model: {self.model_size}")
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}")
            self._model = None
            raise RuntimeError(f"Failed to load speech recognition model: {e}") from e

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready.

        Returns:
            True if model is loaded, False otherwise.
        """
        return self._model is not None

    def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio data to text.

        Args:
            audio_data: Audio data as bytes in 16-bit PCM format at 16kHz.

        Returns:
            Transcribed text as a string.

        Raises:
            RuntimeError: If model is not loaded or transcription fails.
        """
        if not self.is_ready():
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)

            # Normalize audio to [-1, 1] range
            audio_array = audio_array / 32768.0

            logger.debug(f"Transcribing audio: {len(audio_data)} bytes")

            # Transcribe the audio
            segments, info = self._model.transcribe(
                audio_array,
                language="en",
                beam_size=5,
            )

            # Combine segments into a single string
            text = "".join(segment.text for segment in segments)

            logger.debug(f"Transcription complete: {text[:100]}...")
            return text.strip()

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Audio transcription failed: {e}") from e

    def cleanup(self) -> None:
        """Clean up resources used by the recognizer.

        Releases the loaded model from memory.
        """
        if self._model is not None:
            logger.debug("Cleaning up faster-whisper recognizer")
            self._model = None
