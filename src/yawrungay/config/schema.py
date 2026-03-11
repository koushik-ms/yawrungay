"""Configuration schema definitions for Yawrungay."""

from dataclasses import dataclass, field


@dataclass
class AudioConfig:
    """Audio capture configuration."""

    device: int | None = None
    """Audio device index. None = system default."""

    sample_rate: int = 16000
    """Sample rate in Hz."""

    chunk_size: int = 1024
    """Audio chunk size in samples."""

    channels: int = 1
    """Number of audio channels (1 = mono, 2 = stereo)."""


@dataclass
class FasterWhisperConfig:
    """faster-whisper specific configuration."""

    model_size: str = "small"
    """Model size: tiny, base, small, medium, large."""

    cache_dir: str = ""
    """Cache directory for models. Empty = ~/.cache/yawrungay/models."""

    compute_type: str = "int8"
    """Compute type for model inference: int8, float16, float32, default."""


@dataclass
class VoskConfig:
    """Vosk specific configuration."""

    model_path: str = ""
    """Path to Vosk model. Empty = ~/.cache/yawrungay/vosk-models."""


@dataclass
class SpeechRecognitionConfig:
    """Speech recognition configuration."""

    engine: str = "faster-whisper"
    """STT engine: faster-whisper, vosk."""

    faster_whisper: FasterWhisperConfig = field(default_factory=FasterWhisperConfig)
    """faster-whisper engine settings."""

    vosk: VoskConfig = field(default_factory=VoskConfig)
    """Vosk engine settings."""


@dataclass
class TTSConfig:
    """Text-to-speech configuration."""

    engine: str = "pyttsx3"
    """TTS engine: pyttsx3, edge-tts."""

    voice_rate: int = 180
    """Speech rate (words per minute)."""

    voice_volume: float = 1.0
    """Volume level (0.0 to 1.0)."""


@dataclass
class WakeWordConfig:
    """Wake word detection configuration."""

    enabled: bool = False
    """Enable wake word detection."""

    keyword: str = "yawrungay"
    """Wake word keyword."""

    sensitivity: float = 0.5
    """Wake word sensitivity (0.0 to 1.0)."""


@dataclass
class CommandConfig:
    """Command execution configuration."""

    timeout: float = 5.0
    """Command execution timeout in seconds."""

    max_listening_duration: float = 30.0
    """Maximum listening duration in seconds."""


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    """Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL."""

    file: str = ""
    """Log file path. Empty = ~/.cache/yawrungay/logs/app.log."""

    console_output: bool = True
    """Enable console logging."""


@dataclass
class AppConfig:
    """Complete application configuration."""

    audio: AudioConfig = field(default_factory=AudioConfig)
    """Audio capture settings."""

    speech_recognition: SpeechRecognitionConfig = field(default_factory=SpeechRecognitionConfig)
    """Speech recognition settings."""

    tts: TTSConfig = field(default_factory=TTSConfig)
    """Text-to-speech settings."""

    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    """Wake word settings."""

    commands: CommandConfig = field(default_factory=CommandConfig)
    """Command execution settings."""

    logging: LoggingConfig = field(default_factory=LoggingConfig)
    """Logging settings."""
