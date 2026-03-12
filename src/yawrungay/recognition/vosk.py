"""Speech recognition using Vosk offline ASR."""

import json
import logging
import os
import shutil
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Optional
from urllib import request

from vosk import KaldiRecognizer, Model

from yawrungay.audio import SilenceDetector, SilenceState
from yawrungay.recognition.base import BaseRecognizer, Utterance

logger = logging.getLogger(__name__)

# Model information for English
VOSK_MODELS = {
    "small": {
        "name": "vosk-model-small-en-us-0.15",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
        "size_mb": 40,
    },
    "large": {
        "name": "vosk-model-en-us-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip",
        "size_mb": 1800,
    },
}

VALID_MODEL_SIZES = list(VOSK_MODELS.keys())


class VoskRecognizer(BaseRecognizer):
    """Speech recognition using Vosk offline ASR.

    Vosk is an offline speech recognition toolkit that supports multiple languages
    and provides fast, accurate transcription without requiring internet connectivity.

    Attributes:
        model_size: Size of the model ('small' or 'large').
        model_path: Path to the model directory.
        sample_rate: Audio sample rate in Hz.
    """

    def __init__(
        self,
        model_size: str = "small",
        model_path: str | None = None,
        sample_rate: int = 16000,
    ) -> None:
        """Initialize the Vosk recognizer.

        Args:
            model_size: Size of the model to use. Default is 'small'.
                Options: 'small' (~40MB), 'large' (~1.8GB)
            model_path: Path to model directory. If None, uses cache directory.
            sample_rate: Audio sample rate in Hz (default 16000).

        Raises:
            ValueError: If model_size is not valid.
        """
        if model_size not in VALID_MODEL_SIZES:
            raise ValueError(f"Invalid model size '{model_size}'. Must be one of: {', '.join(VALID_MODEL_SIZES)}")

        self.model_size = model_size
        self.sample_rate = sample_rate
        self._model: Optional[Model] = None
        self._recognizer: Optional[KaldiRecognizer] = None

        # Set model path
        if model_path is None:
            model_path = str(Path.home() / ".cache" / "yawrungay" / "vosk-models")
        self.model_path = model_path

        # Full path to the specific model
        self._model_dir = Path(self.model_path) / VOSK_MODELS[model_size]["name"]

        logger.debug(f"Initialized VoskRecognizer with model_size={model_size}, model_path={model_path}")

    def _download_model(self) -> None:
        """Download and extract the Vosk model.

        Raises:
            RuntimeError: If download or extraction fails.
        """
        model_info = VOSK_MODELS[self.model_size]
        model_url = model_info["url"]
        model_name = model_info["name"]
        size_mb = model_info["size_mb"]

        logger.info(f"Downloading Vosk model '{model_name}' (~{size_mb}MB)...")
        logger.info(f"This may take a few minutes depending on your connection speed.")

        # Create cache directory
        cache_dir = Path(self.model_path)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Download to temporary file
        zip_path = cache_dir / f"{model_name}.zip"
        temp_zip_path = cache_dir / f"{model_name}.zip.tmp"

        try:
            # Check if already downloading
            if temp_zip_path.exists():
                logger.warning("Found incomplete download, removing and restarting...")
                temp_zip_path.unlink()

            # Download with progress
            logger.info(f"Downloading from: {model_url}")

            def reporthook(block_num: int, block_size: int, total_size: int) -> None:
                """Progress callback for download."""
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    if block_num % 50 == 0 or percent >= 100:  # Update every ~50 blocks or at completion
                        downloaded_mb = (block_num * block_size) / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        logger.info(f"Download progress: {percent}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)")

            request.urlretrieve(model_url, temp_zip_path, reporthook=reporthook)

            # Move to final location
            shutil.move(str(temp_zip_path), str(zip_path))
            logger.info("Download complete!")

            # Extract the model
            logger.info(f"Extracting model to {cache_dir}...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(cache_dir)

            # Remove the zip file
            zip_path.unlink()
            logger.info(f"Model extracted successfully to: {self._model_dir}")

        except Exception as e:
            # Clean up on failure
            if temp_zip_path.exists():
                temp_zip_path.unlink()
            if zip_path.exists():
                zip_path.unlink()
            raise RuntimeError(f"Failed to download Vosk model: {e}") from e

    def load_model(self) -> None:
        """Load the Vosk model.

        Downloads the model if not already cached. This method is idempotent
        and can be called multiple times safely.

        Raises:
            RuntimeError: If model loading fails.
        """
        if self._model is not None:
            logger.debug("Model already loaded, skipping")
            return

        try:
            # Check if model exists
            if not self._model_dir.exists():
                logger.info(f"Model not found at {self._model_dir}, downloading...")
                self._download_model()

            # Verify model directory has required files
            if not self._model_dir.exists():
                raise RuntimeError(f"Model directory not found after download: {self._model_dir}")

            logger.info(f"Loading Vosk model from: {self._model_dir}")

            # Suppress Vosk's internal logging to stderr
            os.environ["VOSK_LOG_LEVEL"] = "-1"

            # Load the model
            self._model = Model(str(self._model_dir))

            logger.info(f"Successfully loaded Vosk model: {self.model_size}")

        except Exception as e:
            logger.error(f"Failed to load Vosk model: {e}")
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
            logger.debug(f"Transcribing audio: {len(audio_data)} bytes")

            # Create a new recognizer for this transcription
            # Note: We create a new recognizer each time to avoid state issues
            recognizer = KaldiRecognizer(self._model, self.sample_rate)

            # Feed all audio data at once
            recognizer.AcceptWaveform(audio_data)

            # Get the final result
            result_json = recognizer.FinalResult()
            result = json.loads(result_json)

            # Extract text from result
            text = result.get("text", "")

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
            logger.debug("Cleaning up Vosk recognizer")
            self._model = None
            self._recognizer = None

    def supports_streaming(self) -> bool:
        """Vosk supports native streaming transcription.

        Returns:
            True - Vosk has built-in streaming support.
        """
        return True

    def transcribe_stream(
        self,
        audio_chunks: Iterator[bytes],
        silence_threshold_db: float = -35.0,
        min_silence_duration: float = 0.8,
        sample_rate: int = 16000,
    ) -> Iterator[Utterance]:
        """Transcribe audio stream using Vosk's native streaming.

        Uses Vosk's AcceptWaveform/PartialResult/FinalResult API for
        real-time transcription with utterance boundary detection.

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

        recognizer = KaldiRecognizer(self._model, sample_rate)
        buffer: list[bytes] = []
        current_text = ""
        last_partial = ""

        logger.debug("Starting Vosk streaming transcription")

        for chunk in audio_chunks:
            if not chunk:
                continue

            buffer.append(chunk)
            silence_state = silence_detector.process_chunk(chunk)

            recognizer.AcceptWaveform(chunk)

            if silence_state == SilenceState.SPEECH:
                partial_json = recognizer.PartialResult()
                partial_result = json.loads(partial_json)
                partial_text = partial_result.get("partial", "")

                if partial_text and partial_text != last_partial:
                    last_partial = partial_text

            elif silence_state == SilenceState.UTTERANCE_END:
                final_json = recognizer.FinalResult()
                final_result = json.loads(final_json)
                text = final_result.get("text", "").strip()

                if text:
                    logger.debug(f"Vosk streaming utterance: {text}")
                    yield Utterance(text=text, is_final=True, confidence=None)

                buffer.clear()
                current_text = ""
                last_partial = ""
                silence_detector.reset()

        if buffer:
            final_json = recognizer.FinalResult()
            final_result = json.loads(final_json)
            text = final_result.get("text", "").strip()

            if text:
                logger.debug(f"Vosk streaming final utterance: {text}")
                yield Utterance(text=text, is_final=True, confidence=None)
