"""Yawrungay - Voice Assistant Entry Point."""

import argparse
import json
import logging
import sys
import time

from yawrungay.audio import (
    AudioCapture,
    AudioCaptureError,
    AudioConfig,
    preprocess_for_stt,
    print_device_list,
)
from yawrungay.config import ConfigError, Settings
from yawrungay.recognition import get_recognizer

logger = logging.getLogger(__name__)
# Configure logging (will be overridden by settings)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def cmd_list_devices():
    """Command to list available audio devices."""
    print_device_list()


def cmd_test_capture(args):
    """Command to test audio capture."""
    duration = args.duration
    device_index = args.device

    print(f"Testing audio capture for {duration} seconds...")
    print("Speak into your microphone now!")

    config = AudioConfig(
        sample_rate=16000,
        chunk_size=1024,
        channels=1,
        device_index=device_index,
    )

    try:
        with AudioCapture(config) as capture:
            capture.start()
            print("Recording started...")

            # Record audio
            audio_data = capture.record(duration=duration)

            print(f"\nCaptured {len(audio_data)} bytes of audio")

            # Preprocess for STT
            processed = preprocess_for_stt(audio_data, src_sample_rate=16000)
            print(f"Processed to {len(processed)} bytes")

            print("\nAudio capture test completed successfully!")

    except AudioCaptureError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stream_test(args):
    """Command to test streaming audio capture."""
    duration = args.duration
    device_index = args.device

    print(f"Testing audio streaming for {duration} seconds...")
    print("Speak into your microphone now!")

    config = AudioConfig(
        sample_rate=16000,
        chunk_size=1024,
        channels=1,
        device_index=device_index,
    )

    try:
        with AudioCapture(config) as capture:
            capture.start()
            print("Streaming started...")

            start_time = time.time()
            chunks_received = 0
            bytes_received = 0

            for chunk in capture.read_chunks(timeout=0.1):
                if chunk is None:
                    continue

                chunks_received += 1
                bytes_received += len(chunk)

                # Print stats every second
                elapsed = time.time() - start_time
                if elapsed >= 1.0 and chunks_received % 10 == 0:
                    print(
                        f"\rChunks: {chunks_received}, Bytes: {bytes_received}, Queue: {capture.get_queue_size()}",
                        end="",
                        flush=True,
                    )

                if time.time() - start_time >= duration:
                    break

            print("\n\nStreaming completed!")
            print(f"Total chunks: {chunks_received}")
            print(f"Total bytes: {bytes_received}")

    except AudioCaptureError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_config_show(args):
    """Command to display current configuration."""
    try:
        settings = Settings(custom_config_path=args.config)
        config_dict = settings.to_dict()

        print("\n" + "=" * 60)
        print("CURRENT CONFIGURATION:")
        print("=" * 60)
        print(json.dumps(config_dict, indent=2))
        print("=" * 60 + "\n")

    except ConfigError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_config_init(args):
    """Command to generate a configuration template."""
    from pathlib import Path

    config_dir = Path.home() / ".config" / "yawrungay"
    config_file = config_dir / "config.yaml"

    try:
        config_dir.mkdir(parents=True, exist_ok=True)

        if config_file.exists() and not args.force:
            print(f"Configuration file already exists: {config_file}")
            print("Use --force to overwrite")
            sys.exit(1)

        # Read example config
        example_config_path = Path(__file__).parent.parent.parent / ".config.yaml.example"
        if not example_config_path.exists():
            print(f"Error: Example config file not found: {example_config_path}", file=sys.stderr)
            sys.exit(1)

        with open(example_config_path) as src:
            content = src.read()

        with open(config_file, "w") as dst:
            dst.write(content)

        print(f"Configuration template created: {config_file}")
        print("Edit the file to customize your settings")

    except OSError as e:
        print(f"Error creating configuration: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_transcribe(args):
    """Command to transcribe audio from microphone."""
    try:
        settings = Settings(custom_config_path=args.config)
    except ConfigError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Use CLI args if provided, otherwise use config
    duration = args.duration if args.duration else settings.get_max_listening_duration()
    device_index = args.device if args.device is not None else settings.get_audio_device()
    model_size = args.model_size if args.model_size else settings.get_model_size()

    print(f"Transcribing audio for {duration} seconds...")
    print("Speak into your microphone now!")

    config = AudioConfig(
        sample_rate=settings.get_sample_rate(),
        chunk_size=settings.get_chunk_size(),
        channels=settings.get_channels(),
        device_index=device_index,
    )

    try:
        # Initialize recognizer
        stt_engine = settings.get_stt_engine()
        print(f"\nLoading {stt_engine} model ({model_size})...")
        recognizer = get_recognizer(
            engine=stt_engine,
            model_size=model_size,
            cache_dir=settings.get_model_cache_dir() if stt_engine == "faster-whisper" else None,
        )
        recognizer.load_model()

        if not recognizer.is_ready():
            print("Error: Failed to load recognition model", file=sys.stderr)
            sys.exit(1)

        print("Model loaded successfully!")
        print("\nStarting recording...")

        # Capture audio
        with AudioCapture(config) as capture:
            capture.start()
            audio_data = capture.record(duration=duration)
            print(f"\nRecorded {len(audio_data)} bytes of audio")

            # Transcribe
            print("Transcribing audio...")
            text = recognizer.transcribe(audio_data)

            # Display results
            print("\n" + "=" * 60)
            print("TRANSCRIPTION RESULT:")
            print("=" * 60)
            print(text if text else "(No speech detected)")
            print("=" * 60)

        recognizer.cleanup()

    except AudioCaptureError as e:
        print(f"Audio Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Recognition Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        logger.exception("Unexpected error during transcription")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Yawrungay - Privacy-focused voice assistant",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to configuration file (overrides default locations)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List devices command
    subparsers.add_parser("devices", help="List available audio devices")

    # Test capture command
    capture_parser = subparsers.add_parser("test-capture", help="Test audio capture")
    capture_parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=3.0,
        help="Recording duration in seconds (default: 3.0)",
    )
    capture_parser.add_argument(
        "--device",
        "-D",
        type=int,
        default=None,
        help="Device index to use (default: system default)",
    )

    # Stream test command
    stream_parser = subparsers.add_parser("test-stream", help="Test audio streaming")
    stream_parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=5.0,
        help="Streaming duration in seconds (default: 5.0)",
    )
    stream_parser.add_argument(
        "--device",
        "-D",
        type=int,
        default=None,
        help="Device index to use (default: system default)",
    )

    # Transcribe command
    transcribe_parser = subparsers.add_parser("transcribe", help="Transcribe audio from microphone")
    transcribe_parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=None,
        help="Recording duration in seconds (overrides config)",
    )
    transcribe_parser.add_argument(
        "--device",
        "-D",
        type=int,
        default=None,
        help="Device index to use (default: from config)",
    )
    transcribe_parser.add_argument(
        "--model-size",
        "-m",
        type=str,
        choices=["tiny", "base", "small", "medium", "large"],
        default=None,
        help="Model size to use (overrides config)",
    )

    # Config commands
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="Config commands")

    config_show_parser = config_subparsers.add_parser("show", help="Display current configuration")
    config_show_parser.set_defaults(func=cmd_config_show)

    config_init_parser = config_subparsers.add_parser(
        "init",
        help="Generate configuration template in ~/.config/yawrungay/",
    )
    config_init_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing configuration",
    )
    config_init_parser.set_defaults(func=cmd_config_init)

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.command == "devices":
        cmd_list_devices()
    elif args.command == "test-capture":
        cmd_test_capture(args)
    elif args.command == "test-stream":
        cmd_stream_test(args)
    elif args.command == "transcribe":
        cmd_transcribe(args)
    elif args.command == "config":
        if hasattr(args, "func"):
            args.func(args)
        else:
            config_parser.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
