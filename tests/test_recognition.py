"""Tests for speech recognition module."""

import struct
from unittest.mock import MagicMock, patch

import pytest

from yawrungay.recognition import get_recognizer
from yawrungay.recognition.base import BaseRecognizer
from yawrungay.recognition.faster_whisper import FasterWhisperRecognizer


class TestBaseRecognizer:
    """Test cases for BaseRecognizer abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that BaseRecognizer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseRecognizer()

    def test_subclass_must_implement_transcribe(self):
        """Test that subclasses must implement transcribe method."""

        class IncompleteRecognizer(BaseRecognizer):
            def load_model(self) -> None:
                pass

            def is_ready(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteRecognizer()

    def test_subclass_must_implement_load_model(self):
        """Test that subclasses must implement load_model method."""

        class IncompleteRecognizer(BaseRecognizer):
            def transcribe(self, audio_data: bytes) -> str:
                return ""

            def is_ready(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteRecognizer()

    def test_subclass_must_implement_is_ready(self):
        """Test that subclasses must implement is_ready method."""

        class IncompleteRecognizer(BaseRecognizer):
            def transcribe(self, audio_data: bytes) -> str:
                return ""

            def load_model(self) -> None:
                pass

        with pytest.raises(TypeError):
            IncompleteRecognizer()


class TestFasterWhisperRecognizer:
    """Test cases for FasterWhisperRecognizer implementation."""

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_initialization(self, mock_whisper_model):
        """Test that recognizer initializes without loading model."""
        recognizer = FasterWhisperRecognizer(model_size="small")
        assert recognizer.model_size == "small"
        assert recognizer._model is None
        # Model should not be loaded on init
        mock_whisper_model.assert_not_called()

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_load_model(self, mock_whisper_model):
        """Test that load_model initializes the whisper model."""
        mock_model_instance = MagicMock()
        mock_whisper_model.return_value = mock_model_instance

        recognizer = FasterWhisperRecognizer(model_size="small")
        recognizer.load_model()

        # Should have called WhisperModel with correct parameters
        mock_whisper_model.assert_called_once()
        call_args = mock_whisper_model.call_args
        assert "small" in call_args[0] or call_args[1].get("size") == "small"
        assert recognizer._model is not None

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_is_ready_false_before_load(self, mock_whisper_model):
        """Test that is_ready returns False before model is loaded."""
        recognizer = FasterWhisperRecognizer(model_size="small")
        assert recognizer.is_ready() is False

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_is_ready_true_after_load(self, mock_whisper_model):
        """Test that is_ready returns True after model is loaded."""
        mock_model_instance = MagicMock()
        mock_whisper_model.return_value = mock_model_instance

        recognizer = FasterWhisperRecognizer(model_size="small")
        recognizer.load_model()
        assert recognizer.is_ready() is True

    def test_valid_model_sizes(self):
        """Test that valid model sizes are accepted."""
        valid_sizes = ["tiny", "base", "small", "medium", "large"]
        for size in valid_sizes:
            recognizer = FasterWhisperRecognizer(model_size=size)
            assert recognizer.model_size == size

    def test_invalid_model_size_raises_error(self):
        """Test that invalid model size raises ValueError."""
        with pytest.raises(ValueError):
            FasterWhisperRecognizer(model_size="invalid")

    def test_cache_dir_default(self):
        """Test that cache directory defaults to ~/.cache/yawrungay/models."""
        with patch.dict("os.environ", {}, clear=False):
            recognizer = FasterWhisperRecognizer(model_size="small")
            assert ".cache/yawrungay/models" in str(recognizer.cache_dir)

    def test_cache_dir_custom(self):
        """Test that custom cache directory is used."""
        custom_cache = "/custom/cache"
        recognizer = FasterWhisperRecognizer(model_size="small", cache_dir=custom_cache)
        assert recognizer.cache_dir == custom_cache

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_transcribe_requires_loaded_model(self, mock_whisper_model):
        """Test that transcribe raises error if model not loaded."""
        recognizer = FasterWhisperRecognizer(model_size="small")
        audio_data = b"\x00" * 1024  # Dummy audio data

        with pytest.raises(RuntimeError, match="Model not loaded"):
            recognizer.transcribe(audio_data)

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_transcribe_success(self, mock_whisper_model):
        """Test successful transcription."""
        # Mock the model and its transcribe method
        mock_model_instance = MagicMock()
        mock_whisper_model.return_value = mock_model_instance

        # Mock transcribe return value
        mock_segments = [
            MagicMock(text="Hello world"),
            MagicMock(text=" This is a test"),
        ]
        mock_model_instance.transcribe.return_value = (mock_segments, None)

        recognizer = FasterWhisperRecognizer(model_size="small")
        recognizer.load_model()

        # Generate simple audio data (mono, 16-bit, 16kHz)
        sample_rate = 16000
        duration = 1  # 1 second
        num_samples = sample_rate * duration
        audio_data = struct.pack(f"<{num_samples}h", *[0] * num_samples)  # Silent audio

        result = recognizer.transcribe(audio_data)
        assert result == "Hello world This is a test"

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_transcribe_empty_result(self, mock_whisper_model):
        """Test transcription with empty result."""
        mock_model_instance = MagicMock()
        mock_whisper_model.return_value = mock_model_instance
        mock_model_instance.transcribe.return_value = ([], None)

        recognizer = FasterWhisperRecognizer(model_size="small")
        recognizer.load_model()

        audio_data = b"\x00" * 1024
        result = recognizer.transcribe(audio_data)
        assert result == ""

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_cleanup(self, mock_whisper_model):
        """Test cleanup releases resources."""
        mock_model_instance = MagicMock()
        mock_whisper_model.return_value = mock_model_instance

        recognizer = FasterWhisperRecognizer(model_size="small")
        recognizer.load_model()
        assert recognizer._model is not None

        recognizer.cleanup()
        assert recognizer._model is None


class TestRecognizerFactory:
    """Test cases for recognizer factory function."""

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_get_recognizer_default(self, mock_whisper_model):
        """Test that default recognizer is faster-whisper."""
        recognizer = get_recognizer()
        assert isinstance(recognizer, FasterWhisperRecognizer)

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_get_recognizer_faster_whisper(self, mock_whisper_model):
        """Test that faster-whisper engine is returned."""
        recognizer = get_recognizer(engine="faster-whisper")
        assert isinstance(recognizer, FasterWhisperRecognizer)

    def test_get_recognizer_invalid_engine(self):
        """Test that invalid engine raises ValueError."""
        with pytest.raises(ValueError, match="Unknown recognition engine"):
            get_recognizer(engine="invalid-engine")

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_get_recognizer_with_custom_model_size(self, mock_whisper_model):
        """Test that custom model size is passed to recognizer."""
        recognizer = get_recognizer(engine="faster-whisper", model_size="base")
        assert recognizer.model_size == "base"
