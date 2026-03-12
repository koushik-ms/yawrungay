"""Settings manager for Yawrungay configuration."""

import logging
from pathlib import Path
from typing import Any

import yaml

from yawrungay.config.defaults import (
    ALLOWED_COMPUTE_TYPES,
    ALLOWED_LOG_LEVELS,
    ALLOWED_MODEL_SIZES,
    ALLOWED_STT_ENGINES,
    ALLOWED_TTS_ENGINES,
    DEFAULT_CONFIG,
)
from yawrungay.config.schema import (
    AppConfig,
    AudioConfig,
    CommandConfig,
    FasterWhisperConfig,
    LoggingConfig,
    SpeechRecognitionConfig,
    TTSConfig,
    VoskConfig,
    WakeWordConfig,
)

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration loading or validation error."""

    pass


class Settings:
    """Application settings manager.

    Loads configuration from multiple sources in priority order:
    1. Custom config file (passed via -c flag)
    2. .yawrungay/config.yaml (project root or parent dirs, up to git root)
    3. ~/.config/yawrungay/config.yaml (user home)
    4. Hardcoded defaults
    """

    def __init__(self, custom_config_path: str | None = None) -> None:
        """Initialize settings.

        Args:
            custom_config_path: Path to custom config file. Takes highest priority.

        Raises:
            ConfigError: If configuration loading or validation fails.
        """
        self._config = self._load_config(custom_config_path)
        self._ensure_cache_dir()
        logger.debug(f"Configuration loaded: STT engine={self.get_stt_engine()}, model_size={self.get_model_size()}")

    def _load_config(self, custom_config_path: str | None) -> AppConfig:
        """Load configuration from files in priority order.

        Priority (highest to lowest):
        1. Custom config file (--config option)
        2. Project config (.yawrungay/config.yaml in cwd or parent dirs)
        3. User home config (~/.config/yawrungay/config.yaml)
        4. Hardcoded defaults

        Args:
            custom_config_path: Path to custom config file.

        Returns:
            Loaded and validated AppConfig.

        Raises:
            ConfigError: If configuration is invalid.
        """
        config_dict: dict[str, Any] = {}

        if custom_config_path:
            # Priority 1: Custom config takes exclusive priority
            config_path = Path(custom_config_path).expanduser()
            if config_path.exists():
                logger.info(f"Loading custom config from: {config_path}")
                config_dict.update(self._load_yaml(config_path))
            else:
                raise ConfigError(f"Custom config file not found: {config_path}")
        else:
            # Priority 3: User home config (loaded first, lower priority)
            home_config = Path.home() / ".config" / "yawrungay" / "config.yaml"
            if home_config.exists():
                logger.info(f"Loading user config from: {home_config}")
                config_dict.update(self._load_yaml(home_config))

            # Priority 2: Project config (overrides user config)
            # Search for .yawrungay/config.yaml starting from cwd, walking up to git root
            project_config = self._find_project_config()
            if project_config:
                logger.info(f"Loading project config from: {project_config.absolute()}")
                config_dict.update(self._load_yaml(project_config))

        return self._build_config(config_dict)

    @staticmethod
    def _find_project_config() -> Path | None:
        """Find project config by searching for .yawrungay directory.

        Searches from current working directory upward through parent
        directories, stopping at git repository root or user's home.

        Returns:
            Path to config.yaml if found, None otherwise.
        """
        from yawrungay.utils import find_project_dirs

        project_dirs = find_project_dirs(Path.cwd(), ".yawrungay")
        for yawrungay_dir in project_dirs:
            config_file = yawrungay_dir / "config.yaml"
            if config_file.exists():
                return config_file
        return None

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        """Load YAML file.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed YAML as dictionary.

        Raises:
            ConfigError: If YAML is invalid.
        """
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {path}: {e}") from e
        except OSError as e:
            raise ConfigError(f"Cannot read config file {path}: {e}") from e

    @staticmethod
    def _build_config(config_dict: dict[str, Any]) -> AppConfig:
        """Build AppConfig from dictionary, merging with defaults.

        Args:
            config_dict: Configuration dictionary from YAML files.

        Returns:
            Validated AppConfig instance.

        Raises:
            ConfigError: If configuration is invalid.
        """
        try:
            # Audio config
            audio_dict = config_dict.get("audio", {})
            audio = AudioConfig(
                device=audio_dict.get("device", DEFAULT_CONFIG.audio.device),
                sample_rate=audio_dict.get("sample_rate", DEFAULT_CONFIG.audio.sample_rate),
                chunk_size=audio_dict.get("chunk_size", DEFAULT_CONFIG.audio.chunk_size),
                channels=audio_dict.get("channels", DEFAULT_CONFIG.audio.channels),
            )

            # Speech Recognition config
            sr_dict = config_dict.get("speech_recognition", {})
            sr_engine = sr_dict.get("engine", DEFAULT_CONFIG.speech_recognition.engine)

            if sr_engine not in ALLOWED_STT_ENGINES:
                raise ConfigError(f"Invalid STT engine: {sr_engine}. Allowed: {', '.join(ALLOWED_STT_ENGINES)}")

            fw_dict = sr_dict.get("faster_whisper", {})
            fw_model_size = fw_dict.get("model_size", DEFAULT_CONFIG.speech_recognition.faster_whisper.model_size)
            if fw_model_size not in ALLOWED_MODEL_SIZES:
                raise ConfigError(f"Invalid model size: {fw_model_size}. Allowed: {', '.join(ALLOWED_MODEL_SIZES)}")

            fw_compute_type = fw_dict.get("compute_type", DEFAULT_CONFIG.speech_recognition.faster_whisper.compute_type)
            if fw_compute_type not in ALLOWED_COMPUTE_TYPES:
                raise ConfigError(
                    f"Invalid compute type: {fw_compute_type}. Allowed: {', '.join(ALLOWED_COMPUTE_TYPES)}"
                )

            faster_whisper = FasterWhisperConfig(
                model_size=fw_model_size,
                cache_dir=fw_dict.get("cache_dir", DEFAULT_CONFIG.speech_recognition.faster_whisper.cache_dir),
                compute_type=fw_compute_type,
            )

            vosk_dict = sr_dict.get("vosk", {})
            vosk = VoskConfig(
                model_path=vosk_dict.get("model_path", DEFAULT_CONFIG.speech_recognition.vosk.model_path),
            )

            speech_recognition = SpeechRecognitionConfig(
                engine=sr_engine,
                faster_whisper=faster_whisper,
                vosk=vosk,
            )

            # TTS config
            tts_dict = config_dict.get("tts", {})
            tts_engine = tts_dict.get("engine", DEFAULT_CONFIG.tts.engine)
            if tts_engine not in ALLOWED_TTS_ENGINES:
                raise ConfigError(f"Invalid TTS engine: {tts_engine}. Allowed: {', '.join(ALLOWED_TTS_ENGINES)}")

            tts = TTSConfig(
                engine=tts_engine,
                voice_rate=tts_dict.get("voice_rate", DEFAULT_CONFIG.tts.voice_rate),
                voice_volume=tts_dict.get("voice_volume", DEFAULT_CONFIG.tts.voice_volume),
            )

            # Wake word config
            ww_dict = config_dict.get("wake_word", {})
            wake_word = WakeWordConfig(
                enabled=ww_dict.get("enabled", DEFAULT_CONFIG.wake_word.enabled),
                keyword=ww_dict.get("keyword", DEFAULT_CONFIG.wake_word.keyword),
                sensitivity=ww_dict.get("sensitivity", DEFAULT_CONFIG.wake_word.sensitivity),
            )

            # Command config
            cmd_dict = config_dict.get("commands", {})
            commands = CommandConfig(
                timeout=cmd_dict.get("timeout", DEFAULT_CONFIG.commands.timeout),
                max_listening_duration=cmd_dict.get(
                    "max_listening_duration", DEFAULT_CONFIG.commands.max_listening_duration
                ),
            )

            # Logging config
            log_dict = config_dict.get("logging", {})
            log_level = log_dict.get("level", DEFAULT_CONFIG.logging.level)
            if log_level not in ALLOWED_LOG_LEVELS:
                raise ConfigError(f"Invalid log level: {log_level}. Allowed: {', '.join(ALLOWED_LOG_LEVELS)}")

            logging_config = LoggingConfig(
                level=log_level,
                file=log_dict.get("file", DEFAULT_CONFIG.logging.file),
                console_output=log_dict.get("console_output", DEFAULT_CONFIG.logging.console_output),
            )

            return AppConfig(
                audio=audio,
                speech_recognition=speech_recognition,
                tts=tts,
                wake_word=wake_word,
                commands=commands,
                logging=logging_config,
            )

        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to build configuration: {e}") from e

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        cache_dir = Path.home() / ".cache" / "yawrungay"
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Cache directory ready: {cache_dir}")

    # Audio getters
    def get_audio_device(self) -> int | None:
        """Get audio device index."""
        return self._config.audio.device

    def get_sample_rate(self) -> int:
        """Get sample rate."""
        return self._config.audio.sample_rate

    def get_chunk_size(self) -> int:
        """Get chunk size."""
        return self._config.audio.chunk_size

    def get_channels(self) -> int:
        """Get number of channels."""
        return self._config.audio.channels

    # Speech Recognition getters
    def get_stt_engine(self) -> str:
        """Get STT engine name."""
        return self._config.speech_recognition.engine

    def get_model_size(self) -> str:
        """Get model size for faster-whisper."""
        return self._config.speech_recognition.faster_whisper.model_size

    def get_model_cache_dir(self) -> str:
        """Get model cache directory for faster-whisper."""
        cache_dir = self._config.speech_recognition.faster_whisper.cache_dir
        if not cache_dir:
            cache_dir = str(Path.home() / ".cache" / "yawrungay" / "models")
        return cache_dir

    def get_compute_type(self) -> str:
        """Get compute type for faster-whisper."""
        return self._config.speech_recognition.faster_whisper.compute_type

    def get_vosk_model_path(self) -> str:
        """Get Vosk model path."""
        model_path = self._config.speech_recognition.vosk.model_path
        if not model_path:
            model_path = str(Path.home() / ".cache" / "yawrungay" / "vosk-models")
        return model_path

    # TTS getters
    def get_tts_engine(self) -> str:
        """Get TTS engine name."""
        return self._config.tts.engine

    def get_voice_rate(self) -> int:
        """Get voice rate."""
        return self._config.tts.voice_rate

    def get_voice_volume(self) -> float:
        """Get voice volume."""
        return self._config.tts.voice_volume

    # Wake word getters
    def is_wake_word_enabled(self) -> bool:
        """Check if wake word detection is enabled."""
        return self._config.wake_word.enabled

    def get_wake_word(self) -> str:
        """Get wake word keyword."""
        return self._config.wake_word.keyword

    def get_wake_word_sensitivity(self) -> float:
        """Get wake word sensitivity."""
        return self._config.wake_word.sensitivity

    # Command getters
    def get_command_timeout(self) -> float:
        """Get command execution timeout."""
        return self._config.commands.timeout

    def get_max_listening_duration(self) -> float:
        """Get maximum listening duration."""
        return self._config.commands.max_listening_duration

    # Logging getters
    def get_log_level(self) -> str:
        """Get log level."""
        return self._config.logging.level

    def get_log_file(self) -> str:
        """Get log file path."""
        log_file = self._config.logging.file
        if not log_file:
            log_file = str(Path.home() / ".cache" / "yawrungay" / "logs" / "app.log")
        return log_file

    def is_console_logging_enabled(self) -> bool:
        """Check if console logging is enabled."""
        return self._config.logging.console_output

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for display.

        Returns:
            Configuration as nested dictionary.
        """
        return {
            "audio": {
                "device": self._config.audio.device,
                "sample_rate": self._config.audio.sample_rate,
                "chunk_size": self._config.audio.chunk_size,
                "channels": self._config.audio.channels,
            },
            "speech_recognition": {
                "engine": self._config.speech_recognition.engine,
                "faster_whisper": {
                    "model_size": self._config.speech_recognition.faster_whisper.model_size,
                    "cache_dir": self.get_model_cache_dir(),
                },
                "vosk": {
                    "model_path": self.get_vosk_model_path(),
                },
            },
            "tts": {
                "engine": self._config.tts.engine,
                "voice_rate": self._config.tts.voice_rate,
                "voice_volume": self._config.tts.voice_volume,
            },
            "wake_word": {
                "enabled": self._config.wake_word.enabled,
                "keyword": self._config.wake_word.keyword,
                "sensitivity": self._config.wake_word.sensitivity,
            },
            "commands": {
                "timeout": self._config.commands.timeout,
                "max_listening_duration": self._config.commands.max_listening_duration,
            },
            "logging": {
                "level": self._config.logging.level,
                "file": self.get_log_file(),
                "console_output": self._config.logging.console_output,
            },
        }
