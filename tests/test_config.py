"""Tests for configuration management."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from yawrungay.config import ConfigError, Settings
from yawrungay.config.schema import AppConfig


class TestAppConfig:
    """Test cases for AppConfig dataclass."""

    def test_default_config(self):
        """Test that default config is created correctly."""
        config = AppConfig()
        assert config.audio.device is None
        assert config.audio.sample_rate == 16000
        assert config.speech_recognition.engine == "faster-whisper"
        assert config.speech_recognition.faster_whisper.model_size == "small"
        assert config.logging.level == "INFO"

    def test_audio_config_custom_values(self):
        """Test custom audio configuration."""
        from yawrungay.config.schema import AudioConfig

        audio = AudioConfig(device=1, sample_rate=44100, channels=2)
        assert audio.device == 1
        assert audio.sample_rate == 44100
        assert audio.channels == 2


class TestSettingsLoading:
    """Test cases for Settings loading."""

    def test_default_settings(self):
        """Test that default settings are loaded when no config files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory to avoid loading project config
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                    settings = Settings()
                    assert settings.get_stt_engine() == "faster-whisper"
                    assert settings.get_model_size() == "small"
                    assert settings.get_log_level() == "INFO"

    def test_load_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
speech_recognition:
  engine: vosk
  faster_whisper:
    model_size: base
audio:
  sample_rate: 44100
logging:
  level: DEBUG
""")
            f.flush()
            config_path = f.name

        try:
            settings = Settings(custom_config_path=config_path)
            assert settings.get_stt_engine() == "vosk"
            assert settings.get_model_size() == "base"
            assert settings.get_sample_rate() == 44100
            assert settings.get_log_level() == "DEBUG"
        finally:
            Path(config_path).unlink()

    def test_custom_config_takes_priority(self):
        """Test that custom config path takes highest priority."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
speech_recognition:
  engine: vosk
""")
            f.flush()
            custom_config = f.name

        try:
            settings = Settings(custom_config_path=custom_config)
            assert settings.get_stt_engine() == "vosk"
        finally:
            Path(custom_config).unlink()

    def test_missing_custom_config_raises_error(self):
        """Test that missing custom config file raises ConfigError."""
        with pytest.raises(ConfigError, match="Custom config file not found"):
            Settings(custom_config_path="/nonexistent/config.yaml")


class TestSettingsValidation:
    """Test cases for configuration validation."""

    def test_invalid_stt_engine_raises_error(self):
        """Test that invalid STT engine raises ConfigError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
speech_recognition:
  engine: invalid-engine
""")
            f.flush()
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid STT engine"):
                Settings(custom_config_path=config_path)
        finally:
            Path(config_path).unlink()

    def test_invalid_model_size_raises_error(self):
        """Test that invalid model size raises ConfigError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
speech_recognition:
  faster_whisper:
    model_size: invalid-size
""")
            f.flush()
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid model size"):
                Settings(custom_config_path=config_path)
        finally:
            Path(config_path).unlink()

    def test_invalid_log_level_raises_error(self):
        """Test that invalid log level raises ConfigError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
logging:
  level: INVALID
""")
            f.flush()
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid log level"):
                Settings(custom_config_path=config_path)
        finally:
            Path(config_path).unlink()

    def test_invalid_tts_engine_raises_error(self):
        """Test that invalid TTS engine raises ConfigError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
tts:
  engine: invalid-tts
""")
            f.flush()
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid TTS engine"):
                Settings(custom_config_path=config_path)
        finally:
            Path(config_path).unlink()

    def test_invalid_yaml_raises_error(self):
        """Test that invalid YAML syntax raises ConfigError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
invalid: yaml: syntax: here:
  - malformed
""")
            f.flush()
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid YAML"):
                Settings(custom_config_path=config_path)
        finally:
            Path(config_path).unlink()


class TestSettingsGetters:
    """Test cases for Settings getter methods."""

    def test_audio_getters(self):
        """Test audio configuration getters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
audio:
  device: 2
  sample_rate: 48000
  chunk_size: 2048
  channels: 2
""")
            f.flush()
            config_path = f.name

        try:
            settings = Settings(custom_config_path=config_path)
            assert settings.get_audio_device() == 2
            assert settings.get_sample_rate() == 48000
            assert settings.get_chunk_size() == 2048
            assert settings.get_channels() == 2
        finally:
            Path(config_path).unlink()

    def test_stt_getters(self):
        """Test speech recognition getters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
speech_recognition:
  engine: faster-whisper
  faster_whisper:
    model_size: large
    cache_dir: /custom/cache
""")
            f.flush()
            config_path = f.name

        try:
            settings = Settings(custom_config_path=config_path)
            assert settings.get_stt_engine() == "faster-whisper"
            assert settings.get_model_size() == "large"
            assert settings.get_model_cache_dir() == "/custom/cache"
        finally:
            Path(config_path).unlink()

    def test_tts_getters(self):
        """Test TTS configuration getters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
tts:
  engine: edge-tts
  voice_rate: 150
  voice_volume: 0.8
""")
            f.flush()
            config_path = f.name

        try:
            settings = Settings(custom_config_path=config_path)
            assert settings.get_tts_engine() == "edge-tts"
            assert settings.get_voice_rate() == 150
            assert settings.get_voice_volume() == 0.8
        finally:
            Path(config_path).unlink()

    def test_wake_word_getters(self):
        """Test wake word configuration getters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
wake_word:
  enabled: true
  keyword: hello
  sensitivity: 0.7
""")
            f.flush()
            config_path = f.name

        try:
            settings = Settings(custom_config_path=config_path)
            assert settings.is_wake_word_enabled() is True
            assert settings.get_wake_word() == "hello"
            assert settings.get_wake_word_sensitivity() == 0.7
        finally:
            Path(config_path).unlink()

    def test_command_getters(self):
        """Test command configuration getters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
commands:
  timeout: 10.0
  max_listening_duration: 60.0
""")
            f.flush()
            config_path = f.name

        try:
            settings = Settings(custom_config_path=config_path)
            assert settings.get_command_timeout() == 10.0
            assert settings.get_max_listening_duration() == 60.0
        finally:
            Path(config_path).unlink()

    def test_logging_getters(self):
        """Test logging configuration getters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
logging:
  level: WARNING
  console_output: false
""")
            f.flush()
            config_path = f.name

        try:
            settings = Settings(custom_config_path=config_path)
            assert settings.get_log_level() == "WARNING"
            assert settings.is_console_logging_enabled() is False
        finally:
            Path(config_path).unlink()


class TestPathExpansion:
    """Test cases for path expansion."""

    def test_model_cache_dir_default(self):
        """Test that default cache dir is expanded correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                    settings = Settings()
                    cache_dir = settings.get_model_cache_dir()
                    assert ".cache/yawrungay/models" in cache_dir

    def test_log_file_default(self):
        """Test that default log file is expanded correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                    settings = Settings()
                    log_file = settings.get_log_file()
                    assert ".cache/yawrungay/logs/app.log" in log_file

    def test_vosk_model_path_default(self):
        """Test that default Vosk model path is expanded correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                    settings = Settings()
                    model_path = settings.get_vosk_model_path()
                    assert ".cache/yawrungay/vosk-models" in model_path


class TestConfigToDict:
    """Test cases for config to_dict conversion."""

    def test_to_dict_contains_all_sections(self):
        """Test that to_dict includes all configuration sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                    settings = Settings()
                    config_dict = settings.to_dict()

                    assert "audio" in config_dict
                    assert "speech_recognition" in config_dict
                    assert "tts" in config_dict
                    assert "wake_word" in config_dict
                    assert "commands" in config_dict
                    assert "logging" in config_dict

    def test_to_dict_has_correct_values(self):
        """Test that to_dict contains correct values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
speech_recognition:
  engine: vosk
  faster_whisper:
    model_size: tiny
""")
            f.flush()
            config_path = f.name

        try:
            settings = Settings(custom_config_path=config_path)
            config_dict = settings.to_dict()
            assert config_dict["speech_recognition"]["engine"] == "vosk"
            assert config_dict["speech_recognition"]["faster_whisper"]["model_size"] == "tiny"
        finally:
            Path(config_path).unlink()


class TestCacheDirCreation:
    """Test cases for cache directory creation."""

    def test_cache_dir_created_on_init(self):
        """Test that cache directory is created on Settings init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            with patch("pathlib.Path.home", return_value=fake_home):
                with patch("pathlib.Path.cwd", return_value=fake_home):
                    settings = Settings()  # noqa: F841

                    cache_dir = fake_home / ".cache" / "yawrungay"
                    assert cache_dir.exists()
