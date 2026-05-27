# Contributing to IP Prime

First off, thank you for contributing to IP Prime! This project is an advanced AI assistant powered by Google Gemini and tailored to deliver robust voice, vision, and system automation.

Here are the guidelines for contributing to IP Prime.

## Codebase Architecture

IP Prime is organized as follows:
- `main.py`: The system entry point and audio execution loop.
- `core/`: Core systems including session handling (`session.py`), centralized paths (`path_config.py`), and tool registry schemas (`tool_registry.py`).
- `actions/`: The independent tool modules (e.g. system control, browser automation, smart home, and autonomous autopilot).
- `memory/`: Long-term memory and session turn-log telemetry database.
- `tests/`: Zero-dependency unit tests running on standard `unittest`.

## Guidelines for Adding Features

1. **Keep main.py Lean:** Never add large inline functions or lists to `main.py`. Export them to modular action files under `actions/` or core modules under `core/`.
2. **Tool Registrations:** To register a new Gemini tool, append its description schema to `core/tool_registry.py` and implement its routing branch in `main.py`'s `IPRayPlayer._handle_tool_call()`.
3. **Type Annotation:** Ensure all new functions have strict Python type annotations.
4. **No Bare Excepts:** Always capture specific exception types, or use `except Exception as e:` and log it appropriately.
5. **No Emojis in Print Statements:** Do not use emoji characters in terminal-facing print logs, as this causes unicode print crashes in Windows command shells (specifically CP1252 encoding).

## Testing

Before making a Pull Request, run the local unit test suite and syntax checkers:
```bash
# Verify Python syntax
python -m pyflakes main.py core/ actions/ memory/ tests/

# Execute test suite
python -m unittest discover -s tests -p "test_*.py" -v
```

Ensure all tests pass and pyflakes returns zero critical syntax errors. Thank you!
