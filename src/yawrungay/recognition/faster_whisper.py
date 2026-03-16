"""Speech recognition using faster-whisper (OpenAI Whisper optimized)."""

import logging
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

from yawrungay.audio import SilenceDetector, SilenceState
from yawrungay.recognition.base import BaseRecognizer, Utterance

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
        compute_type: Compute type for inference (int8, float16, float32, default).
    """

    def __init__(
        self,
        model_size: str = "small",
        cache_dir: str | None = None,
        compute_type: str = "int8",
    ) -> None:
        """Initialize the faster-whisper recognizer.

        Args:
            model_size: Size of the model to use. Default is 'small'.
                Options: 'tiny', 'base', 'small', 'medium', 'large'
            cache_dir: Directory to cache downloaded models.
                Default: ~/.cache/yawrungay/models
            compute_type: Compute type for inference. Default is 'int8'.
                Options: 'int8', 'int8_float16', 'float16', 'float32', 'default'
                Use 'int8' for best performance on CPU.

        Raises:
            ValueError: If model_size is not valid.
        """
        if model_size not in VALID_MODEL_SIZES:
            raise ValueError(f"Invalid model size '{model_size}'. Must be one of: {', '.join(VALID_MODEL_SIZES)}")

        self.model_size = model_size
        self.compute_type = compute_type
        self._model: WhisperModel | None = None

        # Set cache directory
        if cache_dir is None:
            cache_dir = str(Path.home() / ".cache" / "yawrungay" / "models")
        self.cache_dir = cache_dir

        logger.debug(
            f"Initialized FasterWhisperRecognizer with "
            f"model_size={model_size}, compute_type={compute_type}, cache_dir={cache_dir}"
        )

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
                compute_type=self.compute_type,
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

    def supports_streaming(self) -> bool:
        """Faster-whisper supports buffered streaming.

        Returns:
            True - via buffered approach with silence detection.
        """
        return True

    def transcribe_stream(
        self,
        audio_chunks: Iterator[bytes],
        silence_threshold_db: float = -35.0,
        min_silence_duration: float = 0.8,
        sample_rate: int = 16000,
    ) -> Iterator[Utterance]:
        """Transcribe audio stream using buffered approach.

        Faster-whisper doesn't have native streaming, so this implementation
        buffers audio chunks and transcribes when silence is detected.

        Args:
            audio_chunks: Iterator yielding audio chunks (16-bit PCM bytes).
            silence_threshold_db: dB threshold for silence detection.
            min_silence_duration: Seconds of silence to mark utterance end.
            sample_rate: Audio sample rate in Hz.

        Yields:
            Utterance objects containing transcribed text.

        Raises:
            RuntimeError: If model is not loaded.
        """
        if not self.is_ready():
            raise RuntimeError("Model not loaded. Call load_model() first.")

        silence_detector = SilenceDetector(
            threshold_db=silence_threshold_db,
            min_silence_duration=min_silence_duration,
            sample_rate=sample_rate,
        )

        buffer: list[bytes] = []

        logger.debug("Starting faster-whisper streaming transcription")

        for chunk in audio_chunks:
            if not chunk:
                continue

            buffer.append(chunk)
            silence_state = silence_detector.process_chunk(chunk)

            if silence_state == SilenceState.UTTERANCE_END and buffer:
                audio_data = b"".join(buffer)
                text = self.transcribe(audio_data)

                if text.strip():
                    logger.debug(f"Faster-whisper streaming utterance: {text}")
                    yield Utterance(text=text, is_final=True, confidence=None)

                buffer.clear()
                silence_detector.reset()

        if buffer:
            audio_data = b"".join(buffer)
            text = self.transcribe(audio_data)

            if text.strip():
                logger.debug(f"Faster-whisper streaming final utterance: {text}")
                yield Utterance(text=text, is_final=True, confidence=None)
