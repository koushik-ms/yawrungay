# Yawrungay - Voice Assistant

A privacy-focused, offline voice assistant inspired by [numen](https://git.sr.ht/~geb/numen). This project uses SpeechRecognition library backed by offline speech-to-text models (faster-whisper, vosk, or similar) to listen for commands and perform actions on your computer.

## Overview

Yawrungay is designed to be:
- **Privacy-first**: All speech processing happens locally on your machine
- **Lightweight**: Uses efficient offline speech recognition models
- **Extensible**: Easy to add new commands and integrations
- **Keyboard-friendly**: Can be triggered and controlled via voice or keyboard shortcuts

## Features

- 🎤 Voice command recognition using offline STT models
- ⌨️ Text-to-speech feedback
- 🔧 System automation capabilities
- 📝 Dictation mode for text input
- ⚡ Low latency response
- 🔒 No cloud dependencies

## Architecture

```mermaid
graph TD
    A[Microphone] --> B[Audio Capture]
    B --> C[Speech Recognition Engine]
    C --> D{Command Parser}
    D --> E[Action Executor]
    D --> F[Text Dictation]
    E --> G[System Actions]
    E --> H[Application Control]
    F --> I[Text Input]
    C --> J[faster-whisper]
    C --> K[Vosk]
    C --> L[Other Offline Models]
```

## Prerequisites

- Python 3.12+
- uv (package manager)
- Microphone input device
- Sufficient disk space for speech models (~100MB-2GB depending on model)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/yawrungay.git
cd yawrungay

# Install dependencies using uv
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

## Configuration

Create a `.yawrungay/config.yaml` file in your project root (or any parent directory, search stops at git root):

```yaml
# Speech Recognition Settings
stt_engine: faster-whisper  # Options: faster-whisper, vosk
model_size: small          # For faster-whisper: tiny, base, small, medium, large
model_path: ~/.cache/yawrungay/models

# Audio Settings
input_device: default
sample_rate: 16000
chunk_size: 1024

# Wake Word
wake_word: hey jarvis
wake_word_sensitivity: 0.5

# Text-to-Speech
tts_engine: pyttsx3  # Options: pyttsx3, edge-tts
voice_rate: 180
voice_volume: 1.0

# Commands
command_timeout: 5.0
max_listening_duration: 30.0

# Logging
log_level: INFO
log_file: ~/.cache/yawrungay/logs/app.log
```

## Usage

### Basic Usage

```bash
# List available audio devices
python -m yawrungay devices

# Test audio capture
python -m yawrungay test-capture -d 3

# Transcribe audio using default settings from config
python -m yawrungay transcribe -d 5

# Transcribe with specific STT engine (overrides config)
python -m yawrungay transcribe -d 5 -e vosk
python -m yawrungay transcribe -d 5 -e faster-whisper

# Transcribe with specific engine and model size
python -m yawrungay transcribe -d 5 -e faster-whisper -m medium
python -m yawrungay transcribe -d 5 -e vosk -m large

# Show current configuration
python -m yawrungay config show

# Generate configuration file
python -m yawrungay config init
```

### Comparing STT Engines

You can easily compare the performance of different engines:

```bash
# Record and transcribe with faster-whisper
python -m yawrungay transcribe -d 5 -e faster-whisper -m small

# Record and transcribe the same audio with Vosk
python -m yawrungay transcribe -d 5 -e vosk -m small
```

### Command Mode (Future)

When activated, Yawrungay will be able to execute commands like:
- "Open [application name]"
- "Switch to [window name]"
- "Type [text]"
- "Press [key]"
- "Take screenshot"
- "Set volume to [0-100]"
- And more...

### Dictation Mode (Future)

Say "dictate" to enter dictation mode. Your speech will be typed directly into the active application.

## Supported Speech Recognition Engines

### faster-whisper
- High accuracy offline transcription
- Multiple model sizes available
- Good balance of speed and accuracy

### Vosk
- Lightweight recognition
- Fast initialization
- Good for real-time transcription

## Project Structure

```
yawrungay/
├── README.md              # This file
├── AGENTS.md              # AI agent guidance
├── pyproject.toml         # Project configuration
├── uv.lock               # Locked dependencies
├── src/
│   └── yawrungay/        # Source code
│       ├── __init__.py
│       ├── main.py       # Entry point
│       ├── audio/        # Audio capture and processing
│       ├── recognition/  # Speech recognition engines
│       ├── parsing/      # Command parsing
│       ├── actions/      # System automation actions
│       ├── tts/          # Text-to-speech
│       └── config/       # Configuration management
├── models/               # Speech model storage
├── logs/                 # Application logs
└── tests/                # Test suite
```

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run ruff check src/
uv run ruff format src/
```

### Type Checking

```bash
uv run mypy src/
```

## Roadmap

- [x] Implement audio capture module
- [x] Add audio preprocessing utilities
- [x] Implement faster-whisper integration
- [x] Create YAML configuration system
- [x] Build CLI with test and transcribe commands
- [x] Add comprehensive test suite
- [x] Add Vosk STT engine support
- [x] Implement continuous listening mode
- [x] Build command parsing system with phrase files
- [x] Add system automation actions (keyboard, mouse, shell)
- [ ] Create wake word detection
- [ ] Implement text-to-speech feedback
- [ ] Create GUI interface
- [ ] Add plugin system for custom commands
- [ ] Implement configuration wizard

## Inspiration

This project is inspired by [numen](https://git.sr.ht/~geb/numen), a voice-controlled assistant that prioritizes privacy and offline operation.

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request
