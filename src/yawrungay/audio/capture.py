"""Audio capture using PyAudio with callback-based streaming."""

import logging
import queue
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Callable, Generator, Optional

import numpy as np
import pyaudio

from yawrungay.audio.devices import AudioDevice, get_device_info

logger = logging.getLogger(__name__)

# Default audio parameters optimized for speech recognition
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHUNK_SIZE = 1024
DEFAULT_CHANNELS = 1
DEFAULT_FORMAT = pyaudio.paInt16
DEFAULT_MAX_QUEUE_SIZE = 100


class AudioCaptureError(Exception):
    """Exception raised for audio capture errors."""

    pass


@dataclass
class AudioConfig:
    """Configuration for audio capture.

    Attributes:
        sample_rate: Sample rate in Hz (default 16000).
        chunk_size: Number of frames per chunk (default 1024).
        channels: Number of audio channels (default 1 for mono).
        format: PyAudio format constant (default paInt16).
        device_index: Specific device index, or None for default.
        max_queue_size: Maximum chunks in queue before dropping (default 100).
    """

    sample_rate: int = DEFAULT_SAMPLE_RATE
    chunk_size: int = DEFAULT_CHUNK_SIZE
    channels: int = DEFAULT_CHANNELS
    format: int = DEFAULT_FORMAT
    device_index: Optional[int] = None
    max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE


class AudioCapture:
    """Capture audio from microphone using PyAudio callbacks.

    This class provides thread-safe audio capture with a simple chunk queue.
    Audio data is collected via PyAudio callbacks and stored in a queue for
    processing.

    Example:
        with AudioCapture() as capture:
            capture.start()
            chunk = capture.read_chunk(timeout=1.0)
            if chunk is not None:
                # Process audio chunk
                pass
    """

    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        """Initialize audio capture.

        Args:
            config: Audio configuration. Uses defaults if not provided.
        """
        self.config = config or AudioConfig()
        self._pa: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._queue: queue.Queue[Optional[bytes]] = queue.Queue(maxsize=self.config.max_queue_size)
        self._is_capturing = False
        self._lock = threading.Lock()
        self._device: Optional[AudioDevice] = None

    def _get_device_info(self) -> AudioDevice:
        """Get device info for the configured device.

        Returns:
            AudioDevice information.

        Raises:
            AudioCaptureError: If device cannot be found.
        """
        if self.config.device_index is not None:
            device = get_device_info(self.config.device_index)
            if device is None:
                raise AudioCaptureError(f"Device index {self.config.device_index} not found or does not support input")
            return device
        else:
            # Get default device
            import yawrungay.audio.devices as devices_module

            device = devices_module.get_default_input_device()
            if device is None:
                raise AudioCaptureError("No default input device available")
            return device

    def _callback(
        self, in_data: Optional[bytes], frame_count: int, time_info: Mapping[str, float], status: int
    ) -> tuple[Optional[bytes], int]:
        """PyAudio callback function.

        Called by PyAudio when audio data is available. Puts data into queue.

        Args:
            in_data: Audio data bytes.
            frame_count: Number of frames in in_data.
            time_info: Dictionary with timing information.
            status: Callback status flags.

        Returns:
            Tuple of (out_data, flag) where out_data is None and flag indicates
            whether to continue.
        """
        if in_data is None:
            return (None, pyaudio.paContinue)

        # Try to put data in queue without blocking
        try:
            self._queue.put_nowait(in_data)
        except queue.Full:
            # Queue is full, drop oldest chunk
            try:
                self._queue.get_nowait()  # Remove oldest
                self._queue.put_nowait(in_data)  # Add new
            except queue.Empty:
                pass  # Queue became empty between get and put

        return (None, pyaudio.paContinue)

    def initialize(self) -> None:
        """Initialize PyAudio and verify device availability.

        Raises:
            AudioCaptureError: If initialization fails.
        """
        try:
            self._pa = pyaudio.PyAudio()
        except Exception as e:
            raise AudioCaptureError(f"Failed to initialize PyAudio: {e}") from e

        try:
            self._device = self._get_device_info()
            logger.info(f"Using audio device: {self._device}")
        except AudioCaptureError:
            self._pa.terminate()
            self._pa = None
            raise

    def start(self) -> None:
        """Start audio capture.

        Must call initialize() before start().

        Raises:
            AudioCaptureError: If capture cannot be started.
        """
        with self._lock:
            if self._is_capturing:
                logger.warning("Audio capture already started")
                return

            if self._pa is None:
                raise AudioCaptureError("Must call initialize() before start()")

            # Clear any existing data from queue
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break

            try:
                self._stream = self._pa.open(
                    format=self.config.format,
                    channels=self.config.channels,
                    rate=self.config.sample_rate,
                    input=True,
                    input_device_index=self._device.index if self._device else None,
                    frames_per_buffer=self.config.chunk_size,
                    stream_callback=self._callback,
                )
                self._is_capturing = True
                logger.info(
                    f"Started audio capture: {self.config.sample_rate}Hz, "
                    f"{self.config.channels}ch, chunk={self.config.chunk_size}"
                )
            except Exception as e:
                raise AudioCaptureError(f"Failed to start audio stream: {e}") from e

    def stop(self) -> None:
        """Stop audio capture."""
        with self._lock:
            if not self._is_capturing:
                return

            if self._stream is not None:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception as e:
                    logger.warning(f"Error stopping stream: {e}")
                finally:
                    self._stream = None

            self._is_capturing = False

            # Signal end of stream to any waiting readers
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass

            logger.info("Stopped audio capture")

    def read_chunk(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Read a single audio chunk from the queue.

        Args:
            timeout: Maximum time to wait for data in seconds. None means block
                indefinitely. 0 means non-blocking.

        Returns:
            Audio data as bytes, or None if stream ended or timeout occurred.
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def read_chunks(self, timeout: Optional[float] = None) -> Generator[bytes, None, None]:
        """Generator that yields audio chunks until stream ends.

        Args:
            timeout: Maximum time to wait for each chunk. None means block
                indefinitely.

        Yields:
            Audio data chunks as bytes.
        """
        while True:
            chunk = self.read_chunk(timeout=timeout)
            if chunk is None:
                break
            yield chunk

    def record(self, duration: float) -> bytes:
        """Record audio for a fixed duration.

        Args:
            duration: Duration to record in seconds.

        Returns:
            Recorded audio data as bytes.

        Raises:
            AudioCaptureError: If not capturing when called.
        """
        if not self.is_capturing:
            raise AudioCaptureError("Must start capture before recording")

        chunks: list[bytes] = []
        import time

        start_time = time.time()

        while time.time() - start_time < duration:
            chunk = self.read_chunk(timeout=0.1)
            if chunk is not None:
                chunks.append(chunk)

        return b"".join(chunks)

    def get_queue_size(self) -> int:
        """Get current number of chunks in queue.

        Returns:
            Number of chunks currently in the queue.
        """
        return self._queue.qsize()

    def clear_queue(self) -> None:
        """Clear all pending audio chunks from queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    @property
    def is_capturing(self) -> bool:
        """Check if currently capturing audio.

        Returns:
            True if capture is active, False otherwise.
        """
        with self._lock:
            return self._is_capturing

    @property
    def device(self) -> Optional[AudioDevice]:
        """Get the currently used audio device.

        Returns:
            AudioDevice information, or None if not initialized.
        """
        return self._device

    def close(self) -> None:
        """Close audio capture and release resources."""
        self.stop()

        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception as e:
                logger.warning(f"Error terminating PyAudio: {e}")
            finally:
                self._pa = None

        logger.info("Audio capture closed")

    def __enter__(self) -> "AudioCapture":
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


@contextmanager
def record_audio(
    duration: float,
    config: Optional[AudioConfig] = None,
) -> Generator[bytes, None, None]:
    """Context manager for recording audio.

    Convenience function for simple recording scenarios.

    Args:
        duration: Duration to record in seconds.
        config: Audio configuration. Uses defaults if not provided.

    Yields:
        Recorded audio data as bytes.

    Example:
        with record_audio(duration=5.0) as audio_data:
            # Process 5 seconds of audio
            pass
    """
    capture = AudioCapture(config)
    with capture:
        capture.start()
        yield capture.record(duration)
