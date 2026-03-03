"""Default configuration values for Yawrungay."""

from yawrungay.config.schema import AppConfig

# Allowed values for configuration options
ALLOWED_STT_ENGINES = ["faster-whisper", "vosk"]
ALLOWED_TTS_ENGINES = ["pyttsx3", "edge-tts"]
ALLOWED_MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]
ALLOWED_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Default configuration
DEFAULT_CONFIG = AppConfig()
