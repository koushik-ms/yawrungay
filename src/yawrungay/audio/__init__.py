"""Audio module for capturing and processing audio.

This module provides functionality for:
- Enumerating audio input devices
- Capturing audio from microphones
- Preprocessing audio for speech recognition

Example:
    # List available devices
    from yawrungay.audio import list_audio_devices
    devices = list_audio_devices()

    # Capture audio
    from yawrungay.audio import AudioCapture
    with AudioCapture() as capture:
        capture.start()
        chunk = capture.read_chunk(timeout=1.0)

    # Preprocess audio
    from yawrungay.audio import preprocess_for_stt
    processed = preprocess_for_stt(audio_bytes, src_sample_rate=16000)
"""

from yawrungay.audio.capture import (
    AudioCapture,
    AudioCaptureError,
    AudioConfig,
    record_audio,
)
from yawrungay.audio.devices import (
    AudioDevice,
    get_default_input_device,
    get_device_info,
    list_audio_devices,
    print_device_list,
)
from yawrungay.audio.processing import (
    DEFAULT_MIN_SILENCE_DURATION,
    DEFAULT_SILENCE_THRESHOLD_DB,
    SilenceDetector,
    SilenceState,
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

__all__ = [
    # Capture
    "AudioCapture",
    "AudioCaptureError",
    "AudioConfig",
    "record_audio",
    # Devices
    "AudioDevice",
    "get_default_input_device",
    "get_device_info",
    "list_audio_devices",
    "print_device_list",
    # Processing
    "DEFAULT_MIN_SILENCE_DURATION",
    "DEFAULT_SILENCE_THRESHOLD_DB",
    "SilenceDetector",
    "SilenceState",
    "apply_noise_gate",
    "bytes_to_numpy",
    "calculate_db",
    "calculate_rms",
    "convert_format",
    "is_silence",
    "normalize_audio",
    "numpy_to_bytes",
    "preprocess_for_stt",
    "resample_audio",
    "trim_silence",
]
