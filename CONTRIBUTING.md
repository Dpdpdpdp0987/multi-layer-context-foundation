# Contributing to Multi-Layer Context Foundation

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/Dpdpdpdp0987/multi-layer-context-foundation/issues)
2. If not, create a new issue with:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Relevant logs or screenshots

### Suggesting Features

1. Check [existing feature requests](https://github.com/Dpdpdpdp0987/multi-layer-context-foundation/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
2. Create a new issue with:
   - Clear description of the feature
   - Use case and motivation
   - Proposed implementation (if applicable)
   - Potential alternatives

### Pull Requests

1. **Fork the repository**

```bash
git clone https://github.com/YOUR_USERNAME/multi-layer-context-foundation.git
cd multi-layer-context-foundation
```

2. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

3. **Set up development environment**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
```

4. **Make your changes**

- Follow the code style guidelines (below)
- Add tests for new functionality
- Update documentation as needed

5. **Run tests and linters**

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest --cov=mlcf tests/

# Run linters
black mlcf/ tests/
flake8 mlcf/ tests/
mypy mlcf/
```

6. **Commit your changes**

```bash
git add .
git commit -m "feat: add amazing feature"
```

Commit message format:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `test:` adding or updating tests
- `refactor:` code refactoring
- `perf:` performance improvements
- `chore:` maintenance tasks

7. **Push and create PR**

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots (if UI changes)
- Test results

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting (line length: 88)
- Use type hints where possible
- Write docstrings for all public functions/classes (Google style)

### Example

```python
from typing import List, Optional

def retrieve_context(
    query: str,
    max_results: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant context based on query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        filters: Optional metadata filters
        
    Returns:
        List of context items with scores
        
    Raises:
        ValueError: If query is empty
    """
    if not query:
        raise ValueError("Query cannot be empty")
    
    # Implementation
    return results
```

### Testing Guidelines

- Write tests for all new features
- Maintain >80% code coverage
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

```python
def test_context_retrieval_with_filters():
    """Test that filters correctly narrow down results."""
    # Arrange
    cm = ContextManager()
    cm.store("Python doc", metadata={"type": "code"})
    cm.store("Meeting note", metadata={"type": "note"})
    
    # Act
    results = cm.retrieve(
        query="document",
        filters={"type": "code"}
    )
    
    # Assert
    assert len(results) == 1
    assert results[0]["metadata"]["type"] == "code"
```

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all public APIs
- Update relevant docs in `docs/` directory
- Include code examples where helpful

## Development Setup

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git

### Setup Steps

1. **Clone and install**

```bash
git clone <your-fork>
cd multi-layer-context-foundation
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

2. **Start services**

```bash
docker-compose up -d
```

3. **Run tests**

```bash
pytest tests/
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality:

```bash
pre-commit install
```

Hooks will run automatically on `git commit`.

## Release Process

1. Update version in `mlcf/__init__.py`
2. Update CHANGELOG.md
3. Create release tag: `git tag v0.x.0`
4. Push tag: `git push origin v0.x.0`
5. Create GitHub release

## Questions?

Feel free to:
- Open an issue for discussion
- Join our discussions
- Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Multi-Layer Context Foundation! 🚀