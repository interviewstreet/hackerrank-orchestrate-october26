#!/usr/bin/env python3
"""
Test Runner for Ghost Data Still Exists - Deletion Audit Agent
Validates solution against test cases and checks for correctness.
"""

import csv
import json
import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
import subprocess

# Add the code directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from main import OptimizedDataLoader as DataLoader, OptimizedDeletionAuditor as DeletionAuditor, DeletionRequest, Step


class TestValidator:
    def __init__(self, test_data_dir: Path):
        self.test_data_dir = test_data_dir
        self.results = []
        self.errors = []
        
    def run_solution(self) -> Path:
        """Run the main solution with test data and return output path."""
        # Create a temporary directory for test run
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Copy test data to expected locations
            test_dataset = tmpdir_path / "dataset"
            test_dataset.mkdir()
            test_evidence = test_dataset / "evidence"
            test_evidence.mkdir()
            
            # Copy all test CSV files
            for csv_file in ["deletion_requests.csv", "user_identities.csv", "user_audit_log.csv", 
                           "system_activity.csv", "deletion_rules.csv", "evidence_files.csv"]:
                src = self.test_data_dir / csv_file
                dst = test_dataset / csv_file
                shutil.copy2(src, dst)
            
            # Copy evidence files
            for evidence_file in (self.test_data_dir / "evidence").glob("*"):
                shutil.copy2(evidence_file, test_evidence / evidence_file.name)
            
            # Run the solution with modified paths
            # We'll import and run directly instead of subprocess for speed
            original_base = Path(__file__).parent.parent
            import main
            
            # Monkey-patch the paths
            main.BASE_DIR = tmpdir_path
            main.DATASET_DIR = test_dataset
            main.EVIDENCE_DIR = test_evidence
            
            # Run the main logic
            loader = main.OptimizedDataLoader()
            loader.load_all()
            
            auditor = main.OptimizedDeletionAuditor(loader)
            
            results = []
            for request in loader.requests:
                status, steps = auditor.audit_request(request)
                steps_json = json.dumps([{
                    "step_no": s.step_no,
                    "phase": s.phase,
                    "system_id": s.system_id,
                    "resource_id": s.resource_id,
                    "operation": s.operation,
                    "state": s.state,
                    "evidence_id": s.evidence_id
                } for s in steps], separators=(',', ':'))
                results.append((request.case_id, status, steps_json))
            
            results.sort(key=lambda x: x[0])
            
            # Write output
            output_path = tmpdir_path / "output.csv"
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["case_id", "deletion_status", "steps_json"])
                for case_id, status, steps_json in results:
                    writer.writerow([case_id, status, steps_json])
            
            # Copy to permanent location for inspection
            permanent_output = self.test_data_dir / "actual_output.csv"
            shutil.copy2(output_path, permanent_output)
            
            return permanent_output
    
    def validate_output(self, output_path: Path) -> List[Dict]:
        """Validate the output against expected results."""
        validation_results = []
        
        # Load actual output
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            actual_rows = {row["case_id"]: row for row in reader}
        
        # Load expected output
        expected_path = self.test_data_dir / "expected_output.csv"
        with open(expected_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            expected_rows = {row["case_id"]: row for row in reader}
        
        for case_id, expected in expected_rows.items():
            result = {
                "case_id": case_id,
                "passed": True,
                "errors": [],
                "warnings": []
            }
            
            if case_id not in actual_rows:
                result["passed"] = False
                result["errors"].append(f"Missing case in output: {case_id}")
                validation_results.append(result)
                continue
            
            actual = actual_rows[case_id]
            
            # Check deletion_status
            expected_status = expected["deletion_status"]
            actual_status = actual["deletion_status"]
            if expected_status != actual_status:
                result["passed"] = False
                result["errors"].append(f"Status mismatch: expected {expected_status}, got {actual_status}")
            
            # Parse and validate steps_json
            try:
                steps = json.loads(actual["steps_json"])
            except json.JSONDecodeError as e:
                result["passed"] = False
                result["errors"].append(f"Invalid JSON: {e}")
                validation_results.append(result)
                continue
            
            # Check step numbering
            for i, step in enumerate(steps):
                if step["step_no"] != i + 1:
                    result["passed"] = False
                    result["errors"].append(f"Step numbering error at index {i}: expected {i+1}, got {step['step_no']}")
            
            # Check phase ordering
            phases = [s["phase"] for s in steps]
            phase_order = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
            phase_indices = [phase_order.get(p, -1) for p in phases]
            if phase_indices != sorted(phase_indices):
                result["passed"] = False
                result["errors"].append(f"Phase ordering violation: {phases}")
            
            # Check operation validity
            valid_operations = {
                "FINDING": ["REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REPORT_ACTIVE_DATA_FLOW", "REPORT_RESTORE_RISK"],
                "REMEDIATION": ["DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD", "REDACT_RECORD", "ANONYMIZE_RECORD"],
                "VERIFICATION": ["VERIFY_RECORD_ABSENT", "VERIFY_RECORD_PRESENT", "VERIFY_RECORD_REDACTED", "VERIFY_RECORD_ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED", "VERIFY_RESTORE_BLOCKED"]
            }
            for step in steps:
                phase = step["phase"]
                op = step["operation"]
                if phase in valid_operations and op not in valid_operations[phase]:
                    result["passed"] = False
                    result["errors"].append(f"Invalid operation {op} for phase {phase}")
            
            # Check state validity
            valid_states = {
                "REPORT_REMAINING_RECORD": "PRESENT",
                "REPORT_EXPOSED_PII": "PRESENT",
                "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
                "REPORT_RESTORE_RISK": "ACTIVE",
                "DISABLE_DATA_FLOW": "DISABLED",
                "BLOCK_RESTORE": "BLOCKED",
                "DELETE_RECORD": "ABSENT",
                "REDACT_RECORD": "REDACTED",
                "ANONYMIZE_RECORD": "ANONYMIZED",
                "VERIFY_RECORD_ABSENT": "ABSENT",
                "VERIFY_RECORD_PRESENT": "PRESENT",
                "VERIFY_RECORD_REDACTED": "REDACTED",
                "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
                "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
                "VERIFY_RESTORE_BLOCKED": "BLOCKED"
            }
            for step in steps:
                op = step["operation"]
                state = step["state"]
                if op in valid_states and valid_states[op] != state:
                    result["passed"] = False
                    result["errors"].append(f"Invalid state {state} for operation {op}, expected {valid_states[op]}")
            
            # Check evidence_id rules
            if actual_status == "COMPLETE":
                for step in steps:
                    if step["phase"] in ("FINDING", "VERIFICATION") and not step["evidence_id"]:
                        result["passed"] = False
                        result["errors"].append(f"COMPLETE case missing evidence_id for step {step['step_no']}")
            elif actual_status == "INCOMPLETE":
                for step in steps:
                    if step["phase"] == "REMEDIATION" and step["evidence_id"]:
                        result["passed"] = False
                        result["errors"].append(f"INCOMPLETE remediation step {step['step_no']} should have empty evidence_id")
                    if step["phase"] == "VERIFICATION" and step["evidence_id"]:
                        result["passed"] = False
                        result["errors"].append(f"INCOMPLETE verification step {step['step_no']} should have empty evidence_id")
            
            # Check expected counts (approximate)
            expected_findings = int(expected.get("expected_findings_count", 0))
            expected_remediation = int(expected.get("expected_remediation_count", 0))
            expected_verification = int(expected.get("expected_verification_count", 0))
            
            actual_findings = sum(1 for s in steps if s["phase"] == "FINDING")
            actual_remediation = sum(1 for s in steps if s["phase"] == "REMEDIATION")
            actual_verification = sum(1 for s in steps if s["phase"] == "VERIFICATION")
            
            if actual_status == "INCOMPLETE":
                if actual_findings < expected_findings:
                    result["warnings"].append(f"Fewer findings than expected: {actual_findings} vs {expected_findings}")
                if actual_remediation < expected_remediation:
                    result["warnings"].append(f"Fewer remediation steps than expected: {actual_remediation} vs {expected_remediation}")
                if actual_verification < expected_verification:
                    result["warnings"].append(f"Fewer verification steps than expected: {actual_verification} vs {expected_verification}")
            elif actual_status == "NOT_APPLICABLE":
                if len(steps) != 0:
                    result["passed"] = False
                    result["errors"].append(f"NOT_APPLICABLE should have empty steps array, got {len(steps)} steps")
            
            validation_results.append(result)
        
        # Check for extra cases in actual output
        for case_id in actual_rows:
            if case_id not in expected_rows:
                validation_results.append({
                    "case_id": case_id,
                    "passed": False,
                    "errors": [f"Unexpected case in output: {case_id}"],
                    "warnings": []
                })
        
        return validation_results
    
    def print_results(self, validation_results: List[Dict]):
        """Print validation results."""
        total = len(validation_results)
        passed = sum(1 for r in validation_results if r["passed"])
        failed = total - passed
        
        print(f"\n{'='*60}")
        print(f"VALIDATION RESULTS: {passed}/{total} passed, {failed} failed")
        print(f"{'='*60}")
        
        for result in validation_results:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"\n[{status}] {result['case_id']}")
            for error in result["errors"]:
                print(f"  ERROR: {error}")
            for warning in result["warnings"]:
                print(f"  WARN: {warning}")
        
        if failed > 0:
            print(f"\n{'='*60}")
            print(f"FAILURES: {failed} test(s) failed")
            print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print("ALL TESTS PASSED!")
            print(f"{'='*60}")
        
        return failed == 0


def main():
    test_data_dir = Path(__file__).parent / "test_data"
    
    print("Setting up test environment...")
    validator = TestValidator(test_data_dir)
    
    print("Running solution on test data...")
    output_path = validator.run_solution()
    print(f"Output written to: {output_path}")
    
    print("Validating output...")
    validation_results = validator.validate_output(output_path)
    
    success = validator.print_results(validation_results)
    
    # Also validate the main output.csv
    print("\n\nValidating main output.csv...")
    main_output = Path(__file__).parent.parent / "output.csv"
    if main_output.exists():
        # Just validate structure, not against expected
        with open(main_output, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            main_rows = list(reader)
        print(f"Main output: {len(main_rows)} cases")
        
        # Validate JSON and structure
        main_errors = 0
        for row in main_rows:
            try:
                steps = json.loads(row["steps_json"])
                for i, step in enumerate(steps):
                    if step["step_no"] != i + 1:
                        print(f"  Step numbering error in {row['case_id']}: index {i}, step_no {step['step_no']}")
                        main_errors += 1
                phases = [s["phase"] for s in steps]
                phase_order = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
                phase_indices = [phase_order.get(p, -1) for p in phases]
                if phase_indices != sorted(phase_indices):
                    print(f"  Phase ordering error in {row['case_id']}: {phases}")
                    main_errors += 1
            except json.JSONDecodeError as e:
                print(f"  JSON error in {row['case_id']}: {e}")
                main_errors += 1
        
        if main_errors == 0:
            print("Main output structure validation: PASSED")
        else:
            print(f"Main output structure validation: {main_errors} errors")
    else:
        print("Main output.csv not found")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()