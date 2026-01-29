#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from m2_core import DocstringValidator

def main():
    parser = argparse.ArgumentParser(description="DocuGenius Validator (Milestone 3)")
    parser.add_argument("files", nargs="+", help="Python files to validate")
    parser.add_argument("--min-coverage", type=float, default=90.0, help="Coverage threshold")
    parser.add_argument("--min-compliance", type=float, default=85.0, help="Compliance threshold")
    parser.add_argument("--output", type=Path, help="Output JSON report")
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"DocuGenius Validation (Milestone 3)")
    print(f"Coverage Threshold: {args.min_coverage}%")
    print(f"Compliance Threshold: {args.min_compliance}%")
    print(f"{'='*60}")
    
    results = []
    all_passed = True  # ← START WITH TRUE
    
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
                all_passed = False  # ← ONLY set to False if a file fails
                
        except Exception as e:
            print(f"\nError processing {filepath}: {e}")
            all_passed = False  # ← Error = failure
    
    # Generate report
    if args.output:
        report = {
            "thresholds": {
                "min_coverage": args.min_coverage,
                "min_compliance": args.min_compliance
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
    
    # CRITICAL: Exit with 0 if ALL passed, 1 if ANY failed
    # At the VERY END of main() function, replace any existing sys.exit with:
    if all_passed and len(results) > 0:
        sys.exit(0)  # SUCCESS - all files passed
    else:
        sys.exit(1)  # FAILURE - some files failed or no files processed
if __name__ == "__main__":
    main()