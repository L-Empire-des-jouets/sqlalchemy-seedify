# Contributing to Alembic Seeder

Thank you for your interest in contributing to Alembic Seeder! We welcome contributions from the community and are grateful for any help you can provide.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please treat all contributors and users with respect and professionalism.

## How to Contribute

### Reporting Issues

1. **Check existing issues**: Before creating a new issue, please check if it already exists.
2. **Use issue templates**: When creating an issue, use the appropriate template.
3. **Provide details**: Include as much relevant information as possible:
   - Python version
   - SQLAlchemy/Alembic versions
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and stack traces

### Suggesting Features

1. **Open a discussion**: Start with a GitHub Discussion to gather feedback.
2. **Create a proposal**: If there's interest, create a detailed feature proposal.
3. **Consider implementation**: Be prepared to contribute code if possible.

### Contributing Code

#### Setup Development Environment

1. Fork the repository:
```bash
git clone https://github.com/L-Empire-des-jouets/sqlalchemy-seedifyr.git
cd sqlalchemy-seedify
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

#### Development Workflow

1. **Create a branch**: 
```bash
git checkout -b feature/your-feature-name
```

2. **Make changes**: Write your code following our style guide.

3. **Write tests**: Ensure all new code has appropriate test coverage.

4. **Run tests**:
```bash
pytest
pytest --cov=alembic_seeder  # With coverage
```

5. **Format code**:
```bash
black src tests
ruff check src tests --fix
```

6. **Type check**:
```bash
mypy src
```

7. **Commit changes**:
```bash
git add .
git commit -m "feat: add new feature"  # Use conventional commits
```

8. **Push and create PR**:
```bash
git push origin feature/your-feature-name
```

### Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks
- `perf:` Performance improvements

Examples:
```
feat: add support for parallel seeder execution
fix: resolve circular dependency detection issue
docs: update README with new CLI commands
```

### Code Style Guide

#### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting
- Use [Ruff](https://github.com/charliermarsh/ruff) for linting
- Maximum line length: 100 characters
- Use type hints for all functions

#### Documentation

- Write clear docstrings for all public functions/classes
- Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Brief description of function.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When invalid input provided
    """
    pass
```

### Testing Guidelines

#### Writing Tests

- Place tests in `tests/` directory
- Mirror the source code structure
- Use descriptive test names
- Test both success and failure cases
- Use fixtures for common setup

Example:
```python
import pytest
from alembic_seeder import BaseSeeder

class TestBaseSeeder:
    """Test suite for BaseSeeder."""
    
    @pytest.fixture
    def seeder(self):
        """Create a test seeder instance."""
        return TestSeeder()
    
    def test_seeder_initialization(self, seeder):
        """Test that seeder initializes correctly."""
        assert seeder.name == "TestSeeder"
    
    def test_seeder_execution_success(self, seeder):
        """Test successful seeder execution."""
        result = seeder.execute()
        assert result["status"] == "success"
```

#### Coverage Requirements

- Maintain at least 80% code coverage
- New features should have 90%+ coverage
- Critical paths should have 100% coverage

### Documentation

#### Code Documentation

- All public APIs must have docstrings
- Include examples in docstrings when helpful
- Keep documentation up-to-date with code changes

#### User Documentation

- Update README.md for new features
- Add examples to `examples/` directory
- Update CLI help text

### Pull Request Process

1. **Title**: Use a clear, descriptive title
2. **Description**: Fill out the PR template completely
3. **Tests**: Ensure all tests pass
4. **Documentation**: Update relevant documentation
5. **Review**: Address reviewer feedback promptly
6. **Squash**: We squash commits on merge

### Review Process

PRs require:
- At least one approving review
- All CI checks passing
- No unresolved conversations
- Up-to-date with main branch

## Development Tips

### Running Specific Tests

```bash
# Run specific test file
pytest tests/test_base_seeder.py

# Run specific test
pytest tests/test_base_seeder.py::TestBaseSeeder::test_initialization

# Run with verbose output
pytest -v

# Run with print statements
pytest -s
```

### Debugging

```python
# Use breakpoints
import pdb; pdb.set_trace()

# Or with ipdb (if installed)
import ipdb; ipdb.set_trace()
```

### Performance Testing

```python
# Profile your code
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# Your code here
profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumulative')
stats.print_stats()
```

## Release Process

1. **Version Bump**: Update version in `pyproject.toml`
2. **Changelog**: Update CHANGELOG.md
3. **Tag**: Create git tag with version
4. **Release**: GitHub Actions handles PyPI deployment

## Getting Help

- 💬 [GitHub Discussions](https://github.com/sqlalchemy-seedify/sqlalchemy-seedify/discussions)
- 🐛 [Issue Tracker](https://github.com/sqlalchemy-seedify/sqlalchemy-seedify/issues)
- 📧 Email: contribute@sqlalchemy-seedify.dev

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- GitHub contributors page
- Release notes

Thank you for contributing to Alembic Seeder! 🌱