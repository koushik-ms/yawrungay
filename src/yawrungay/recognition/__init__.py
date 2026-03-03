"""Speech recognition engines for Yawrungay."""

from yawrungay.recognition.base import BaseRecognizer
from yawrungay.recognition.faster_whisper import FasterWhisperRecognizer

__all__ = [
    "BaseRecognizer",
    "FasterWhisperRecognizer",
    "get_recognizer",
]


def get_recognizer(
    engine: str = "faster-whisper",
    model_size: str = "small",
    cache_dir: str | None = None,
) -> BaseRecognizer:
    """Factory function to get a speech recognizer instance.

    Args:
        engine: The recognition engine to use. Default: 'faster-whisper'.
            Options: 'faster-whisper'
        model_size: Size of the model. Default: 'small'.
            Options: 'tiny', 'base', 'small', 'medium', 'large'
        cache_dir: Directory to cache models. Default: ~/.cache/yawrungay/models

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
    else:
        raise ValueError(f"Unknown recognition engine '{engine}'. Available engines: 'faster-whisper'")
