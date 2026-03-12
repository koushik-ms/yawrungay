"""Configuration management for Yawrungay."""

from yawrungay.config.defaults import DEFAULT_CONFIG
from yawrungay.config.schema import AppConfig
from yawrungay.config.settings import ConfigError, Settings


def generate_config_template() -> dict:
    """Generate complete configuration template from defaults.

    Returns:
        Dictionary containing all configuration options with default values.
    """
    return {
        "audio": {
            "device": DEFAULT_CONFIG.audio.device,
            "sample_rate": DEFAULT_CONFIG.audio.sample_rate,
            "chunk_size": DEFAULT_CONFIG.audio.chunk_size,
            "channels": DEFAULT_CONFIG.audio.channels,
        },
        "speech_recognition": {
            "engine": DEFAULT_CONFIG.speech_recognition.engine,
            "faster_whisper": {
                "model_size": DEFAULT_CONFIG.speech_recognition.faster_whisper.model_size,
                "cache_dir": DEFAULT_CONFIG.speech_recognition.faster_whisper.cache_dir,
                "compute_type": DEFAULT_CONFIG.speech_recognition.faster_whisper.compute_type,
            },
            "vosk": {
                "model_path": DEFAULT_CONFIG.speech_recognition.vosk.model_path,
            },
        },
        "tts": {
            "engine": DEFAULT_CONFIG.tts.engine,
            "voice_rate": DEFAULT_CONFIG.tts.voice_rate,
            "voice_volume": DEFAULT_CONFIG.tts.voice_volume,
        },
        "wake_word": {
            "enabled": DEFAULT_CONFIG.wake_word.enabled,
            "keyword": DEFAULT_CONFIG.wake_word.keyword,
            "sensitivity": DEFAULT_CONFIG.wake_word.sensitivity,
        },
        "commands": {
            "timeout": DEFAULT_CONFIG.commands.timeout,
            "max_listening_duration": DEFAULT_CONFIG.commands.max_listening_duration,
        },
        "logging": {
            "level": DEFAULT_CONFIG.logging.level,
            "file": DEFAULT_CONFIG.logging.file,
            "console_output": DEFAULT_CONFIG.logging.console_output,
        },
    }


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries.

    Values in override take precedence. For nested dicts, recursively merges.

    Args:
        base: Base dictionary (default values).
        override: Override dictionary (user values).

    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


__all__ = [
    "AppConfig",
    "Settings",
    "ConfigError",
    "generate_config_template",
    "deep_merge",
]
