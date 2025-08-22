# Contributing to Intugle

First off, thank you for considering contributing to Intugle! It's people like you that make Intugle such a great tool.

Intugle is an open source project and we love to receive contributions from our community — you!

There are many ways to contribute, from writing tutorials or blog posts, improving the documentation, submitting bug reports and feature requests or writing code which can be incorporated into Intugle itself.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue on our [GitHub repository](https://github.com/Intugle/intugle/issues). Please include a clear and concise description of the bug, as well as steps to reproduce it.

### Submitting Feature Requests

If you have an idea for a new feature, please open an issue on our [GitHub repository](https://github.com/Intugle/intugle/issues). Please include a clear and concise description of the feature, as well as a justification for why it would be a good addition to the project.

### Writing Code

If you want to contribute code to the project, please follow the steps below.

## Getting Started

1.  Fork the repository on GitHub.
2.  Clone your fork locally:

    ```bash
    git clone https://github.com/your-username/intugle.git
    ```

3.  Set up a virtual environment and install the dependencies:

    ```bash
    cd intugle
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

## Development Workflow

1.  Create a new branch for your changes:

    ```bash
    git checkout -b my-new-feature
    ```

2.  Make your changes to the code.

3.  Run the tests to make sure that your changes don't break anything:

    ```bash
    pytest
    ```

4.  Commit your changes:

    ```bash
    git commit -m "Add some feature"
    ```

5.  Push your changes to your fork:

    ```bash
    git push origin my-new-feature
    ```

6.  Open a pull request on the [Intugle repository](https://github.com/Intugle/intugle/pulls).

## Coding Style

This project uses `ruff` for linting and code formatting. Before submitting a pull request, please make sure that your code conforms to the project's coding style by running the following command:

```bash
ruff check .
```

## Testing

This project uses `pytest` for testing. To run the tests, use the following command:

```bash
pytest
```

## Submitting a Pull Request

When you submit a pull request, please include the following:

*   A clear and concise title for the pull request.
*   A clear and concise description of the changes that you made.
*   A link to the issue that the pull request addresses (if applicable).

## Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.
