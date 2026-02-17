import ast

import pytest

from m2_core import CodeInstrumentor, DocstringValidator


def _get_function_and_class_nodes(source: str):
    """Helper to parse source and return (functions, classes)."""
    tree = ast.parse(source)
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    return functions, classes


def test_empty_python_file_analysis():
    """Empty Python files should not crash and should report zero items."""
    result = DocstringValidator.analyze_code_quality("")

    assert result["total_functions"] == 0
    assert result["total_classes"] == 0
    assert result["total_items"] == 0
    # With no items, coverage is defined as 0 and compliance as 100
    assert result["coverage_percentage"] == 0
    assert result["compliance_percentage"] == 100.0


def test_empty_python_file_instrumentation_adds_module_docstring():
    """Instrumenting an empty file should at least add a module docstring."""
    instrumented = CodeInstrumentor.add_docstrings("", style="google")

    assert '"""Module for processing Python files."""' in instrumented
    # Resulting code should still be valid Python
    ast.parse(instrumented)


def test_nested_functions_only_top_level_get_docstrings():
    """Nested functions should not be treated as top-level API."""
    source = """
def outer(x):
    def inner(y):
        return x + y
    return inner(x)
"""
    instrumented = CodeInstrumentor.add_docstrings(source, style="google")
    functions, _ = _get_function_and_class_nodes(instrumented)

    outer = next(f for f in functions if f.name == "outer")
    inner = next(f for f in functions if f.name == "inner")

    assert ast.get_docstring(outer) is not None
    # Inner function is currently not documented by the instrumentor
    assert ast.get_docstring(inner) is None


def test_decorated_functions_are_instrumented():
    """Decorated top-level functions should still receive docstrings."""
    source = """
def decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@decorator
def decorated(a, b):
    return a + b
"""
    instrumented = CodeInstrumentor.add_docstrings(source, style="google")
    functions, _ = _get_function_and_class_nodes(instrumented)

    decorated = next(f for f in functions if f.name == "decorated")
    assert ast.get_docstring(decorated) is not None


def test_class_without_methods_is_handled():
    """Classes without methods should be counted and instrumented safely."""
    source = """
class Empty:
    pass
"""
    # Original quality: one undocumented class
    original_quality = DocstringValidator.analyze_code_quality(source)
    assert original_quality["total_classes"] == 1
    assert original_quality["documented_classes"] == 0

    instrumented = CodeInstrumentor.add_docstrings(source, style="google")
    _, classes = _get_function_and_class_nodes(instrumented)
    empty_class = next(c for c in classes if c.name == "Empty")

    assert ast.get_docstring(empty_class) is not None


def test_already_documented_functions_are_not_overwritten():
    """Existing substantial docstrings should be preserved."""
    source = '''
def documented(x, y):
    """This is an existing, meaningful docstring that should stay."""
    return x * y
'''
    instrumented = CodeInstrumentor.add_docstrings(source, style="google")
    functions, _ = _get_function_and_class_nodes(instrumented)

    documented = next(f for f in functions if f.name == "documented")
    doc = ast.get_docstring(documented)
    assert "existing, meaningful docstring" in doc


def test_syntax_error_input_raises_syntaxerror():
    """Invalid Python input should raise SyntaxError during analysis."""
    bad_source = "def broken(:\n    pass"

    with pytest.raises(SyntaxError):
        DocstringValidator.analyze_code_quality(bad_source)


def test_instrumented_code_has_zero_pydocstyle_violations(tmp_path):
    """Instrumented code should be PEP-257 clean (no violations)."""
    source = """
def add(x, y):
    return x + y


class Foo:
    def method(self, a):
        return a
"""
    instrumented = CodeInstrumentor.add_docstrings(source, style="google")

    # Write to a tempfile and validate via pydocstyle
    file_path = tmp_path / "sample.py"
    file_path.write_text(instrumented, encoding="utf-8")

    violations = DocstringValidator.validate_file(str(file_path))
    assert violations == [], f"Expected 0 violations, got: {violations}"

