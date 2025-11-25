# Contributing to Marketplace Deal Scout

Thank you for your interest in contributing to Marketplace Deal Scout!

## Development Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (macOS/Linux) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Install in development mode: `pip install -e .`
6. Copy `.env.example` to `.env` and add your API key

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html

# Run property-based tests
pytest tests/property/ -v
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to all public functions and classes
- Keep functions focused and single-purpose

## Commit Guidelines

- Use clear, descriptive commit messages
- Reference issue numbers when applicable
- Keep commits atomic and focused

## Privacy and Security

- Never commit API keys, credentials, or personal data
- Use `.env` files for sensitive configuration
- Test with dummy data when possible
- Respect Facebook's Terms of Service

## Legal Compliance

This tool is for **personal use only**. Contributors must:
- Comply with Facebook's Terms of Service
- Respect rate limits and robots.txt
- Not use the tool for commercial purposes
- Implement ethical scraping practices

## Questions?

Open an issue for discussion before starting major changes.
