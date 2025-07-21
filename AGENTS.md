# AGENTS.md

This document outlines the standards and best practices for AI-driven Python development in this repository.

## 1. Project & Environment Setup

This is a simple Python project without external dependencies. A virtual environment is recommended but not strictly required.

- **To create a virtual environment:**
  ```bash
  python -m venv venv
  source venv/bin/activate
  ```

## 2. Build & Test Commands

- **Run Application:**
  ```bash
  python scoreboard.py
  ```
- **Run All Tests:**
  ```bash
  python -m unittest discover
  ```
- **Run Specific Test File:**
  ```bash
  python -m unittest test_scoreboard.py
  ```
- **Run Specific Test Case:**
  ```bash
  python -m unittest test_scoreboard.TestScoreboard.test_single_match
  ```

## 3. Code Style (PEP 8 Aligned)

- **Imports:** Use standard library imports. Keep them organized at the top of the file.
- **Typing:** Use type hints for function signatures (`def my_function(param: str) -> int:`).
- **Naming Conventions:**
  - `snake_case` for variables and functions.
  - `PascalCase` for classes.
  - `UPPER_SNAKE_CASE` for constants.
- **Error Handling:** Use `try...except` blocks for operations that can fail, such as file I/O. Provide informative error messages.
- **Docstrings:** All public modules, classes, and functions should have a docstring explaining their purpose.
