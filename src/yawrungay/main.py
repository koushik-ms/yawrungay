"""Yawrungay - Voice Assistant Entry Point."""

import argparse
import logging
import sys
import time

from yawrungay.audio import (
    AudioCapture,
    AudioCaptureError,
    AudioConfig,
    list_audio_devices,
    preprocess_for_stt,
    print_device_list,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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

            print(f"\n\nStreaming completed!")
            print(f"Total chunks: {chunks_received}")
            print(f"Total bytes: {bytes_received}")

    except AudioCaptureError as e:
        print(f"Error: {e}", file=sys.stderr)
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

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.command == "devices":
        cmd_list_devices()
    elif args.command == "test-capture":
        cmd_test_capture(args)
    elif args.command == "test-stream":
        cmd_stream_test(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
