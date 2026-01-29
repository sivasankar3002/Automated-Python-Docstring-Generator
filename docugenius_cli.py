#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from m2_core import DocstringValidator

# Config loader (works with Python 3.11+)
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Python <3.11
    except ImportError:
        tomllib = None

def load_config():
    """Load configuration from pyproject.toml"""
    config = {
        "min_coverage": 90.0,
        "min_compliance": 85.0,
        "style": "google"
    }
    
    try:
        pyproject_path = Path("pyproject.toml")
        if pyproject_path.exists() and tomllib:
            # Read as binary to avoid encoding issues
            with open(pyproject_path, "rb") as f:
                pyproject = tomllib.load(f)
            tool_config = pyproject.get("tool", {}).get("docugenius", {})
            config.update(tool_config)
            print(f"✓ Loaded config from pyproject.toml")
    except Exception as e:
        # Don't crash - just use defaults with warning
        print(f"⚠️ Warning: Could not load pyproject.toml config: {e}", file=sys.stderr)
    
    return config

def main():
    config = load_config()
    
    parser = argparse.ArgumentParser(description="DocuGenius Validator (Milestone 3)")
    parser.add_argument("files", nargs="+", help="Python files to validate")
    parser.add_argument("--min-coverage", type=float, 
                       default=config["min_coverage"],
                       help=f"Coverage threshold (default: {config['min_coverage']}%)")
    parser.add_argument("--min-compliance", type=float,
                       default=config["min_compliance"],
                       help=f"Compliance threshold (default: {config['min_compliance']}%)")
    parser.add_argument("--output", type=Path, help="Output JSON report")
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"DocuGenius Validation (Milestone 3)")
    print(f"Coverage Threshold: {args.min_coverage}%")
    print(f"Compliance Threshold: {args.min_compliance}%")
    print(f"{'='*60}")
    
    results = []
    all_passed = True
    
    for filepath in args.files:
        if not filepath.endswith('.py'):
            continue
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            quality = DocstringValidator.analyze_code_quality(content)
            passed = (
                quality['coverage_percentage'] >= args.min_coverage and 
                quality['compliance_percentage'] >= args.min_compliance
            )
            
            status = "PASSED" if passed else "FAILED"
            print(f"\nFile: {Path(filepath).name}")
            print(f"   Coverage: {quality['coverage_percentage']}% ({status})")
            print(f"   Compliance: {quality['compliance_percentage']}%")
            
            results.append({
                'filepath': filepath,
                'coverage': quality['coverage_percentage'],
                'compliance': quality['compliance_percentage'],
                'passed': passed
            })
            
            if not passed:
                all_passed = False
                
        except Exception as e:
            print(f"\nError processing {filepath}: {e}")
            all_passed = False
    
    # Generate report
    if args.output:
        report = {
            "config": {
                "min_coverage": args.min_coverage,
                "min_compliance": args.min_compliance,
                "style": config["style"]
            },
            "files": results,
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r['passed']),
                "failed": sum(1 for r in results if not r['passed'])
            }
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {args.output}")
    
    print(f"\n{'='*60}")
    passed_count = sum(1 for r in results if r['passed'])
    print(f"SUMMARY: {passed_count}/{len(results)} files passed")
    print(f"{'='*60}")
    
    # Critical: Exit with proper code
    sys.exit(0 if all_passed and len(results) > 0 else 1)

if __name__ == "__main__":
    main()