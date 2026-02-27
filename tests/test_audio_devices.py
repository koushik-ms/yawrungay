"""Tests for audio devices module."""

import pytest

from yawrungay.audio.devices import AudioDevice, get_device_info, list_audio_devices


class TestAudioDevice:
    """Test cases for AudioDevice dataclass."""

    def test_device_creation(self):
        """Test creating an AudioDevice."""
        device = AudioDevice(
            index=0,
            name="Test Microphone",
            max_input_channels=2,
            default_sample_rate=48000.0,
        )
        assert device.index == 0
        assert device.name == "Test Microphone"
        assert device.max_input_channels == 2
        assert device.default_sample_rate == 48000.0
        assert not device.is_default

    def test_default_device_str(self):
        """Test string representation of default device."""
        device = AudioDevice(
            index=0,
            name="Default Mic",
            max_input_channels=1,
            default_sample_rate=16000.0,
            is_default=True,
        )
        str_repr = str(device)
        assert "[0]" in str_repr
        assert "Default Mic" in str_repr
        assert "(default)" in str_repr

    def test_non_default_device_str(self):
        """Test string representation of non-default device."""
        device = AudioDevice(
            index=1,
            name="Secondary Mic",
            max_input_channels=1,
            default_sample_rate=16000.0,
            is_default=False,
        )
        str_repr = str(device)
        assert "[1]" in str_repr
        assert "Secondary Mic" in str_repr
        assert "(default)" not in str_repr


class TestListAudioDevices:
    """Test cases for list_audio_devices function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        devices = list_audio_devices()
        assert isinstance(devices, list)

    def test_devices_are_audio_device_type(self):
        """Test that returned devices are AudioDevice instances."""
        devices = list_audio_devices()
        for device in devices:
            assert isinstance(device, AudioDevice)

    def test_devices_have_input_channels(self):
        """Test that returned devices have at least 1 input channel."""
        devices = list_audio_devices()
        for device in devices:
            assert device.max_input_channels > 0

    def test_at_most_one_default(self):
        """Test that at most one device is marked as default."""
        devices = list_audio_devices()
        default_count = sum(1 for d in devices if d.is_default)
        assert default_count <= 1


class TestGetDeviceInfo:
    """Test cases for get_device_info function."""

    def test_invalid_device_returns_none(self):
        """Test that invalid device index returns None."""
        # Use a very high index that shouldn't exist
        result = get_device_info(9999)
        assert result is None

    def test_valid_device(self):
        """Test getting info for a valid device."""
        devices = list_audio_devices()
        if devices:
            device_info = get_device_info(devices[0].index)
            assert device_info is not None
            assert device_info.index == devices[0].index
            assert isinstance(device_info.name, str)
            assert device_info.max_input_channels > 0
