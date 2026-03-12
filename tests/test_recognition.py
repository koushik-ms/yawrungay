"""Tests for speech recognition module."""

import struct
from unittest.mock import MagicMock, patch

import pytest

from yawrungay.recognition import get_recognizer
from yawrungay.recognition.base import BaseRecognizer, Utterance
from yawrungay.recognition.faster_whisper import FasterWhisperRecognizer
from yawrungay.recognition.vosk import VoskRecognizer


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


class TestVoskRecognizer:
    """Test cases for VoskRecognizer implementation."""

    @patch("yawrungay.recognition.vosk.Model")
    def test_initialization(self, mock_vosk_model):
        """Test that Vosk recognizer initializes without loading model."""
        recognizer = VoskRecognizer(model_size="small")
        assert recognizer.model_size == "small"
        assert recognizer._model is None
        assert recognizer.sample_rate == 16000
        # Model should not be loaded on init
        mock_vosk_model.assert_not_called()

    def test_invalid_model_size(self):
        """Test that invalid model size raises ValueError."""
        with pytest.raises(ValueError, match="Invalid model size"):
            VoskRecognizer(model_size="invalid")

    @patch("yawrungay.recognition.vosk.Model")
    @patch("yawrungay.recognition.vosk.Path.exists")
    def test_load_model_existing(self, mock_exists, mock_vosk_model):
        """Test loading an existing Vosk model."""
        mock_exists.return_value = True
        mock_model_instance = MagicMock()
        mock_vosk_model.return_value = mock_model_instance

        recognizer = VoskRecognizer(model_size="small")
        recognizer.load_model()

        # Should have called Model with model path
        mock_vosk_model.assert_called_once()
        assert recognizer._model is not None

    @patch("yawrungay.recognition.vosk.Model")
    @patch("yawrungay.recognition.vosk.Path.exists")
    @patch("yawrungay.recognition.vosk.request.urlretrieve")
    @patch("yawrungay.recognition.vosk.zipfile.ZipFile")
    @patch("yawrungay.recognition.vosk.Path.unlink")
    @patch("yawrungay.recognition.vosk.shutil.move")
    def test_load_model_downloads_if_missing(
        self, mock_move, mock_unlink, mock_zipfile, mock_urlretrieve, mock_exists, mock_vosk_model
    ):
        """Test that model is downloaded if not present."""
        # Model dir doesn't exist initially, exists after download, and temp file doesn't exist
        mock_exists.side_effect = [False, False, True]
        mock_model_instance = MagicMock()
        mock_vosk_model.return_value = mock_model_instance

        # Mock zipfile context manager
        mock_zip_instance = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        recognizer = VoskRecognizer(model_size="small")
        recognizer.load_model()

        # Should have downloaded the model
        mock_urlretrieve.assert_called_once()
        # Should have extracted the zip
        mock_zip_instance.extractall.assert_called_once()
        # Should have loaded the model
        mock_vosk_model.assert_called_once()
        assert recognizer._model is not None

    @patch("yawrungay.recognition.vosk.Model")
    @patch("yawrungay.recognition.vosk.Path.exists")
    def test_is_ready_false_before_load(self, mock_exists, mock_vosk_model):
        """Test that is_ready returns False before model is loaded."""
        recognizer = VoskRecognizer(model_size="small")
        assert recognizer.is_ready() is False

    @patch("yawrungay.recognition.vosk.Model")
    @patch("yawrungay.recognition.vosk.Path.exists")
    def test_is_ready_true_after_load(self, mock_exists, mock_vosk_model):
        """Test that is_ready returns True after model is loaded."""
        mock_exists.return_value = True
        mock_model_instance = MagicMock()
        mock_vosk_model.return_value = mock_model_instance

        recognizer = VoskRecognizer(model_size="small")
        recognizer.load_model()

        assert recognizer.is_ready() is True

    @patch("yawrungay.recognition.vosk.Model")
    @patch("yawrungay.recognition.vosk.Path.exists")
    @patch("yawrungay.recognition.vosk.KaldiRecognizer")
    def test_transcribe(self, mock_kaldi, mock_exists, mock_vosk_model):
        """Test transcribing audio data."""
        mock_exists.return_value = True
        mock_model_instance = MagicMock()
        mock_vosk_model.return_value = mock_model_instance

        # Mock KaldiRecognizer
        mock_recognizer_instance = MagicMock()
        mock_recognizer_instance.FinalResult.return_value = '{"text": "hello world"}'
        mock_kaldi.return_value = mock_recognizer_instance

        recognizer = VoskRecognizer(model_size="small")
        recognizer.load_model()

        # Create dummy audio data
        audio_data = struct.pack("<" + "h" * 1600, *([0] * 1600))  # 0.1 second at 16kHz

        text = recognizer.transcribe(audio_data)

        assert text == "hello world"
        mock_recognizer_instance.AcceptWaveform.assert_called_once_with(audio_data)
        mock_recognizer_instance.FinalResult.assert_called_once()

    def test_transcribe_before_load_raises(self):
        """Test that transcribing before loading model raises error."""
        recognizer = VoskRecognizer(model_size="small")
        audio_data = b"dummy"

        with pytest.raises(RuntimeError, match="Model not loaded"):
            recognizer.transcribe(audio_data)

    @patch("yawrungay.recognition.vosk.Model")
    @patch("yawrungay.recognition.vosk.Path.exists")
    def test_load_model_idempotent(self, mock_exists, mock_vosk_model):
        """Test that calling load_model multiple times is safe."""
        mock_exists.return_value = True
        mock_model_instance = MagicMock()
        mock_vosk_model.return_value = mock_model_instance

        recognizer = VoskRecognizer(model_size="small")
        recognizer.load_model()
        recognizer.load_model()  # Second call

        # Model should only be loaded once
        assert mock_vosk_model.call_count == 1

    @patch("yawrungay.recognition.vosk.Model")
    @patch("yawrungay.recognition.vosk.Path.exists")
    def test_cleanup(self, mock_exists, mock_vosk_model):
        """Test that cleanup releases resources."""
        mock_exists.return_value = True
        mock_model_instance = MagicMock()
        mock_vosk_model.return_value = mock_model_instance

        recognizer = VoskRecognizer(model_size="small")
        recognizer.load_model()
        assert recognizer._model is not None

        recognizer.cleanup()
        assert recognizer._model is None

    @patch("yawrungay.recognition.vosk.Model")
    @patch("yawrungay.recognition.vosk.Path.exists")
    @patch("yawrungay.recognition.vosk.KaldiRecognizer")
    def test_transcribe_empty_result(self, mock_kaldi, mock_exists, mock_vosk_model):
        """Test transcribing with empty result."""
        mock_exists.return_value = True
        mock_model_instance = MagicMock()
        mock_vosk_model.return_value = mock_model_instance

        # Mock KaldiRecognizer with empty result
        mock_recognizer_instance = MagicMock()
        mock_recognizer_instance.FinalResult.return_value = '{"text": ""}'
        mock_kaldi.return_value = mock_recognizer_instance

        recognizer = VoskRecognizer(model_size="small")
        recognizer.load_model()

        audio_data = struct.pack("<" + "h" * 1600, *([0] * 1600))
        text = recognizer.transcribe(audio_data)

        assert text == ""

    @patch("yawrungay.recognition.vosk.Model")
    def test_get_recognizer_vosk(self, mock_vosk_model):
        """Test that vosk engine is returned from get_recognizer."""
        recognizer = get_recognizer(engine="vosk", model_size="small")
        assert isinstance(recognizer, VoskRecognizer)
        assert recognizer.model_size == "small"

    @patch("yawrungay.recognition.vosk.Model")
    def test_get_recognizer_vosk_with_model_path(self, mock_vosk_model):
        """Test that model_path is passed to VoskRecognizer."""
        custom_path = "/custom/path"
        recognizer = get_recognizer(engine="vosk", model_size="large", model_path=custom_path)
        assert isinstance(recognizer, VoskRecognizer)
        assert recognizer.model_size == "large"
        assert recognizer.model_path == custom_path


class TestUtterance:
    """Test cases for Utterance class."""

    def test_creation(self):
        """Test creating an utterance."""
        utterance = Utterance(text="Hello world")
        assert utterance.text == "Hello world"
        assert utterance.is_final is True
        assert utterance.confidence is None

    def test_partial_utterance(self):
        """Test creating a partial utterance."""
        utterance = Utterance(text="Hello", is_final=False)
        assert utterance.text == "Hello"
        assert utterance.is_final is False

    def test_with_confidence(self):
        """Test creating utterance with confidence."""
        utterance = Utterance(text="Hello", confidence=0.95)
        assert utterance.confidence == 0.95

    def test_repr(self):
        """Test string representation."""
        utterance = Utterance(text="Hello")
        assert "Hello" in repr(utterance)
        assert "final" in repr(utterance)

        partial = Utterance(text="Hello", is_final=False)
        assert "partial" in repr(partial)


class TestStreamingSupport:
    """Test cases for streaming transcription support."""

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_faster_whisper_supports_streaming(self, mock_whisper_model):
        """Test that faster-whisper reports streaming support."""
        recognizer = FasterWhisperRecognizer(model_size="small")
        assert recognizer.supports_streaming() is True

    @patch("yawrungay.recognition.vosk.Model")
    def test_vosk_supports_streaming(self, mock_vosk_model):
        """Test that Vosk reports streaming support."""
        recognizer = VoskRecognizer(model_size="small")
        assert recognizer.supports_streaming() is True

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_faster_whisper_transcribe_stream_requires_model(self, mock_whisper_model):
        """Test that streaming requires loaded model."""
        recognizer = FasterWhisperRecognizer(model_size="small")

        def audio_gen():
            yield b"\x00" * 1024

        with pytest.raises(RuntimeError, match="Model not loaded"):
            list(recognizer.transcribe_stream(audio_gen()))

    @patch("yawrungay.recognition.vosk.Model")
    def test_vosk_transcribe_stream_requires_model(self, mock_vosk_model):
        """Test that Vosk streaming requires loaded model."""
        recognizer = VoskRecognizer(model_size="small")

        def audio_gen():
            yield b"\x00" * 1024

        with pytest.raises(RuntimeError, match="Model not loaded"):
            list(recognizer.transcribe_stream(audio_gen()))

    @patch("yawrungay.recognition.faster_whisper.WhisperModel")
    def test_faster_whisper_transcribe_stream(self, mock_whisper_model):
        """Test faster-whisper streaming transcription."""
        mock_model_instance = MagicMock()
        mock_whisper_model.return_value = mock_model_instance

        mock_segments = [MagicMock(text="Hello world")]
        mock_model_instance.transcribe.return_value = (mock_segments, None)

        recognizer = FasterWhisperRecognizer(model_size="small")
        recognizer.load_model()

        silence_chunk = struct.pack("<" + "h" * 1024, *([0] * 1024))
        speech_chunk = struct.pack("<" + "h" * 1024, *([10000] * 1024))

        def audio_gen():
            yield speech_chunk
            yield speech_chunk
            for _ in range(10):
                yield silence_chunk

        utterances = list(
            recognizer.transcribe_stream(
                audio_gen(),
                min_silence_duration=0.5,
                sample_rate=16000,
            )
        )

        assert len(utterances) >= 1
        assert utterances[0].text == "Hello world"
        assert utterances[0].is_final is True

    @patch("yawrungay.recognition.vosk.Model")
    @patch("yawrungay.recognition.vosk.KaldiRecognizer")
    def test_vosk_transcribe_stream(self, mock_kaldi, mock_vosk_model):
        """Test Vosk streaming transcription."""
        mock_exists = patch("yawrungay.recognition.vosk.Path.exists", return_value=True)
        mock_exists.start()

        mock_model_instance = MagicMock()
        mock_vosk_model.return_value = mock_model_instance

        mock_recognizer_instance = MagicMock()
        mock_recognizer_instance.FinalResult.return_value = '{"text": "hello world"}'
        mock_recognizer_instance.PartialResult.return_value = '{"partial": ""}'
        mock_kaldi.return_value = mock_recognizer_instance

        recognizer = VoskRecognizer(model_size="small")
        recognizer.load_model()

        silence_chunk = struct.pack("<" + "h" * 1600, *([0] * 1600))
        speech_chunk = struct.pack("<" + "h" * 1600, *([10000] * 1600))

        def audio_gen():
            yield speech_chunk
            yield speech_chunk
            for _ in range(10):
                yield silence_chunk

        utterances = list(
            recognizer.transcribe_stream(
                audio_gen(),
                min_silence_duration=0.5,
                sample_rate=16000,
            )
        )

        assert len(utterances) >= 1
        assert utterances[0].text == "hello world"
        assert utterances[0].is_final is True

        mock_exists.stop()
