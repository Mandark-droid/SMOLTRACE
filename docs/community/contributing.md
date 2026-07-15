# Contributing

Contributions to SMOLTRACE are welcome. Here's how to get started.

## Development Setup

```bash
git clone https://github.com/Mandark-droid/SMOLTRACE.git
cd SMOLTRACE
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
pip install -e .[dev]
```

## Running Tests

```bash
pytest
```

See the `tests/` directory for examples.

## Code Quality

SMOLTRACE uses `black`, `isort`, and `ruff` (all configured for a line length of 100):

```bash
black smoltrace tests     # Format (line length: 100)
isort smoltrace tests     # Sort imports (black profile)
ruff check .              # Lint
```

## Reporting Bugs & Requesting Features

Open an issue on the [GitHub Issues page](https://github.com/Mandark-droid/SMOLTRACE/issues) with a clear description.

## Pull Request Process

1. Fork the repository on GitHub.
2. Create a new branch for your feature or bug fix:

    ```bash
    git checkout -b feature/your-feature-name
    ```

3. Make your changes and add tests for them.
4. Run the linters and tests to ensure your code meets the project's standards.
5. Commit your changes with a clear, descriptive message.
6. Push to your branch and open a Pull Request to `main`.
7. Address any feedback from the maintainers' review.

## License

By contributing, you agree that your contributions will be licensed under the [Apache-2.0 License](https://github.com/Mandark-droid/SMOLTRACE/blob/main/LICENSE).

## Community

- [GitHub](https://github.com/Mandark-droid/SMOLTRACE)
- [GitHub Issues](https://github.com/Mandark-droid/SMOLTRACE/issues)
