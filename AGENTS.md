# AGENTS.md

This project is a simple Python-based scoreboard for data verification.

## Build, Lint, Test

- **Run Demo**: To see a demonstration, run the main script:
  ```bash
  python scoreboard.py
  ```
- **Run Tests**: To run the full test suite, use the `unittest` module:
  ```bash
  python -m unittest test_scoreboard.py
  ```
- **Run a Single Test**: To run a specific test case:
  ```bash
  python -m unittest test_scoreboard.TestScoreboard.test_single_match
  ```
- **Linting**: No linter is configured. Please adhere to PEP 8 standards.

## Code Style Guidelines

- **Formatting**: Follow PEP 8. Use f-strings for formatted strings.
- **Naming**: Use `PascalCase` for classes and `snake_case` for functions and variables.
- **Types**: Add type hints for function and method arguments.
- **Docstrings**: Provide clear docstrings for all public classes and methods.
- **Error Handling**: Use `try...except` blocks for I/O and queue access. Log errors to `sys.stderr`.
