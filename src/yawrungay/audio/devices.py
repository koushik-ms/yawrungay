"""Audio device enumeration and management."""

from dataclasses import dataclass

import pyaudio


@dataclass
class AudioDevice:
    """Represents an audio input device.

    Attributes:
        index: Device index from PyAudio.
        name: Human-readable device name.
        max_input_channels: Maximum number of input channels.
        default_sample_rate: Default sample rate in Hz.
        is_default: Whether this is the system default input device.
    """

    index: int
    name: str
    max_input_channels: int
    default_sample_rate: float
    is_default: bool = False

    def __str__(self) -> str:
        """Return string representation of the device."""
        default_marker = " (default)" if self.is_default else ""
        return f"[{self.index}] {self.name}{default_marker}"


def list_audio_devices() -> list[AudioDevice]:
    """Enumerate all available audio input devices.

    Returns:
        List of AudioDevice objects representing available input devices.
        Only devices with at least 1 input channel are included.

    Raises:
        RuntimeError: If unable to initialize PyAudio.
    """
    devices: list[AudioDevice] = []

    try:
        p = pyaudio.PyAudio()
    except Exception as e:
        raise RuntimeError(f"Failed to initialize PyAudio: {e}") from e

    try:
        # Get default input device info
        try:
            default_device_index = p.get_default_input_device_info()["index"]
        except OSError:
            default_device_index = None

        # Enumerate all devices
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                max_input_channels = int(info.get("maxInputChannels", 0))

                # Only include devices with input channels
                if max_input_channels > 0:
                    device = AudioDevice(
                        index=i,
                        name=str(info.get("name", f"Device {i}")),
                        max_input_channels=max_input_channels,
                        default_sample_rate=float(info.get("defaultSampleRate", 44100.0)),
                        is_default=(i == default_device_index),
                    )
                    devices.append(device)
            except (OSError, ValueError):
                # Skip devices that can't be queried
                continue
    finally:
        p.terminate()

    return devices


def get_default_input_device() -> AudioDevice | None:
    """Get the system's default input device.

    Returns:
        AudioDevice representing the default input device, or None if no
        input devices are available.

    Raises:
        RuntimeError: If unable to initialize PyAudio.
    """
    try:
        p = pyaudio.PyAudio()
    except Exception as e:
        raise RuntimeError(f"Failed to initialize PyAudio: {e}") from e

    try:
        try:
            info = p.get_default_input_device_info()
            return AudioDevice(
                index=int(info["index"]),
                name=str(info["name"]),
                max_input_channels=int(info.get("maxInputChannels", 0)),
                default_sample_rate=float(info.get("defaultSampleRate", 44100.0)),
                is_default=True,
            )
        except OSError:
            return None
    finally:
        p.terminate()


def get_device_info(device_index: int) -> AudioDevice | None:
    """Get information about a specific audio device.

    Args:
        device_index: The index of the device to query.

    Returns:
        AudioDevice with device information, or None if device doesn't exist
        or doesn't support input.

    Raises:
        RuntimeError: If unable to initialize PyAudio.
    """
    try:
        p = pyaudio.PyAudio()
    except Exception as e:
        raise RuntimeError(f"Failed to initialize PyAudio: {e}") from e

    try:
        # Check if this is the default device
        try:
            default_index = p.get_default_input_device_info()["index"]
        except OSError:
            default_index = None

        try:
            info = p.get_device_info_by_index(device_index)
            max_input_channels = int(info.get("maxInputChannels", 0))

            if max_input_channels == 0:
                return None

            return AudioDevice(
                index=device_index,
                name=str(info.get("name", f"Device {device_index}")),
                max_input_channels=max_input_channels,
                default_sample_rate=float(info.get("defaultSampleRate", 44100.0)),
                is_default=(device_index == default_index),
            )
        except (OSError, ValueError):
            return None
    finally:
        p.terminate()


def print_device_list() -> None:
    """Print a formatted list of available audio input devices."""
    devices = list_audio_devices()

    if not devices:
        print("No audio input devices found.")
        return

    print(f"Found {len(devices)} audio input device(s):\n")
    for device in devices:
        print(f"  {device}")
        print(f"      Channels: {device.max_input_channels}")
        print(f"      Sample Rate: {int(device.default_sample_rate)} Hz")
        print()


if __name__ == "__main__":
    print_device_list()
