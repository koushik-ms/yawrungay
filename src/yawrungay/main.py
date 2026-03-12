"""Yawrungay - Voice Assistant Entry Point."""

import argparse
import json
import logging
import signal
import sys
import time
from collections.abc import Generator

from yawrungay.audio import (
    AudioCapture,
    AudioCaptureError,
    AudioConfig,
    SilenceDetector,
    SilenceState,
    preprocess_for_stt,
    print_device_list,
)
from yawrungay.actions import ActionExecutor
from yawrungay.config import ConfigError, Settings
from yawrungay.parsing import CommandParser, PhraseFileLoader
from yawrungay.recognition import Utterance, get_recognizer

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
    try:
        settings = Settings(custom_config_path=args.config)
    except ConfigError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Use CLI args if provided, otherwise use config
    duration = args.duration
    device_index = args.device if args.device is not None else settings.get_audio_device()

    print(f"Testing audio capture for {duration} seconds...")
    print("Speak into your microphone now!")

    config = AudioConfig(
        sample_rate=settings.get_sample_rate(),
        chunk_size=settings.get_chunk_size(),
        channels=settings.get_channels(),
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
            processed = preprocess_for_stt(audio_data, src_sample_rate=settings.get_sample_rate())
            print(f"Processed to {len(processed)} bytes")

            print("\nAudio capture test completed successfully!")

    except AudioCaptureError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stream_test(args):
    """Command to test streaming audio capture."""
    try:
        settings = Settings(custom_config_path=args.config)
    except ConfigError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Use CLI args if provided, otherwise use config
    duration = args.duration
    device_index = args.device if args.device is not None else settings.get_audio_device()

    print(f"Testing audio streaming for {duration} seconds...")
    print("Speak into your microphone now!")

    config = AudioConfig(
        sample_rate=settings.get_sample_rate(),
        chunk_size=settings.get_chunk_size(),
        channels=settings.get_channels(),
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
    stt_engine = args.engine if args.engine else settings.get_stt_engine()

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
        print(f"\nLoading {stt_engine} model ({model_size})...")
        recognizer = get_recognizer(
            engine=stt_engine,
            model_size=model_size,
            cache_dir=settings.get_model_cache_dir() if stt_engine == "faster-whisper" else None,
            model_path=settings.get_vosk_model_path() if stt_engine == "vosk" else None,
            compute_type=settings.get_compute_type() if stt_engine == "faster-whisper" else "int8",
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


class StopListening(Exception):
    """Exception raised to stop continuous listening."""

    pass


def cmd_listen(args):
    """Command for continuous listening mode."""
    try:
        settings = Settings(custom_config_path=args.config)
    except ConfigError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Use CLI args if provided, otherwise use config
    device_index = args.device if args.device is not None else settings.get_audio_device()
    model_size = args.model_size if args.model_size else settings.get_model_size()
    stt_engine = args.engine if args.engine else settings.get_stt_engine()
    silence_threshold = args.silence_threshold if args.silence_threshold else -35.0
    silence_duration = args.silence_duration if args.silence_duration else 0.8
    output_json = args.json

    sample_rate = settings.get_sample_rate()
    chunk_size = settings.get_chunk_size()

    config = AudioConfig(
        sample_rate=sample_rate,
        chunk_size=chunk_size,
        channels=settings.get_channels(),
        device_index=device_index,
    )

    stop_flag = False

    def signal_handler(signum, frame):
        nonlocal stop_flag
        stop_flag = True
        logger.info("Received signal to stop listening")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info(f"Loading {stt_engine} model ({model_size})...")
        recognizer = get_recognizer(
            engine=stt_engine,
            model_size=model_size,
            cache_dir=settings.get_model_cache_dir() if stt_engine == "faster-whisper" else None,
            model_path=settings.get_vosk_model_path() if stt_engine == "vosk" else None,
            compute_type=settings.get_compute_type() if stt_engine == "faster-whisper" else "int8",
        )
        recognizer.load_model()

        if not recognizer.is_ready():
            print("Error: Failed to load recognition model", file=sys.stderr)
            sys.exit(1)

        logger.info("Model loaded successfully")

        def audio_generator() -> Generator[bytes, None, None]:
            """Generator yielding audio chunks until stop signal."""
            with AudioCapture(config) as capture:
                capture.start()
                logger.info("Listening... (press Ctrl+C to stop)")

                while not stop_flag:
                    chunk = capture.read_chunk(timeout=0.1)
                    if chunk is not None:
                        yield chunk

        def output_utterance(utterance: Utterance) -> None:
            """Output an utterance to stdout."""
            if not utterance.text:
                return

            if output_json:
                output = json.dumps(
                    {
                        "text": utterance.text,
                        "is_final": utterance.is_final,
                        "timestamp": time.time(),
                    },
                    ensure_ascii=False,
                )
                print(output, flush=True)
            else:
                print(utterance.text, flush=True)

        for utterance in recognizer.transcribe_stream(
            audio_generator(),
            silence_threshold_db=silence_threshold,
            min_silence_duration=silence_duration,
            sample_rate=sample_rate,
        ):
            output_utterance(utterance)

        recognizer.cleanup()
        logger.info("Listening stopped")

    except AudioCaptureError as e:
        print(f"Audio Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Recognition Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        logger.exception("Unexpected error during listening")
        sys.exit(1)


def _find_wake_word(text: str, wake_word: str) -> int:
    """Find wake word in text (case-insensitive).

    Args:
        text: The text to search in.
        wake_word: The wake word to find.

    Returns:
        Index where wake word starts, or -1 if not found.
    """
    text_lower = text.lower()
    wake_lower = wake_word.lower()
    return text_lower.find(wake_lower)


def _extract_command_after_wake_word(text: str, wake_word: str) -> str:
    """Extract the command portion after the wake word.

    Strips leading punctuation and whitespace after the wake word.

    Args:
        text: The full utterance text.
        wake_word: The wake word to find and skip.

    Returns:
        The text after the wake word, stripped of whitespace and punctuation.
    """
    idx = _find_wake_word(text, wake_word)
    if idx < 0:
        return ""
    # Skip past the wake word
    command = text[idx + len(wake_word) :]
    # Strip whitespace and common punctuation that may follow wake word
    command = command.lstrip(" \t\n\r,!.?;:").rstrip()
    return command


class MonitorState:
    """State machine for monitor command."""

    WAITING = "waiting"
    LISTENING_FOR_COMMAND = "listening"


def cmd_monitor(args):
    """Command for wake word monitoring mode.

    Listens continuously for the wake word, then parses and executes
    voice commands. Supports two modes:
    - Same utterance: "yawrungay type hello" executes immediately
    - Two-phase: "yawrungay" alone waits for next utterance as command
    """
    try:
        settings = Settings(custom_config_path=args.config)
    except ConfigError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Use CLI args if provided, otherwise use config
    device_index = args.device if args.device is not None else settings.get_audio_device()
    model_size = args.model_size if args.model_size else settings.get_model_size()
    stt_engine = args.engine if args.engine else settings.get_stt_engine()
    silence_threshold = args.silence_threshold if args.silence_threshold else -35.0
    silence_duration = args.silence_duration if args.silence_duration else 0.8
    output_json = args.json

    # Wake word from CLI or config
    wake_word = args.wake_word if args.wake_word else settings.get_wake_word()

    sample_rate = settings.get_sample_rate()
    chunk_size = settings.get_chunk_size()

    config = AudioConfig(
        sample_rate=sample_rate,
        chunk_size=chunk_size,
        channels=settings.get_channels(),
        device_index=device_index,
    )

    stop_flag = False

    def signal_handler(signum, frame):
        nonlocal stop_flag
        stop_flag = True
        logger.info("Received signal to stop monitoring")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize speech recognizer
        logger.info(f"Loading {stt_engine} model ({model_size})...")
        recognizer = get_recognizer(
            engine=stt_engine,
            model_size=model_size,
            cache_dir=settings.get_model_cache_dir() if stt_engine == "faster-whisper" else None,
            model_path=settings.get_vosk_model_path() if stt_engine == "vosk" else None,
            compute_type=settings.get_compute_type() if stt_engine == "faster-whisper" else "int8",
        )
        recognizer.load_model()

        if not recognizer.is_ready():
            print("Error: Failed to load recognition model", file=sys.stderr)
            sys.exit(1)

        logger.info("Model loaded successfully")

        # Initialize command parser with phrases
        phrase_loader = PhraseFileLoader()
        command_parser = CommandParser(phrase_loader=phrase_loader)
        logger.info(f"Loaded {len(command_parser._phrases)} phrases")

        # Initialize action executor
        executor = ActionExecutor()
        logger.info(f"Registered actions: {executor.get_registered_actions()}")

        def audio_generator() -> Generator[bytes, None, None]:
            """Generator yielding audio chunks until stop signal."""
            with AudioCapture(config) as capture:
                capture.start()
                logger.info(f"Monitoring for wake word '{wake_word}'... (press Ctrl+C to stop)")

                while not stop_flag:
                    chunk = capture.read_chunk(timeout=0.1)
                    if chunk is not None:
                        yield chunk

        def output_event(event_type: str, data: dict) -> None:
            """Output an event to stdout."""
            if output_json:
                output = json.dumps(
                    {
                        "event": event_type,
                        "timestamp": time.time(),
                        **data,
                    },
                    ensure_ascii=False,
                )
                print(output, flush=True)
            else:
                if event_type == "wake_word":
                    print(f"[Wake word detected: '{data.get('text', '')}']", flush=True)
                elif event_type == "command":
                    print(f"[Command: {data.get('action_type', '')} {data.get('arguments', {})}]", flush=True)
                elif event_type == "result":
                    success = data.get("success", False)
                    if success:
                        print(f"[Success: {data.get('message', '')}]", flush=True)
                    else:
                        print(f"[Failed: {data.get('error', '')}]", flush=True)
                elif event_type == "listening":
                    print("[Listening for command...]", flush=True)
                elif event_type == "no_command":
                    print(f"[No command recognized: '{data.get('text', '')}']", flush=True)

        # State machine
        state = MonitorState.WAITING

        for utterance in recognizer.transcribe_stream(
            audio_generator(),
            silence_threshold_db=silence_threshold,
            min_silence_duration=silence_duration,
            sample_rate=sample_rate,
        ):
            if not utterance.text:
                continue

            text = utterance.text.strip()
            logger.debug(f"Utterance: '{text}' (state: {state})")

            if state == MonitorState.WAITING:
                # Check for wake word
                if _find_wake_word(text, wake_word) >= 0:
                    # Extract any command after the wake word
                    command_text = _extract_command_after_wake_word(text, wake_word)

                    if command_text:
                        # Same utterance mode: wake word + command in one phrase
                        output_event("wake_word", {"text": text, "mode": "same_utterance"})

                        # Parse and execute command
                        parsed = command_parser.parse(command_text)
                        if parsed:
                            output_event(
                                "command",
                                {
                                    "action_type": parsed.action_type,
                                    "arguments": parsed.arguments,
                                    "raw": command_text,
                                },
                            )
                            result = executor.execute(parsed)
                            output_event(
                                "result",
                                {
                                    "success": result.success,
                                    "message": result.message,
                                    "error": result.error,
                                },
                            )
                        else:
                            output_event("no_command", {"text": command_text})
                        # Stay in WAITING state
                    else:
                        # Two-phase mode: wake word only, wait for command
                        output_event("wake_word", {"text": text, "mode": "two_phase"})
                        output_event("listening", {})
                        state = MonitorState.LISTENING_FOR_COMMAND

            elif state == MonitorState.LISTENING_FOR_COMMAND:
                # Parse the utterance as a command
                parsed = command_parser.parse(text)
                if parsed:
                    output_event(
                        "command",
                        {
                            "action_type": parsed.action_type,
                            "arguments": parsed.arguments,
                            "raw": text,
                        },
                    )
                    result = executor.execute(parsed)
                    output_event(
                        "result",
                        {
                            "success": result.success,
                            "message": result.message,
                            "error": result.error,
                        },
                    )
                else:
                    output_event("no_command", {"text": text})

                # Return to waiting for wake word
                state = MonitorState.WAITING

        recognizer.cleanup()
        logger.info("Monitoring stopped")

    except AudioCaptureError as e:
        print(f"Audio Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Recognition Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        logger.exception("Unexpected error during monitoring")
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
        default=None,
        help="Model size to use (overrides config). faster-whisper: tiny/base/small/medium/large, vosk: small/large",
    )
    transcribe_parser.add_argument(
        "--engine",
        "-e",
        type=str,
        choices=["faster-whisper", "vosk"],
        default=None,
        help="STT engine to use (overrides config). Options: faster-whisper, vosk",
    )

    # Listen command
    listen_parser = subparsers.add_parser(
        "listen",
        help="Continuous listening mode - transcribes speech and outputs text",
    )
    listen_parser.add_argument(
        "--device",
        "-D",
        type=int,
        default=None,
        help="Device index to use (default: from config)",
    )
    listen_parser.add_argument(
        "--model-size",
        "-m",
        type=str,
        default=None,
        help="Model size to use (overrides config). faster-whisper: tiny/base/small/medium/large, vosk: small/large",
    )
    listen_parser.add_argument(
        "--engine",
        "-e",
        type=str,
        choices=["faster-whisper", "vosk"],
        default=None,
        help="STT engine to use (overrides config). Options: faster-whisper, vosk",
    )
    listen_parser.add_argument(
        "--silence-threshold",
        "-t",
        type=float,
        default=-35.0,
        help="Silence threshold in dB (default: -35.0)",
    )
    listen_parser.add_argument(
        "--silence-duration",
        "-s",
        type=float,
        default=0.8,
        help="Silence duration in seconds to mark utterance end (default: 0.8)",
    )
    listen_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON lines instead of plain text",
    )

    # Monitor command
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Wake word monitoring mode - listens for wake word then executes commands",
    )
    monitor_parser.add_argument(
        "--device",
        "-D",
        type=int,
        default=None,
        help="Device index to use (default: from config)",
    )
    monitor_parser.add_argument(
        "--model-size",
        "-m",
        type=str,
        default=None,
        help="Model size to use (overrides config). faster-whisper: tiny/base/small/medium/large, vosk: small/large",
    )
    monitor_parser.add_argument(
        "--engine",
        "-e",
        type=str,
        choices=["faster-whisper", "vosk"],
        default=None,
        help="STT engine to use (overrides config). Options: faster-whisper, vosk",
    )
    monitor_parser.add_argument(
        "--silence-threshold",
        "-t",
        type=float,
        default=None,
        help="Silence threshold in dB (default: -35.0)",
    )
    monitor_parser.add_argument(
        "--silence-duration",
        "-s",
        type=float,
        default=None,
        help="Silence duration in seconds to mark utterance end (default: 0.8)",
    )
    monitor_parser.add_argument(
        "--wake-word",
        "-w",
        type=str,
        default=None,
        help="Wake word to listen for (default: from config, 'yawrungay')",
    )
    monitor_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON lines instead of plain text",
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
    elif args.command == "listen":
        cmd_listen(args)
    elif args.command == "monitor":
        cmd_monitor(args)
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
