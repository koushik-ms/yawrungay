"""Speech recognition engines for Yawrungay."""

from yawrungay.recognition.base import BaseRecognizer
from yawrungay.recognition.faster_whisper import FasterWhisperRecognizer
from yawrungay.recognition.vosk import VoskRecognizer

__all__ = [
    "BaseRecognizer",
    "FasterWhisperRecognizer",
    "VoskRecognizer",
    "get_recognizer",
]


def get_recognizer(
    engine: str = "faster-whisper",
    model_size: str = "small",
    cache_dir: str | None = None,
    model_path: str | None = None,
) -> BaseRecognizer:
    """Factory function to get a speech recognizer instance.

    Args:
        engine: The recognition engine to use. Default: 'faster-whisper'.
            Options: 'faster-whisper', 'vosk'
        model_size: Size of the model. Default: 'small'.
            For faster-whisper: 'tiny', 'base', 'small', 'medium', 'large'
            For vosk: 'small', 'large'
        cache_dir: Directory to cache models. Default: ~/.cache/yawrungay/models
            Used by faster-whisper.
        model_path: Path to model directory. Default: ~/.cache/yawrungay/vosk-models
            Used by vosk.

    Returns:
        An instance of a BaseRecognizer subclass.

    Raises:
        ValueError: If the specified engine is not available.
    """
    if engine == "faster-whisper":
        return FasterWhisperRecognizer(
            model_size=model_size,
            cache_dir=cache_dir,
        )
    elif engine == "vosk":
        return VoskRecognizer(
            model_size=model_size,
            model_path=model_path,
        )
    else:
        raise ValueError(f"Unknown recognition engine '{engine}'. Available engines: 'faster-whisper', 'vosk'")
