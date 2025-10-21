# Contributing

We welcome contributions to `smoltrace`! Please see the guidelines below for how to contribute.

## Code of Conduct

This project adheres to the Contributor Covenant Code of Conduct. Please see the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) file for more details.

## How to Contribute

### Reporting Bugs

If you find a bug, please report it by opening an issue on our [GitHub Issues page](https://github.com/your-username/smoltrace/issues).

### Feature Requests

We welcome feature requests! Please open an issue on our [GitHub Issues page](https://github.com/your-username/smoltrace/issues) with a clear description of the feature you'd like to see.

### Contributing Code

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/your-username/smoltrace.git
    cd smoltrace
    ```
3.  **Create a new branch** for your feature or bug fix:
    ```bash
    git checkout -b feature/your-feature-name
    ```
4.  **Make your changes** and ensure they are well-tested.
5.  **Add tests** for your changes. See the `tests/` directory for examples.
6.  **Run linters and tests** to ensure your code meets our standards:
    ```bash
    # Example commands (adjust as needed based on project setup)
    ruff check .
    pytest
    ```
7.  **Commit your changes**:
    ```bash
    git commit -am "Add your descriptive commit message"
    ```
8.  **Push to the branch**:
    ```bash
    git push origin feature/your-feature-name
    ```
9.  **Open a Pull Request** on the original repository.

### Development Setup

To set up the development environment, follow these steps:

1.  Clone the repository and navigate to the project directory.
2.  Create a virtual environment (recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```
3.  Install the project in editable mode with development dependencies:
    ```bash
    pip install -e .[dev]
    ```

## Pull Request Process

1.  Ensure your fork is up-to-date with the main repository.
2.  Create a new branch for your changes.
3.  Submit a pull request with a clear title and description.
4.  Your pull request will be reviewed by the maintainers.
5.  Address any feedback from the review.

## Project Structure

(Optional: Add a brief overview of the project structure if it's complex.)

## License

By contributing to this project, you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE).
