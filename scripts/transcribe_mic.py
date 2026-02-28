#!/usr/bin/env python3
"""Real-time speech-to-text transcription using faster-whisper."""

import io
import logging
import os

import speech_recognition as sr
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def suppress_alsa_errors():
    """Suppress ALSA error messages by redirecting stderr temporarily."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    return old_stderr, devnull


def restore_stderr(old_stderr: int, devnull: int) -> None:
    """Restore stderr after ALSA operations."""
    os.dup2(old_stderr, 2)
    os.close(devnull)
    os.close(old_stderr)


def find_default_input_device() -> int:
    """Find the default input device index using PyAudio.

    Returns:
        Device index of the default input device.

    Raises:
        RuntimeError: If no default input device is found.
    """
    import pyaudio

    old_stderr, devnull = suppress_alsa_errors()
    try:
        p = pyaudio.PyAudio()

        try:
            default_info = p.get_default_input_device_info()
            device_index = int(default_info["index"])
            logger.info(f"Default input device: [{device_index}] {default_info['name']}")
            p.terminate()
            return device_index
        except OSError:
            pass

        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            name = str(info["name"]).lower()
            if ("default" in name or "pulse" in name) and int(info["maxInputChannels"]) > 0:
                logger.info(f"Found input device: [{i}] {info['name']}")
                p.terminate()
                return i

        p.terminate()
        raise RuntimeError("No default input device found")
    finally:
        restore_stderr(old_stderr, devnull)


def main() -> None:
    model_size = "small"
    device = "cpu"
    compute_type = "int8"

    logger.info(f"Loading faster-whisper model: {model_size} (device={device}, compute_type={compute_type})")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    recognizer = sr.Recognizer()

    old_stderr, devnull = suppress_alsa_errors()
    try:
        device_index = find_default_input_device()
        microphone = sr.Microphone(device_index=device_index)
    finally:
        restore_stderr(old_stderr, devnull)

    logger.info("Adjusting for ambient noise...")
    old_stderr, devnull = suppress_alsa_errors()
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
    finally:
        restore_stderr(old_stderr, devnull)

    logger.info("Listening for speech... (Ctrl+C to stop)")

    while True:
        try:
            old_stderr, devnull = suppress_alsa_errors()
            try:
                with microphone as source:
                    audio = recognizer.listen(source, timeout=None, phrase_time_limit=10)
            finally:
                restore_stderr(old_stderr, devnull)

            logger.info("Transcribing...")
            # Convert raw audio data to a file-like object for faster-whisper
            audio_io = io.BytesIO(audio.get_wav_data())
            segments, info = model.transcribe(audio_io, beam_size=5)

            text = "".join(segment.text for segment in segments)
            print(f"You: {text.strip()}")

        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")


if __name__ == "__main__":
    main()
