import ast
import astor
import pydocstyle
import re
import os
import tempfile
import sys
from typing import Dict, List, Tuple, Union, Optional
import json

class DocstringGenerator:
    SUPPORTED_STYLES = ['google', 'numpy', 'reST']
    
    def __init__(self, style: str = 'google'):
        if style.lower() not in self.SUPPORTED_STYLES:
            raise ValueError(f"Unsupported style: {style}. Choose from {self.SUPPORTED_STYLES}")
        self.style = style.lower()
    
    def extract_function_info(self, node: ast.FunctionDef) -> Dict:
        """Extract parameters, returns, raises, and yields information from AST node"""
        args = []
        for arg in node.args.args:
            arg_type = ast.unparse(arg.annotation) if arg.annotation else "Any"
            args.append((arg.arg, arg_type))
        
        # Handle *args and **kwargs
        if node.args.vararg:
            args.append((f"*{node.args.vararg.arg}", "Any"))
        if node.args.kwarg:
            args.append((f"**{node.args.kwarg.arg}", "Any"))
        
        # Check for return annotation
        returns = ast.unparse(node.returns) if node.returns else "None"
        
        # Detect raises and yields
        raises = set()
        yields = False
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Raise) and stmt.exc:
                exc_type = ast.unparse(stmt.exc)
                raises.add(re.sub(r'\(.*?\)', '', exc_type))  # Remove parentheses and content
            if isinstance(stmt, (ast.Yield, ast.YieldFrom)):
                yields = True
        
        return {
            'name': node.name,
            'args': args,
            'returns': returns,
            'raises': list(raises),
            'yields': yields
        }
    
    def extract_class_info(self, node: ast.ClassDef) -> Dict:
        """Extract class attributes from AST node"""
        attributes = []
        methods = []
        
        # Find __init__ method to extract instance attributes
        init_method = None
        for body_item in node.body:
            if isinstance(body_item, ast.FunctionDef) and body_item.name == '__init__':
                init_method = body_item
                break
        
        if init_method:
            for stmt in ast.walk(init_method):
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                            if target.value.id == 'self':
                                attr_type = "Any"
                                if hasattr(stmt, 'annotation') and stmt.annotation:
                                    attr_type = ast.unparse(stmt.annotation)
                                attributes.append((target.attr, attr_type))
        
        # Extract public methods
        for body_item in node.body:
            if isinstance(body_item, ast.FunctionDef) and not body_item.name.startswith('_'):
                methods.append(body_item.name)
        
        return {
            'name': node.name,
            'attributes': attributes,
            'methods': methods
        }
    
    def generate_docstring(self, node: Union[ast.FunctionDef, ast.ClassDef]) -> str:
        """Generate docstring based on node type and selected style"""
        if isinstance(node, ast.FunctionDef):
            info = self.extract_function_info(node)
            return self._format_function_docstring(info)
        elif isinstance(node, ast.ClassDef):
            info = self.extract_class_info(node)
            return self._format_class_docstring(info)
        return ""
    
    def _format_function_docstring(self, info: Dict) -> str:
        """Format function docstring according to selected style"""
        short_desc = f"{info['name']} function."
        long_desc = ""
        
        if self.style == 'google':
            sections = [f"{short_desc}\n"]
            if long_desc:
                sections.append(f"{long_desc}\n")
            
            if info['args']:
                sections.append("Args:")
                for arg_name, arg_type in info['args']:
                    sections.append(f"    {arg_name} ({arg_type}): TODO: describe argument")
                sections.append("")
            
            if info['yields']:
                sections.append("Yields:")
                sections.append(f"    {info['returns']}: TODO: describe yielded value\n")
            elif info['returns'] != "None":
                sections.append("Returns:")
                sections.append(f"    {info['returns']}: TODO: describe return value\n")
            
            if info['raises']:
                sections.append("Raises:")
                for exc in info['raises']:
                    sections.append(f"    {exc}: TODO: describe when this exception is raised")
            
            return "\n".join(sections)
        
        elif self.style == 'numpy':
            sections = [f"{short_desc}\n"]
            if long_desc:
                sections.append(f"{long_desc}\n")
            
            if info['args']:
                sections.append("Parameters")
                sections.append("----------")
                for arg_name, arg_type in info['args']:
                    sections.append(f"{arg_name} : {arg_type}")
                    sections.append("    TODO: describe parameter")
                sections.append("")
            
            if info['yields']:
                sections.append("Yields")
                sections.append("------")
                sections.append(f"{info['returns']}")
                sections.append("    TODO: describe yielded value\n")
            elif info['returns'] != "None":
                sections.append("Returns")
                sections.append("-------")
                sections.append(f"{info['returns']}")
                sections.append("    TODO: describe return value\n")
            
            if info['raises']:
                sections.append("Raises")
                sections.append("------")
                for exc in info['raises']:
                    sections.append(f"{exc}")
                    sections.append("    TODO: describe exception\n")
            
            return "\n".join(sections)
        
        # reST style
        sections = [f"{short_desc}\n"]
        if long_desc:
            sections.append(f"{long_desc}\n")
        
        if info['args']:
            sections.append(":param " + ", :param ".join([arg[0] for arg in info['args']]) + ":")
            for arg_name, arg_type in info['args']:
                sections.append(f":type {arg_name}: {arg_type}")
        
        if info['yields']:
            sections.append(f":yields: {info['returns']} - TODO: describe yielded value")
        elif info['returns'] != "None":
            sections.append(f":return: TODO: describe return value")
            sections.append(f":rtype: {info['returns']}")
        
        for exc in info['raises']:
            sections.append(f":raises {exc}: TODO: describe exception")
        
        return "\n".join(sections)
    
    def _format_class_docstring(self, info: Dict) -> str:
        """Format class docstring according to selected style"""
        short_desc = f"{info['name']} class."
        long_desc = ""
        
        if self.style == 'google':
            sections = [f"{short_desc}\n"]
            if long_desc:
                sections.append(f"{long_desc}\n")
            
            if info['attributes']:
                sections.append("Attributes:")
                for attr_name, attr_type in info['attributes']:
                    sections.append(f"    {attr_name} ({attr_type}): TODO: describe attribute")
                sections.append("")
            
            if info['methods']:
                sections.append("Methods:")
                for method in info['methods']:
                    sections.append(f"    {method}(): TODO: describe method")
            
            return "\n".join(sections)
        
        elif self.style == 'numpy':
            sections = [f"{short_desc}\n"]
            if long_desc:
                sections.append(f"{long_desc}\n")
            
            if info['attributes']:
                sections.append("Attributes")
                sections.append("----------")
                for attr_name, attr_type in info['attributes']:
                    sections.append(f"{attr_name} : {attr_type}")
                    sections.append("    TODO: describe attribute")
                sections.append("")
            
            if info['methods']:
                sections.append("Methods")
                sections.append("-------")
                for method in info['methods']:
                    sections.append(f"{method}()")
                    sections.append("    TODO: describe method")
            
            return "\n".join(sections)
        
        # reST style
        sections = [f"{short_desc}\n"]
        if long_desc:
            sections.append(f"{long_desc}\n")
        
        if info['attributes']:
            sections.append("Attributes:")
            for attr_name, attr_type in info['attributes']:
                sections.append(f":ivar {attr_name}: TODO: describe attribute")
                sections.append(f":vartype {attr_name}: {attr_type}")
        
        return "\n".join(sections)

class DocstringValidator:
    @staticmethod
    def validate_file(file_path: str) -> List[Dict]:
        """Validate docstrings against PEP 257 using pydocstyle"""
        results = []
        for error in pydocstyle.check([file_path]):
            results.append({
                'line': error.line,
                'code': error.code,
                'message': error.message,
                'source': error.source
            })
        return results
    
    @staticmethod
    def analyze_code_quality(file_content: str) -> Dict:
        """Analyze code quality including coverage and compliance metrics"""
        tree = ast.parse(file_content)
        
        # Count functions and classes
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node)
            elif isinstance(node, ast.ClassDef):
                classes.append(node)
        
        total_functions = len(functions)
        total_classes = len(classes)
        total_items = total_functions + total_classes
        
        # Get documented items
        documented_functions = 0
        documented_classes = 0
        undocumented_functions = []
        undocumented_classes = []
        
        for node in functions:
            docstring = ast.get_docstring(node)
            if docstring and len(docstring.strip()) > 0:
                documented_functions += 1
            else:
                undocumented_functions.append(node.name)
        
        for node in classes:
            docstring = ast.get_docstring(node)
            if docstring and len(docstring.strip()) > 0:
                documented_classes += 1
            else:
                undocumented_classes.append(node.name)
        
        documented_items = documented_functions + documented_classes
        undocumented_items = (total_functions - documented_functions) + (total_classes - documented_classes)
        coverage_percentage = round(documented_items / total_items * 100, 1) if total_items > 0 else 0
        
        # Get compliance data - WINDOWS-SAFE TEMP FILE HANDLING
        violations = []
        fd, tmp_path = tempfile.mkstemp(suffix='.py', text=True)
        try:
            # Write content with explicit UTF-8 encoding
            with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                tmp.write(file_content)
            # File is CLOSED before validation (critical for Windows)
            violations = list(pydocstyle.check([tmp_path]))
        except Exception as e:
            print(f"Warning: Validation error: {e}", file=sys.stderr)
        finally:
            # Always clean up temp file - suppress errors if already gone
            try:
                os.unlink(tmp_path)
            except (OSError, FileNotFoundError):
                pass
        
        violation_count = len(violations)
        
        # Calculate compliance percentage based on documented items with violations
        # Only count violations in documented items (items with docstrings)
        items_with_violations = set()
        for violation in violations:
            # Track which line has violations
            items_with_violations.add(violation.line)
        
        # Calculate compliance: (documented_items - items_with_violations) / documented_items
        # If no documented items, compliance is 100% (nothing to validate)
        if documented_items == 0:
            compliance_percentage = 100.0
        elif violation_count == 0:
            compliance_percentage = 100.0
        else:
            # Estimate items with violations (each violation roughly corresponds to one item)
            # This is approximate but works for most cases
            affected_items = min(len(items_with_violations), documented_items)
            compliant_items = documented_items - affected_items
            compliance_percentage = round((compliant_items / documented_items) * 100, 1)
            # Ensure non-negative
            compliance_percentage = max(0.0, compliance_percentage)
        
        
        return {
            'total_functions': total_functions,
            'total_classes': total_classes,
            'documented_items': documented_items,
            'undocumented_items': undocumented_items,
            'documented_functions': documented_functions,
            'undocumented_functions': undocumented_functions,
            'documented_classes': documented_classes,
            'undocumented_classes': undocumented_classes,
            'total_items': total_items,
            'coverage_percentage': coverage_percentage,
            'compliance_percentage': compliance_percentage,
            'violation_count': violation_count,
            'violations': violations
        }

class CodeInstrumentor:
    @staticmethod
    def add_docstrings(file_content: str, style: str = 'google') -> str:
        """Add docstrings to all functions and classes in the code"""
        tree = ast.parse(file_content)
        generator = DocstringGenerator(style)
        
        # Transform AST to add docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                # Skip if already has a substantial docstring
                existing_doc = ast.get_docstring(node)
                if existing_doc and len(existing_doc.strip()) > 20:
                    continue
                
                # Generate and add new docstring
                docstring = generator.generate_docstring(node)
                if docstring:
                    # Create AST node for docstring
                    doc_node = ast.Expr(value=ast.Constant(value=docstring.strip()))
                    node.body.insert(0, doc_node)
        
        return astor.to_source(tree)
    
    @staticmethod
    def process_directory(directory_path: str, style: str = 'google') -> Dict:
        """Process all Python files in a directory"""
        results = {}
        total_functions = 0
        total_classes = 0
        total_documented = 0
        total_undocumented = 0
        total_items = 0
        total_violations = 0
        
        original_summary = {
            'total_functions': 0,
            'total_classes': 0,
            'documented_items': 0,
            'undocumented_items': 0,
            'total_items': 0,
            'coverage_percentage': 0,
            'compliance_percentage': 0,
            'violation_count': 0
        }
        
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    # FIXED: Added encoding='utf-8' when reading files
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Analyze original code first
                    original_quality = DocstringValidator.analyze_code_quality(content)
                    
                    # Add docstrings
                    instrumented_code = CodeInstrumentor.add_docstrings(content, style)
                    
                    # Analyze instrumented code - WINDOWS-SAFE TEMP FILE HANDLING
                    fd, tmp_path = tempfile.mkstemp(suffix='.py', text=True)
                    try:
                        with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                            tmp.write(instrumented_code)
                        instrumented_quality = DocstringValidator.analyze_code_quality(instrumented_code)
                        validation_results = DocstringValidator.validate_file(tmp_path)
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except (OSError, FileNotFoundError):
                            pass
                    
                    # Update totals for original code
                    original_summary['total_functions'] += original_quality['total_functions']
                    original_summary['total_classes'] += original_quality['total_classes']
                    original_summary['documented_items'] += original_quality['documented_items']
                    original_summary['undocumented_items'] += original_quality['undocumented_items']
                    original_summary['total_items'] += original_quality['total_items']
                    original_summary['violation_count'] += original_quality['violation_count']
                    
                    # Update totals for instrumented code
                    total_functions += instrumented_quality['total_functions']
                    total_classes += instrumented_quality['total_classes']
                    total_documented += instrumented_quality['documented_items']
                    total_undocumented += instrumented_quality['undocumented_items']
                    total_items += instrumented_quality['total_items']
                    total_violations += instrumented_quality['violation_count']
                    
                    # Collect results
                    results[file_path] = {
                        'original_code': content,
                        'instrumented_code': instrumented_code,
                        'original_quality': original_quality,
                        'instrumented_quality': instrumented_quality,
                        'validation': validation_results,
                        'original_violations': original_quality['violations']
                    }
        
        # Calculate overall metrics for original code
        if original_summary['total_items'] > 0:
            original_summary['coverage_percentage'] = round(
                original_summary['documented_items'] / original_summary['total_items'] * 100, 1
            )
            original_summary['compliance_percentage'] = round(
                (original_summary['total_items'] - original_summary['violation_count']) / 
                original_summary['total_items'] * 100, 1
            )
        
        # Calculate overall metrics for instrumented code
        overall_coverage = round(total_documented / total_items * 100, 1) if total_items > 0 else 0
        overall_compliance = round((total_items - total_violations) / total_items * 100, 1) if total_items > 0 else 0
        
        return {
            'file_results': results,
            'original_summary': original_summary,
            'instrumented_summary': {
                'total_functions': total_functions,
                'total_classes': total_classes,
                'documented_items': total_documented,
                'undocumented_items': total_undocumented,
                'total_items': total_items,
                'coverage_percentage': overall_coverage,
                'compliance_percentage': overall_compliance,
                'violation_count': total_violations
            }
        }

# Utility functions
def get_file_content(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:  # FIXED: Added encoding
        return f.read()

def save_file(file_path: str, content: str):
    with open(file_path, 'w', encoding='utf-8') as f:  # FIXED: Added encoding
        f.write(content)

def generate_before_coverage_report(quality_report: Dict) -> str:
    """Generate a formatted coverage report for original code"""
    report = f"""
Documentation Coverage Report (Before Instrumentation)
=====================================================

Functions: {quality_report['total_functions']}
  Documented: {quality_report['documented_functions']}
  Undocumented: {quality_report['total_functions'] - quality_report['documented_functions']}
  Undocumented functions: {', '.join(quality_report['undocumented_functions']) if quality_report['undocumented_functions'] else 'None'}

Classes: {quality_report['total_classes']}
  Documented: {quality_report['documented_classes']}
  Undocumented: {quality_report['total_classes'] - quality_report['documented_classes']}
  Undocumented classes: {', '.join(quality_report['undocumented_classes']) if quality_report['undocumented_classes'] else 'None'}

Coverage %: {quality_report['coverage_percentage']}
PEP-257 Compliance %: {quality_report['compliance_percentage']}
PEP-257 Violations: {quality_report['violation_count']}
"""
    return report

def generate_after_coverage_report(quality_report: Dict) -> str:
    """Generate a formatted coverage report for instrumented code"""
    report = f"""
Documentation Coverage Report (After Instrumentation)
====================================================

Functions: {quality_report['total_functions']}
  Documented: {quality_report['documented_items'] - (quality_report['total_classes'] - quality_report['documented_classes'])}
  Undocumented: {quality_report['undocumented_items'] - (quality_report['total_classes'] - quality_report['documented_classes'])}

Classes: {quality_report['total_classes']}
  Documented: {quality_report['documented_classes']}
  Undocumented: {quality_report['total_classes'] - quality_report['documented_classes']}

Coverage %: {quality_report['coverage_percentage']}
PEP-257 Compliance %: {quality_report['compliance_percentage']}
PEP-257 Violations: {quality_report['violation_count']}
"""
    return report

def generate_compliance_report(violations: List, title: str = "PEP-257 Compliance Report") -> str:
    """Generate a formatted compliance report"""
    if not violations:
        return f"{title}\n{'='*len(title)}\n\n✅ No compliance issues found!\n"
    
    report = f"{title}\n{'='*len(title)}\n\n"
    report += f"Found {len(violations)} compliance issues:\n\n"
    
    for i, issue in enumerate(violations, 1):
        report += f"Issue #{i}:\n"
        report += f"  Line: {issue['line']}\n"
        report += f"  Code: {issue['code']}\n"
        report += f"  Message: {issue['message']}\n"
        if 'source' in issue:
            report += f"  Source: {issue['source']}\n"
        report += "\n"
    
    return report