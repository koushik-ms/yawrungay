# AI Agent Guidelines for Yawrungay

This document provides guidance for AI agents working on the Yawrungay voice assistant project.

## Project Context

Yawrungay is a privacy-focused, offline voice assistant inspired by [numen](https://git.sr.ht/~geb/numen). The project has implemented core audio capture, configuration management, and faster-whisper speech recognition. Active development is ongoing for additional STT engines and voice command features.

## Technology Stack

- **Language**: Python 3.12+
- **Package Manager**: uv
- **Speech Recognition**: SpeechRecognition library with offline backends (faster-whisper, vosk)
- **Text-to-Speech**: pyttsx3 or edge-tts
- **Configuration**: YAML-based configuration

## Development Guidelines

### Code Style

- Follow PEP 8 style guide except allow max line length of 120 characters
- Use type hints for all function signatures and variables
- Prefer explicit over implicit
- Write docstrings for all public functions and classes
- Keep functions small and focused on single responsibilities

### Architecture Principles

1. **Modularity**: Each component (audio, recognition, parsing, actions, tts) should be independent
2. **Extensibility**: Design interfaces that allow easy addition of new STT engines and commands
3. **Error Handling**: Graceful degradation with informative error messages
4. **Testing**: Write tests for new features before implementation

### Asking Clarifying Questions

AI agents working on this project should use the question tool when:
- Design decisions have multiple valid approaches
- Requirements are ambiguous or incomplete
- Trade-offs exist between different implementation strategies
- User preferences are needed for behavior or configuration

Use the question tool proactively - confirming intent prevents rework and ensures the implementation matches user expectations.

### Implementation Order

When implementing features, follow this priority order:

1. **Audio Capture Module**
   - Microphone input handling
   - Audio buffering and chunking
   - Audio device enumeration

2. **Speech Recognition Integration**
   - faster-whisper integration (primary)
   - Vosk integration (secondary)
   - Model downloading and caching

3. **Command Parsing**
   - Natural language understanding
   - Command template matching
   - Entity extraction

4. **Action System**
   - System automation actions
   - Application control
   - Keyboard/mouse simulation

5. **Text-to-Speech**
   - TTS engine abstraction
   - Voice configuration
   - Response generation

6. **Wake Word Detection**
   - Keyword spotting
   - Sensitivity configuration

### File Naming Conventions

- **Modules**: lowercase with underscores (`audio_capture.py`)
- **Classes**: CamelCase (`AudioCapture`)
- **Functions**: lowercase with underscores (`get_audio_devices`)
- **Constants**: UPPERCASE with underscores (`SAMPLE_RATE`)
- **Tests**: `test_<module>.py`

### Module Structure

```
src/yawrungay/
├── __init__.py           # Package initialization
├── main.py               # Application entry point
├── config/
│   ├── __init__.py
│   ├── settings.py       # Configuration management
│   └── defaults.py       # Default configuration values
├── audio/
│   ├── __init__.py
│   ├── capture.py        # Microphone input handling
│   ├── processing.py     # Audio preprocessing
│   └── devices.py        # Audio device enumeration
├── recognition/
│   ├── __init__.py
│   ├── base.py           # Base recognizer interface
│   ├── faster_whisper.py # faster-whisper implementation
│   └── vosk.py          # Vosk implementation
├── parsing/
│   ├── __init__.py
│   ├── command_parser.py # Command parsing logic
│   ├── patterns.py       # Command patterns and templates
│   └── entities.py       # Entity extraction
├── actions/
│   ├── __init__.py
│   ├── base.py           # Base action interface
│   ├── system.py         # System operations
│   ├── application.py    # Application control
│   └── keyboard.py       # Keyboard simulation
├── tts/
│   ├── __init__.py
│   ├── base.py           # Base TTS interface
│   └── engine.py         # TTS engine implementations
└── utils/
    ├── __init__.py         # Shared utilities (path finding, git root detection)
    ├── logging.py          # Logging setup
    └── paths.py            # Path utilities
```

### Project Discovery Logic

Yawrungay discovers project-level configuration and phrases by searching for `.yawrungay` directories. This applies to both config files and phrase files.

**Search Behavior:**
- Starts from the current working directory
- Walks up through parent directories
- Stops at git repository root (if inside a git repo) OR user's home directory (if not in a git repo)
- Searches the boundary directory itself as well

**Priority Order (lowest to highest):**

For configuration (`~/.config/yawrungay/config.yaml`):
1. `/etc/yawrungay/config.yaml` (system - if present)
2. `~/.config/yawrungay/config.yaml` (user)
3. `.yawrungay/config.yaml` in cwd/parents (project - highest)

For phrases:
1. `/etc/yawrungay/phrases/` (system)
2. `~/.config/yawrungay/phrases/` (user)
3. `.yawrungay/phrases/` in cwd/parents (project - highest)

Project-level files are loaded last, so they take priority over user and system settings.

### Utility Functions

Shared utilities are in `src/yawrungay/utils/__init__.py`:
- `find_git_root(start: Path) -> Path`: Finds git repository root, returns home if not in git repo
- `find_project_dirs(start: Path, dirname: str) -> list[Path]`: Finds project directories by name

### Configuration Files

- `pyproject.toml`: Project metadata and dependencies
- `.yawrungay/config.yaml`: User configuration (create from template)
- `.env.example`: Environment variables template
- `.config.yaml.example`: Reference template (for reference only, use `config init` to create config)

### Adding New Configuration Settings

When adding new configuration options, follow these steps to ensure proper integration:

1. **Add to schema** (`src/yawrungay/config/schema.py`):
   - Add a new dataclass or extend existing one with the new field
   - Include type hints and default values

2. **Update config init** (`src/yawrungay/config/__init__.py`):
   - Add the new field to `generate_config_template()` function
   - This ensures `config init` generates complete configs with defaults

3. **Add getter method** (`src/yawrungay/config/settings.py`):
   - Add a getter method to access the new configuration value
   - Follow the pattern of existing getters

4. **Update documentation**:
   - Add the new option to `.config.yaml.example` with comments
   - Update README.md if needed

Example:
```python
# 1. schema.py - Add field
@dataclass
class NewFeatureConfig:
    enabled: bool = False
    option: str = "default"

# 2. __init__.py - Add to template
def generate_config_template() -> dict:
    return {
        # ... existing fields ...
        "new_feature": {
            "enabled": False,
            "option": "default",
        },
    }

# 3. settings.py - Add getter
def is_new_feature_enabled(self) -> bool:
    return self._config.new_feature.enabled
```

### Dependencies

Add dependencies using uv:

```bash
uv add package-name
uv add --dev package-name  # For development dependencies
```

### Common Development Tasks

#### Running the Application

```bash
uv run python -m yawrungay
```

#### Running Tests

```bash
uv run pytest
```

#### Code Quality

```bash
uv run ruff check src/     # Linting
uv run ruff format src/    # Formatting
uv run mypy src/          # Type checking
```

## Key Concepts

### Speech Recognition Flow

1. Audio is captured from microphone in chunks
2. Audio is processed to remove noise and normalize
3. Processed audio is sent to STT engine
4. Transcribed text is parsed for commands
5. Commands are executed by action system
6. Feedback is provided via TTS or console

### Command Structure

Commands follow a natural language pattern:

```
[action] [target] [modifiers]
```

Examples:
- "Open Firefox"
- "Switch to Terminal window"
- "Type Hello world"
- "Set volume to 50 percent"

### Wake Word

The wake word activates the command listening mode. Default: "yawrungay"

## Important Notes

- **No Cloud APIs**: All processing must be done locally
- **Cross-platform**: Support Linux, macOS, and Windows
- **Performance**: Minimize latency for responsive interaction
- **Privacy**: No audio or text data leaves the local machine
- **Offline-first**: Assume no internet connection

## Current State

- ✅ Project structure initialized
- ✅ Documentation in sync with implementation
- ✅ Audio capture module (capture, devices, processing)
- ✅ Configuration management system (YAML-based)
- ✅ Speech recognition integration (faster-whisper)
- ✅ CLI with transcribe, test, and config commands
- ✅ Comprehensive test suite (183 tests)
- ✅ Vosk STT engine with auto-download
- ✅ Continuous listening mode (`listen` command)
- ✅ Command parsing system with phrase files
- ✅ Action system (keyboard, mouse, shell)
- ⬜ TTS integration
- ⬜ Wake word detection

## Getting Started for New AI Agents

1. Read [README.md](README.md) for project overview
2. Review this file for implementation guidelines
3. Check the roadmap in README.md for priority features
4. Start with audio capture module implementation
5. Write tests before implementing features
6. Follow code style guidelines strictly
7. Update documentation when adding new features

## Troubleshooting Common Issues

### Audio Device Issues
- Use `audio/devices.py` to enumerate available devices
- Handle device not found errors gracefully
- Support default device selection

### Model Loading
- Download models on first use
- Cache models in user config directory
- Handle model loading failures with clear messages

### Vosk Model Issues
- Models are auto-downloaded on first use
- Small model: ~40MB, good for testing
- Large model: ~1.8GB, better accuracy
- Manual download available from https://alphacephei.com/vosk/models
- Ensure sufficient disk space before download

### Performance Issues
- Use chunked audio processing
- Implement proper audio buffering
- Consider background threads for non-blocking operation

## Contact and Support

- Refer to [numen documentation](https://git.sr.ht/~geb/numen/tree/master/doc/numen.1.scd) for inspiration
- Or run `man numen` locally to get the manpage if web fetch fails
- Check existing issues in the repository
- Review commit history for implementation patterns
