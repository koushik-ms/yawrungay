"""Tests for audio processing module."""

import numpy as np
import pytest

from yawrungay.audio.processing import (
    apply_noise_gate,
    bytes_to_numpy,
    calculate_db,
    calculate_rms,
    convert_format,
    is_silence,
    normalize_audio,
    numpy_to_bytes,
    preprocess_for_stt,
    resample_audio,
    trim_silence,
)


class TestBytesToNumpy:
    """Test cases for bytes_to_numpy function."""

    def test_mono_conversion(self):
        """Test converting mono audio bytes to numpy."""
        # Create 1 second of 16-bit mono audio at 16kHz
        samples = np.zeros(16000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        result = bytes_to_numpy(audio_bytes, dtype=np.int16, channels=1)
        assert result.shape == (16000,)
        assert result.dtype == np.int16

    def test_stereo_conversion(self):
        """Test converting stereo audio bytes to numpy."""
        # Create 1 second of 16-bit stereo audio at 16kHz
        samples = np.zeros(16000 * 2, dtype=np.int16)
        audio_bytes = samples.tobytes()

        result = bytes_to_numpy(audio_bytes, dtype=np.int16, channels=2)
        assert result.shape == (16000, 2)
        assert result.dtype == np.int16

    def test_default_dtype(self):
        """Test default dtype is int16."""
        samples = np.zeros(1000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        result = bytes_to_numpy(audio_bytes)
        assert result.dtype == np.int16


class TestNumpyToBytes:
    """Test cases for numpy_to_bytes function."""

    def test_conversion(self):
        """Test converting numpy array to bytes."""
        samples = np.array([0, 1000, -1000, 500], dtype=np.int16)
        audio_bytes = numpy_to_bytes(samples)
        assert isinstance(audio_bytes, bytes)
        assert len(audio_bytes) == len(samples) * 2  # 2 bytes per int16


class TestNormalizeAudio:
    """Test cases for normalize_audio function."""

    def test_normalize_to_target(self):
        """Test normalizing audio to target level."""
        # Create audio with low amplitude
        samples = np.array([100, 200, -100, -200], dtype=np.int16)
        audio_bytes = samples.tobytes()

        normalized = normalize_audio(audio_bytes, target_db=-10.0)
        normalized_array = bytes_to_numpy(normalized)

        # Peak should be closer to -10 dBFS
        peak = np.max(np.abs(normalized_array))
        assert peak > 1000  # Should be amplified

    def test_silence_stays_silent(self):
        """Test that silent audio stays silent."""
        samples = np.zeros(1000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        normalized = normalize_audio(audio_bytes)
        normalized_array = bytes_to_numpy(normalized)

        assert np.all(normalized_array == 0)


class TestResampleAudio:
    """Test cases for resample_audio function."""

    def test_same_rate(self):
        """Test that same rate returns original."""
        samples = np.arange(16000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        result = resample_audio(audio_bytes, 16000, 16000)
        assert result == audio_bytes

    def test_downsample(self):
        """Test downsampling audio."""
        samples = np.arange(16000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        result = resample_audio(audio_bytes, 16000, 8000)
        result_array = bytes_to_numpy(result)

        # Should have approximately half the samples
        assert len(result_array) == 8000

    def test_upsample(self):
        """Test upsampling audio."""
        samples = np.arange(8000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        result = resample_audio(audio_bytes, 8000, 16000)
        result_array = bytes_to_numpy(result)

        # Should have approximately double the samples
        assert len(result_array) == 16000


class TestCalculateRMS:
    """Test cases for calculate_rms function."""

    def test_silence(self):
        """Test RMS of silence is zero."""
        samples = np.zeros(1000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        rms = calculate_rms(audio_bytes)
        assert rms == 0.0

    def test_full_scale(self):
        """Test RMS of full scale audio."""
        samples = np.full(1000, 32767, dtype=np.int16)
        audio_bytes = samples.tobytes()

        rms = calculate_rms(audio_bytes)
        assert rms > 0.9  # Should be close to 1.0


class TestCalculateDb:
    """Test cases for calculate_db function."""

    def test_silence_is_infinite(self):
        """Test dB of silence is -infinity."""
        samples = np.zeros(1000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        db = calculate_db(audio_bytes)
        assert db == float("-inf")

    def test_full_scale(self):
        """Test dB of full scale audio."""
        samples = np.full(1000, 32767, dtype=np.int16)
        audio_bytes = samples.tobytes()

        db = calculate_db(audio_bytes)
        assert db > -1.0  # Should be close to 0 dBFS


class TestIsSilence:
    """Test cases for is_silence function."""

    def test_true_silence(self):
        """Test that true silence is detected."""
        samples = np.zeros(1000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        assert is_silence(audio_bytes)

    def test_non_silence(self):
        """Test that non-silence is detected."""
        samples = np.full(1000, 1000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        assert not is_silence(audio_bytes)


class TestTrimSilence:
    """Test cases for trim_silence function."""

    def test_trim_leading_trailing(self):
        """Test trimming silence from beginning and end."""
        # Create audio with silence at start and end
        silence = np.zeros(1000, dtype=np.int16)
        signal = np.full(1000, 1000, dtype=np.int16)
        samples = np.concatenate([silence, signal, silence])
        audio_bytes = samples.tobytes()

        trimmed = trim_silence(audio_bytes)
        trimmed_array = bytes_to_numpy(trimmed)

        # Should be close to original signal length
        assert len(trimmed_array) == 1000

    def test_all_silence(self):
        """Test trimming when all is silence."""
        samples = np.zeros(1000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        trimmed = trim_silence(audio_bytes)
        assert trimmed == b""


class TestPreprocessForSTT:
    """Test cases for preprocess_for_stt function."""

    def test_resample(self):
        """Test resampling during preprocessing."""
        samples = np.zeros(16000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        result = preprocess_for_stt(audio_bytes, src_sample_rate=16000, dst_sample_rate=8000)
        result_array = bytes_to_numpy(result)

        # Should be resampled to 8kHz
        assert len(result_array) == 8000

    def test_no_change_when_rates_match(self):
        """Test no change when sample rates match."""
        samples = np.full(16000, 1000, dtype=np.int16)
        audio_bytes = samples.tobytes()

        result = preprocess_for_stt(audio_bytes, src_sample_rate=16000, dst_sample_rate=16000)
        result_array = bytes_to_numpy(result)

        # Should maintain same number of samples
        assert len(result_array) == 16000
