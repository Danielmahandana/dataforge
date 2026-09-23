# Contributing to Darkroom DataForge

Thank you for contributing to the Wits–merSETA Darkroom data engineering platform.

## 1. Development Principles

- **No Silent Mutations**: Never silently alter or drop source data. Always store both raw and normalized values.
- **Strict Provenance**: Every new extractor must populate `ProvenanceRecord` with source document, page, method, and confidence score.
- **Type Annotations**: All function signatures must include Python type hints.
- **Hermetic Testing**: All automated tests must use synthetic fixtures (via `demo/sample_generator.py`) and must not rely on proprietary or external network services.

---

## 2. Setting Up Development Environment

```bash
# Clone and enter directory
cd "Darkroom DataForge"

# Initialize virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

---

## 3. Running Tests & Quality Verification

Before committing any changes, ensure all tests pass:

```bash
pytest tests/ -v
```

To run a specific test module:
```bash
pytest tests/test_extractors.py -v
```

---

## 4. Code Style & Standards

- Adhere to **PEP 8** standards.
- Use `snake_case` for variables, column names, and module files.
- Use `PascalCase` for classes and Pydantic models.
- Avoid broad `except:` clauses; catch explicit exceptions or log detailed tracebacks.
