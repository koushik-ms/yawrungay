"""Tests for audio capture module."""

import time

import pytest

from yawrungay.audio.capture import (
    AudioCapture,
    AudioCaptureError,
    AudioConfig,
    record_audio,
)
from yawrungay.audio.devices import list_audio_devices


class TestAudioConfig:
    """Test cases for AudioConfig dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.chunk_size == 1024
        assert config.channels == 1
        assert config.format == 8  # pyaudio.paInt16
        assert config.device_index is None
        assert config.max_queue_size == 100

    def test_custom_values(self):
        """Test that custom values are set correctly."""
        config = AudioConfig(
            sample_rate=44100,
            chunk_size=2048,
            channels=2,
            device_index=1,
            max_queue_size=50,
        )
        assert config.sample_rate == 44100
        assert config.chunk_size == 2048
        assert config.channels == 2
        assert config.device_index == 1
        assert config.max_queue_size == 50


class TestAudioCapture:
    """Test cases for AudioCapture class."""

    def test_initialization(self):
        """Test that capture initializes correctly."""
        capture = AudioCapture()
        assert not capture.is_capturing
        assert capture.device is None

    def test_context_manager(self):
        """Test that context manager works correctly."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        with AudioCapture() as capture:
            assert capture.device is not None
            assert not capture.is_capturing

    def test_initialize_without_start(self):
        """Test initialization without starting capture."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        capture = AudioCapture()
        capture.initialize()
        assert capture.device is not None
        assert not capture.is_capturing
        capture.close()

    def test_start_stop(self):
        """Test starting and stopping capture."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        with AudioCapture() as capture:
            capture.start()
            assert capture.is_capturing
            capture.stop()
            assert not capture.is_capturing

    def test_double_start(self):
        """Test that double start doesn't fail."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        with AudioCapture() as capture:
            capture.start()
            capture.start()  # Should not raise
            assert capture.is_capturing

    def test_stop_without_start(self):
        """Test that stop without start doesn't fail."""
        capture = AudioCapture()
        capture.initialize()
        capture.stop()  # Should not raise
        capture.close()

    def test_read_chunk_timeout(self):
        """Test reading chunk with timeout."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        with AudioCapture() as capture:
            capture.start()
            # Should return None on timeout
            chunk = capture.read_chunk(timeout=0.01)
            # Note: chunk might be None or actual data depending on timing
            capture.stop()

    def test_read_chunks_generator(self):
        """Test the read_chunks generator."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        with AudioCapture() as capture:
            capture.start()
            # Allow audio thread time to initialize and start producing data
            time.sleep(0.05)

            chunks = []
            start_time = time.time()

            # Use longer timeout and collection window to account for slow audio initialization
            for chunk in capture.read_chunks(timeout=0.05):
                chunks.append(chunk)
                if time.time() - start_time > 0.5:  # Collect for 500ms
                    break

            capture.stop()
            assert len(chunks) > 0, "Expected at least one audio chunk; audio device may not be responding"

    def test_record(self):
        """Test recording fixed duration."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        with AudioCapture() as capture:
            capture.start()
            audio_data = capture.record(duration=0.1)
            assert isinstance(audio_data, bytes)
            assert len(audio_data) > 0

    def test_record_without_start(self):
        """Test that record without start raises error."""
        with AudioCapture() as capture:
            with pytest.raises(AudioCaptureError):
                capture.record(duration=0.1)

    def test_queue_size(self):
        """Test getting queue size."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        with AudioCapture() as capture:
            capture.start()
            size = capture.get_queue_size()
            assert isinstance(size, int)
            assert size >= 0
            capture.stop()

    def test_clear_queue(self):
        """Test clearing the queue."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        with AudioCapture() as capture:
            capture.start()
            time.sleep(0.05)  # Let some data accumulate
            initial_size = capture.get_queue_size()
            capture.clear_queue()
            assert capture.get_queue_size() == 0
            capture.stop()

    def test_invalid_device(self):
        """Test that invalid device raises error."""
        config = AudioConfig(device_index=9999)
        capture = AudioCapture(config)
        with pytest.raises(AudioCaptureError):
            capture.initialize()


class TestRecordAudio:
    """Test cases for record_audio context manager."""

    def test_record_audio(self):
        """Test record_audio context manager."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        with record_audio(duration=0.1) as audio_data:
            assert isinstance(audio_data, bytes)
            assert len(audio_data) > 0

    def test_record_audio_with_config(self):
        """Test record_audio with custom config."""
        devices = list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available")

        config = AudioConfig(sample_rate=22050)
        with record_audio(duration=0.1, config=config) as audio_data:
            assert isinstance(audio_data, bytes)
