"""Audio preprocessing utilities."""

import logging
from typing import Optional

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)

# Default noise gate threshold (in dB relative to full scale)
DEFAULT_NOISE_GATE_THRESHOLD_DB = -40.0


def bytes_to_numpy(
    audio_bytes: bytes,
    dtype: npt.DTypeLike = np.int16,
    channels: int = 1,
) -> np.ndarray:
    """Convert audio bytes to numpy array.

    Args:
        audio_bytes: Raw audio data as bytes.
        dtype: Numpy data type (default int16 for 16-bit PCM).
        channels: Number of audio channels.

    Returns:
        Numpy array of audio samples with shape (samples, channels).
    """
    audio_array = np.frombuffer(audio_bytes, dtype=dtype)
    if channels > 1:
        audio_array = audio_array.reshape(-1, channels)
    return audio_array


def numpy_to_bytes(audio_array: np.ndarray) -> bytes:
    """Convert numpy array to audio bytes.

    Args:
        audio_array: Numpy array of audio samples.

    Returns:
        Raw audio data as bytes.
    """
    return audio_array.astype(np.int16).tobytes()


def normalize_audio(
    audio_bytes: bytes,
    target_db: float = -3.0,
    dtype: npt.DTypeLike = np.int16,
) -> bytes:
    """Normalize audio to target peak level.

    Normalizes audio so the peak amplitude equals the target dB level.

    Args:
        audio_bytes: Raw audio data as bytes.
        target_db: Target peak level in dB (default -3.0 dBFS).
        dtype: Numpy data type of the input audio.

    Returns:
        Normalized audio as bytes.
    """
    audio_array = bytes_to_numpy(audio_bytes, dtype=dtype)

    # Convert to float for processing
    if dtype == np.int16:
        max_val = 32767.0
        audio_float = audio_array.astype(np.float32) / max_val
    elif dtype == np.int32:
        max_val = 2147483647.0
        audio_float = audio_array.astype(np.float32) / max_val
    else:
        audio_float = audio_array.astype(np.float32)
        max_val = 1.0

    # Find current peak
    current_peak = np.max(np.abs(audio_float))
    if current_peak == 0:
        return audio_bytes  # Silence, nothing to normalize

    # Calculate gain needed
    target_linear = 10 ** (target_db / 20.0)
    gain = target_linear / current_peak

    # Apply gain
    normalized = audio_float * gain

    # Clip to prevent overflow
    normalized = np.clip(normalized, -1.0, 1.0)

    # Convert back to original dtype
    if dtype == np.int16:
        result = (normalized * max_val).astype(np.int16)
    elif dtype == np.int32:
        result = (normalized * max_val).astype(np.int32)
    else:
        result = normalized.astype(dtype)

    return result.tobytes()


def resample_audio(
    audio_bytes: bytes,
    src_rate: int,
    dst_rate: int,
    dtype: npt.DTypeLike = np.int16,
    channels: int = 1,
) -> bytes:
    """Resample audio from one sample rate to another.

    Uses simple linear interpolation for resampling. For production use,
    consider using a library like librosa or scipy.signal.resample.

    Args:
        audio_bytes: Raw audio data as bytes.
        src_rate: Source sample rate in Hz.
        dst_rate: Destination sample rate in Hz.
        dtype: Numpy data type of the audio.
        channels: Number of audio channels.

    Returns:
        Resampled audio as bytes.
    """
    if src_rate == dst_rate:
        return audio_bytes

    audio_array = bytes_to_numpy(audio_bytes, dtype=dtype, channels=channels)

    # Calculate new length
    src_length = len(audio_array)
    dst_length = int(src_length * dst_rate / src_rate)

    # Use numpy's interp for linear interpolation
    src_indices = np.linspace(0, src_length - 1, src_length)
    dst_indices = np.linspace(0, src_length - 1, dst_length)

    if channels == 1:
        resampled = np.interp(dst_indices, src_indices, audio_array)
    else:
        resampled = np.zeros((dst_length, channels), dtype=dtype)
        for ch in range(channels):
            resampled[:, ch] = np.interp(dst_indices, src_indices, audio_array[:, ch])

    return resampled.astype(dtype).tobytes()


def apply_noise_gate(
    audio_bytes: bytes,
    threshold_db: float = DEFAULT_NOISE_GATE_THRESHOLD_DB,
    attack_ms: float = 5.0,
    release_ms: float = 50.0,
    sample_rate: int = 16000,
    dtype: npt.DTypeLike = np.int16,
) -> bytes:
    """Apply noise gate to audio.

    Reduces audio below a certain threshold to silence.

    Args:
        audio_bytes: Raw audio data as bytes.
        threshold_db: Threshold in dB below which audio is gated (default -40).
        attack_ms: Attack time in milliseconds.
        release_ms: Release time in milliseconds.
        sample_rate: Sample rate of the audio.
        dtype: Numpy data type of the audio.

    Returns:
        Gated audio as bytes.
    """
    audio_array = bytes_to_numpy(audio_bytes, dtype=dtype)

    # Convert to float for processing
    if dtype == np.int16:
        max_val = 32767.0
        audio_float = audio_array.astype(np.float32) / max_val
    else:
        audio_float = audio_array.astype(np.float32)
        max_val = 1.0

    # Calculate threshold in linear scale
    threshold_linear = 10 ** (threshold_db / 20.0)

    # Calculate envelope
    envelope = np.abs(audio_float)

    # Convert attack/release times to samples
    attack_samples = max(1, int(attack_ms * sample_rate / 1000.0))
    release_samples = max(1, int(release_ms * sample_rate / 1000.0))

    # Simple noise gate implementation
    gain = np.ones_like(audio_float)
    current_gain = 1.0

    for i in range(len(envelope)):
        if envelope[i] > threshold_linear:
            # Attack phase - increase gain
            current_gain = min(1.0, current_gain + (1.0 / attack_samples))
        else:
            # Release phase - decrease gain
            current_gain = max(0.0, current_gain - (1.0 / release_samples))
        gain[i] = current_gain

    # Apply gain
    gated = audio_float * gain

    # Convert back to original dtype
    if dtype == np.int16:
        result = (gated * max_val).astype(np.int16)
    else:
        result = gated.astype(dtype)

    return result.tobytes()


def convert_format(
    audio_bytes: bytes,
    src_dtype: np.dtype,
    dst_dtype: np.dtype,
) -> bytes:
    """Convert audio from one format to another.

    Args:
        audio_bytes: Raw audio data as bytes.
        src_dtype: Source numpy data type.
        dst_dtype: Destination numpy data type.

    Returns:
        Converted audio as bytes.
    """
    audio_array = bytes_to_numpy(audio_bytes, dtype=src_dtype)

    # Convert to float [-1, 1] range
    if src_dtype == np.int16:
        audio_float = audio_array.astype(np.float32) / 32767.0
    elif src_dtype == np.int32:
        audio_float = audio_array.astype(np.float32) / 2147483647.0
    else:
        audio_float = audio_array.astype(np.float32)

    # Convert to destination format
    if dst_dtype == np.int16:
        result = (audio_float * 32767.0).astype(np.int16)
    elif dst_dtype == np.int32:
        result = (audio_float * 2147483647.0).astype(np.int32)
    else:
        result = audio_float.astype(dst_dtype)

    return result.tobytes()


def calculate_rms(audio_bytes: bytes, dtype: npt.DTypeLike = np.int16) -> float:
    """Calculate RMS (Root Mean Square) of audio.

    Args:
        audio_bytes: Raw audio data as bytes.
        dtype: Numpy data type of the audio.

    Returns:
        RMS value of the audio (normalized to 0.0-1.0 range).
    """
    audio_array = bytes_to_numpy(audio_bytes, dtype=dtype)

    # Convert to float
    if dtype == np.int16:
        audio_float = audio_array.astype(np.float32) / 32767.0
    else:
        audio_float = audio_array.astype(np.float32)

    # Calculate RMS
    rms = np.sqrt(np.mean(audio_float**2))
    return float(rms)


def calculate_db(audio_bytes: bytes, dtype: npt.DTypeLike = np.int16) -> float:
    """Calculate dB level of audio.

    Args:
        audio_bytes: Raw audio data as bytes.
        dtype: Numpy data type of the audio.

    Returns:
        dB level of the audio (relative to full scale).
    """
    rms = calculate_rms(audio_bytes, dtype)
    if rms == 0:
        return -np.inf
    return 20.0 * np.log10(rms)


def is_silence(
    audio_bytes: bytes,
    threshold_db: float = DEFAULT_NOISE_GATE_THRESHOLD_DB,
    dtype: npt.DTypeLike = np.int16,
) -> bool:
    """Check if audio is silence (below threshold).

    Args:
        audio_bytes: Raw audio data as bytes.
        threshold_db: Threshold in dB (default -40).
        dtype: Numpy data type of the audio.

    Returns:
        True if audio is below threshold, False otherwise.
    """
    db = calculate_db(audio_bytes, dtype)
    return db < threshold_db


def trim_silence(
    audio_bytes: bytes,
    threshold_db: float = DEFAULT_NOISE_GATE_THRESHOLD_DB,
    sample_rate: int = 16000,
    dtype: npt.DTypeLike = np.int16,
) -> bytes:
    """Trim silence from beginning and end of audio.

    Args:
        audio_bytes: Raw audio data as bytes.
        threshold_db: Threshold in dB for silence detection.
        sample_rate: Sample rate of the audio.
        dtype: Numpy data type of the audio.

    Returns:
        Trimmed audio as bytes.
    """
    audio_array = bytes_to_numpy(audio_bytes, dtype=dtype)

    # Convert to float for processing
    if dtype == np.int16:
        audio_float = audio_array.astype(np.float32) / 32767.0
    else:
        audio_float = audio_array.astype(np.float32)

    threshold_linear = 10 ** (threshold_db / 20.0)

    # Find start and end of non-silent audio
    non_silent = np.abs(audio_float) > threshold_linear

    if not np.any(non_silent):
        return b""  # Entirely silent

    start_idx = np.argmax(non_silent)
    end_idx = len(non_silent) - np.argmax(non_silent[::-1])

    trimmed = audio_array[start_idx:end_idx]
    return trimmed.tobytes()


def preprocess_for_stt(
    audio_bytes: bytes,
    src_sample_rate: int,
    dst_sample_rate: int = 16000,
    normalize: bool = True,
    noise_gate: bool = True,
    dtype: npt.DTypeLike = np.int16,
) -> bytes:
    """Preprocess audio for speech-to-text recognition.

    Applies common preprocessing steps:
    1. Resample to target sample rate
    2. Normalize audio levels
    3. Apply noise gate

    Args:
        audio_bytes: Raw audio data as bytes.
        src_sample_rate: Source sample rate in Hz.
        dst_sample_rate: Target sample rate in Hz (default 16000).
        normalize: Whether to normalize audio levels.
        noise_gate: Whether to apply noise gate.
        dtype: Numpy data type of the audio.

    Returns:
        Preprocessed audio as bytes.
    """
    # Resample if necessary
    if src_sample_rate != dst_sample_rate:
        audio_bytes = resample_audio(audio_bytes, src_sample_rate, dst_sample_rate, dtype)

    # Normalize
    if normalize:
        audio_bytes = normalize_audio(audio_bytes, target_db=-3.0, dtype=dtype)

    # Apply noise gate
    if noise_gate:
        audio_bytes = apply_noise_gate(audio_bytes, sample_rate=dst_sample_rate, dtype=dtype)

    return audio_bytes
