# DocuGenius

A comprehensive docstring generator and validator for Python code.

## Features

- **Automatic Docstring Generation**: Generate docstrings for functions and classes in multiple styles
- **PEP-257 Compliance**: Validate docstrings against PEP-257 standards
- **Multiple Styles**: Support for Google, NumPy, and reStructuredText docstring formats
- **Coverage Reporting**: Measure docstring coverage and compliance metrics
- **CLI Tools**: Command-line interface for batch processing and reporting

## Installation

### From PyPI (when published)

```bash
pip install docugenius
```

### From source (development mode)

Clone the repository and install in editable mode:

```bash
git clone <your-fork-or-repo-url>
cd M2  # project root
pip install -e ".[dev,ui]"
```

This installs:

- **Core library** (`m2_core.py`)
- **CLI tool** (`docugenius` entry point)
- **Streamlit UI** (`streamlit_app.py`)
- **Developer tooling** (pytest, black, mypy, etc.)

## Quick Start

### Using the CLI

The `docugenius` CLI validates docstring coverage and PEP‑257 compliance for one or more Python files.

```bash
# Basic validation
docugenius myfile.py

# Multiple files
docugenius src/module_a.py src/module_b.py

# Custom thresholds
docugenius myfile.py --min-coverage 90 --min-compliance 85

# Generate a JSON report
docugenius myfile.py another_file.py --output report.json
```

**CLI options:**

- **`files`** (positional): One or more `.py` files to analyse.
- **`--min-coverage`**: Minimum docstring coverage percentage required
  (default from `[tool.docugenius].min_coverage`).
- **`--min-compliance`**: Minimum PEP‑257 compliance percentage required
  (default from `[tool.docugenius].min_compliance`).
- **`--output`**: Optional path to a JSON report file summarising results.

Exit codes:

- **0** – all analysed files meet the thresholds.
- **1** – one or more files fail the thresholds or an error occurs.

### Using as a Library

```python
from docugenius import DocstringGenerator, DocstringValidator
from m2_core import CodeInstrumentor

source_code = open("myfile.py", encoding="utf-8").read()

# Generate/inject docstrings for functions & classes in a file
instrumented = CodeInstrumentor.add_docstrings(source_code, style="google")

# Validate quality before/after as needed
quality_before = DocstringValidator.analyze_code_quality(source_code)
quality_after = DocstringValidator.analyze_code_quality(instrumented)

print(f"Coverage before: {quality_before['coverage_percentage']}%")
print(f"Coverage after:  {quality_after['coverage_percentage']}%")
print(f"Compliance after: {quality_after['compliance_percentage']}%")
```

## Configuration

Configure DocuGenius using `pyproject.toml` in your project root:

```toml
-tool.docugenius]
style = "google"           # google, numpy, or reST
min_coverage = 90.0        # Minimum coverage percentage
min_compliance = 85.0      # Minimum compliance percentage
exclude_patterns = ["tests/**", "venv/**"]
```
**Where configuration is used:**

- The **CLI** (`docugenius_cli.py`) reads `[tool.docugenius]` for defaults.
- You can still override thresholds via CLI flags when needed.

## Example Workflows

### 1. Enforce docstring quality in CI

1. Add a `pyproject.toml` with sensible thresholds:

```toml
[tool.docugenius]
style = "google"
min_coverage = 80.0
min_compliance = 85.0
exclude_patterns = ["tests/**", "venv/**", "build/**"]
```

2. In your CI pipeline (GitHub Actions, GitLab CI, etc.), run:

```bash
pip install docugenius
docugenius src/**/*.py
```

If coverage or compliance drop below the configured thresholds, the job will fail.

### 2. Improve documentation for a legacy project

1. Collect your code into a directory (for example, `legacy_src/`).
2. Use the **Streamlit UI** to explore before/after metrics and generate improved code:

```bash
pip install "docugenius[ui]"
streamlit run streamlit_app.py
```

3. Upload either:

- A **single `.py` file** to see detailed metrics and a side‑by‑side code comparison.
- A **ZIP archive** of multiple `.py` files to get project‑wide metrics and per‑file views.

4. Download the instrumented code and reports from the UI and commit them back into your project.

### 3. Integrate into a custom tool

You can integrate the analysis and instrumentation into your own tooling:

```python
from m2_core import CodeInstrumentor, DocstringValidator

def ensure_docs(path: str, style: str = "google") -> None:
    content = open(path, encoding="utf-8").read()
    quality_before = DocstringValidator.analyze_code_quality(content)
    instrumented = CodeInstrumentor.add_docstrings(content, style=style)
    quality_after = DocstringValidator.analyze_code_quality(instrumented)
    print("Before:", quality_before["coverage_percentage"])
    print("After:", quality_after["coverage_percentage"])
```

## Development & Contribution

### Setting up a dev environment

```bash
git clone <your-fork-or-repo-url>
cd M2
pip install -e ".[dev,ui]"
```

### Running tests

The test suite (configured via `pytest.ini`) lives under `tests/`:

```bash
pytest
```

This includes edge‑case tests for:

- empty files
- nested and decorated functions
- classes without methods
- already documented functions
- syntax‑error inputs

### Contribution guidelines

- **Coding style**: Follow PEP 8 and ensure docstrings are PEP‑257 compliant.
- **Testing**: Add or update tests in `tests/` for any new behaviour or bug fix.
- **Commits/PRs**:
  - Keep changes focused and well‑described.
  - Include a short summary of the problem and the solution.
  - Run `pytest` locally before opening a pull request.

## License

MIT

## Support

For issues, questions, or contributions, please visit the project repository and open an issue or pull request.
