#!/usr/bin/env python3
"""
Stress test and benchmark script for 50M records scale.
Generates synthetic data and measures performance.
"""

import csv
import json
import os
import random
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import tempfile
import shutil
import sys

# Add code to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))


def generate_large_dataset(output_dir: Path, num_users: int, num_requests: int, 
                          num_activities: int, num_evidence_files: int):
    """Generate synthetic dataset for stress testing."""
    print(f"Generating dataset: {num_users} users, {num_requests} requests, "
          f"{num_activities} activities, {num_evidence_files} evidence files")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_dir / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    
    # Generate user identities
    print("Generating user_identities.csv...")
    with open(output_dir / "user_identities.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "name", "email", "phone", "email_hash", "updated_at"])
        base_date = datetime(2025, 1, 1)
        for i in range(num_users):
            user_id = f"user_{i:08d}"
            name = f"User {i}"
            email = f"user{i}@example.com"
            phone = f"+1-555-{i:04d}"
            email_hash = f"{i:064x}"  # 64-char hex
            updated_at = (base_date + timedelta(days=random.randint(0, 365))).isoformat() + "Z"
            writer.writerow([user_id, name, email, phone, email_hash, updated_at])
    
    # Generate audit logs (historical changes)
    print("Generating user_audit_log.csv...")
    with open(output_dir / "user_audit_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["audit_id", "user_id", "event_time", "field_name", "old_value", "new_value"])
        for i in range(min(num_users, 10000)):  # Only for first 10k users
            user_id = f"user_{i:08d}"
            if random.random() < 0.3:  # 30% have email change
                old_email = f"user{i}_old@example.com"
                new_email = f"user{i}@example.com"
                audit_dt = base_date + timedelta(days=random.randint(0, 365))
                audit_time = audit_dt.isoformat().replace("+00:00", "") + "Z"
                writer.writerow([f"audit_{i}_email", user_id, audit_time, "email", old_email, new_email])
            if random.random() < 0.2:  # 20% have phone change
                old_phone = f"+1-555-{random.randint(0, 9999):04d}"
                new_phone = f"+1-555-{i:04d}"
                audit_dt = base_date + timedelta(days=random.randint(0, 365))
                audit_time = audit_dt.isoformat().replace("+00:00", "") + "Z"
                writer.writerow([f"audit_{i}_phone", user_id, audit_time, "phone", old_phone, new_phone])
    
    # Generate system activities
    print("Generating system_activity.csv...")
    event_types = ["SYNC_RECORD", "INDEX_RECORD", "BACKUP", "RESTORE", "DELETE_RECORD", 
                   "ANONYMIZE_RECORD", "UPDATE_RECORD", "EXPORT", "SEND_EMAIL", "RETAIN_RECORD"]
    source_systems = ["account_service", "analytics_platform", "search_service", "support_platform",
                      "export_service", "backup_service", "notification_service", "security_service",
                      "profile_service", "deletion_worker"]
    target_systems = ["account_service", "analytics_platform", "search_service", "support_platform",
                      "export_service", "backup_service", "email_delivery_service", "archive_service"]
    
    with open(output_dir / "system_activity.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["activity_id", "event_time", "event_type", "source_system", 
                        "target_system", "resource_id", "reported_result", "details"])
        for i in range(num_activities):
            user_idx = random.randint(0, num_users - 1)
            event_type = random.choice(event_types)
            source = random.choice(source_systems)
            target = random.choice(target_systems)
            resource_id = f"{target}_{random.randint(0, 1000000):06d}"
            result = random.choice(["SUCCESS", "FAILED", "PARTIAL"])
            details = f"{event_type} processed {resource_id} for user{user_idx}@example.com"
            event_dt = base_date + timedelta(days=random.randint(0, 730))
            event_time = event_dt.isoformat().replace("+00:00", "") + "Z"
            writer.writerow([f"act_{i:08d}", event_time, event_type, source, target, resource_id, result, details])
    
    # Generate deletion rules (same as original)
    print("Generating deletion_rules.csv...")
    rules = [
        ("rule_01", "USER_PROFILE", "Always", "DELETE"),
        ("rule_02", "SECONDARY_IDENTIFIER", "Always", "DELETE"),
        ("rule_03", "SEARCH_INDEX_ENTRY", "Always", "DELETE"),
        ("rule_04", "CACHE_ENTRY", "Always", "DELETE"),
        ("rule_05", "SUPPORT_MESSAGE", "Conversation contains shared customer, agent, or order context that must be retained", "REDACT"),
        ("rule_06", "SUPPORT_ATTACHMENT", "Attachment belongs only to the deletion subject", "DELETE"),
        ("rule_07", "ANALYTICS_PROFILE", "Record is still attributable to a user", "ANONYMIZE"),
        ("rule_08", "PRODUCT_TELEMETRY", "Record is still attributable to a user", "ANONYMIZE"),
        ("rule_09", "USER_EXPORT", "Always", "DELETE"),
        ("rule_10", "MARKETING_PROFILE", "Always", "DELETE"),
        ("rule_11", "EMAIL_DELIVERY_LOG", "Log contains a user email address", "REDACT"),
        ("rule_12", "SECURITY_AUDIT_LOG", "Record is within the supplied retention period", "RETAIN"),
        ("rule_13", "LEGAL_HOLD_RECORD", "A supplied legal hold is active", "RETAIN"),
        ("rule_14", "BACKUP_ARCHIVE", "Restore access can be blocked", "RETAIN"),
        ("rule_15", "ACCOUNT_TOMBSTONE", "Account is deleted and only a stable internal user_id is needed to preserve references to retained records", "REDACT"),
    ]
    with open(output_dir / "deletion_rules.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rule_id", "data_category", "condition", "required_action"])
        for rule in rules:
            writer.writerow(rule)
    
    # Generate evidence files manifest
    print("Generating evidence_files.csv...")
    evidence_types = [
        ("account_service", "sql"),
        ("analytics_platform", "json"),
        ("search_service", "json"),
        ("backup_service", "sql"),
        ("export_service", "json"),
        ("email_delivery_service", "log"),
        ("security_service", "log"),
        ("support_platform", "json"),
    ]
    with open(output_dir / "evidence_files.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file_id", "file_path", "origin", "captured_at"])
        for i in range(num_evidence_files):
            sys_id, ext = random.choice(evidence_types)
            file_id = f"ev_{i:06d}"
            file_path = f"evidence/{sys_id}_{i:06d}.{ext}"
            captured_dt = base_date + timedelta(days=random.randint(0, 730))
            captured_at = captured_dt.isoformat().replace("+00:00", "") + "Z"
            writer.writerow([file_id, file_path, sys_id, captured_at])
    
    # Generate deletion requests
    print("Generating deletion_requests.csv...")
    deletion_templates = [
        "Please delete my account and all associated personal data.",
        "I want to close my account and have my data erased permanently.",
        "Please remove my profile and personal information from your systems.",
        "Delete my account please.",
        "I would like my account deleted and all data removed.",
        "Please process a permanent account deletion request for this email address.",
        "I am requesting deletion of the account registered to this email address.",
    ]
    non_deletion_templates = [
        "I would like to access my data and correct my email address.",
        "Please export my data and then delete my account.",
        "Unsubscribe me from marketing emails.",
        "I want to update my preferences.",
        "Please let me view my personal data.",
    ]
    
    with open(output_dir / "deletion_requests.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text"])
        for i in range(num_requests):
            case_id = f"case_{i:08d}"
            user_idx = random.randint(0, num_users - 1)
            email = f"user{user_idx}@example.com"
            requested_at = (base_date + timedelta(days=random.randint(0, 700))).isoformat().replace("+00:00", "") + "Z"
            reported_dt = datetime.fromisoformat(requested_at.replace("Z", "+00:00")) + timedelta(days=random.randint(1, 5))
            reported_at = reported_dt.isoformat().replace("+00:00", "") + "Z"
            audit_dt = datetime.fromisoformat(reported_at.replace("Z", "+00:00")) + timedelta(days=random.randint(1, 10))
            audit_at = audit_dt.isoformat().replace("+00:00", "") + "Z"
            reported_status = random.choice(["COMPLETE", "PARTIALLY_COMPLETE", "NOT_STARTED"])
            
            if random.random() < 0.85:  # 85% deletion requests
                request_text = random.choice(deletion_templates)
            else:
                request_text = random.choice(non_deletion_templates)
            
            writer.writerow([case_id, email, requested_at, reported_status, reported_at, audit_at, request_text])
    
    # Generate evidence files
    print("Generating evidence files...")
    for i in range(num_evidence_files):
        sys_id, ext = random.choice(evidence_types)
        file_path = evidence_dir / f"{sys_id}_{i:06d}.{ext}"
        
        if ext == "sql":
            # Generate SQL with user data
            num_records = random.randint(100, 1000)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("CREATE TABLE user_data (\n")
                f.write("    user_id TEXT,\n    email TEXT,\n    phone TEXT,\n    name TEXT,\n    email_hash TEXT,\n    data TEXT\n);\n\n")
                for j in range(num_records):
                    u = random.randint(0, num_users - 1)
                    f.write(f"INSERT INTO user_data VALUES ('user_{u:08d}', 'user{u}@example.com', '+1-555-{u:04d}', 'User {u}', '{u:064x}', '{{}}');\n")
        
        elif ext == "json":
            # Generate JSON with user data
            num_records = random.randint(100, 1000)
            records = []
            for j in range(num_records):
                u = random.randint(0, num_users - 1)
                records.append({
                    "resource_id": f"{sys_id}_{j:06d}",
                    "user_id": f"user_{u:08d}",
                    "email": f"user{u}@example.com",
                    "name": f"User {u}",
                    "phone": f"+1-555-{u:04d}",
                    "email_hash": f"{u:064x}"
                })
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({f"{sys_id}_records": records}, f)
        
        elif ext == "log":
            # Generate log file
            num_lines = random.randint(500, 5000)
            with open(file_path, "w", encoding="utf-8") as f:
                for j in range(num_lines):
                    u = random.randint(0, num_users - 1)
                    f.write(f"2026-01-10T10:00:00Z INFO Processed user{u}@example.com for {sys_id}\n")
    
    print(f"Dataset generated in {output_dir}")


def run_benchmark(dataset_dir: Path, num_runs: int = 3) -> Dict[str, float]:
    """Run the solution on the dataset and measure performance."""
    import main
    
    times = []
    memory_usage = []
    
    for run in range(num_runs):
        print(f"\nRun {run + 1}/{num_runs}...")
        
        # Create temp copy for isolation
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_dataset = tmpdir_path / "dataset"
            shutil.copytree(dataset_dir, test_dataset)
            
            main.BASE_DIR = tmpdir_path
            main.DATASET_DIR = test_dataset
            main.EVIDENCE_DIR = test_dataset / "evidence"
            
            # Measure time
            start_time = time.time()
            
            loader = main.DataLoader()
            loader.load_all()
            load_time = time.time()
            
            auditor = main.DeletionAuditor(loader)
            
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
            
            with open(tmpdir_path / "output.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["case_id", "deletion_status", "steps_json"])
                for case_id, status, steps_json in results:
                    writer.writerow([case_id, status, steps_json])
            
            end_time = time.time()
            
            total_time = end_time - start_time
            load_duration = load_time - start_time
            process_duration = end_time - load_time
            
            times.append({
                "total": total_time,
                "load": load_duration,
                "process": process_duration
            })
            
            print(f"  Load time: {load_duration:.2f}s")
            print(f"  Process time: {process_duration:.2f}s")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Requests/sec: {len(loader.requests) / total_time:.1f}")
    
    # Calculate averages
    avg_total = sum(t["total"] for t in times) / len(times)
    avg_load = sum(t["load"] for t in times) / len(times)
    avg_process = sum(t["process"] for t in times) / len(times)
    
    return {
        "avg_total": avg_total,
        "avg_load": avg_load,
        "avg_process": avg_process,
        "runs": times
    }


def estimate_50m_performance(benchmark_results: Dict, current_scale: Dict) -> Dict:
    """Estimate performance at 50M scale based on benchmark."""
    # Current scale metrics
    current_users = current_scale["users"]
    current_requests = current_scale["requests"]
    current_activities = current_scale["activities"]
    current_evidence = current_scale["evidence"]
    
    # Target scale
    target_users = 50_000_000
    target_requests = 50_000_000
    target_activities = 200_000_000  # ~4 per user
    target_evidence = 100_000  # Evidence files don't scale linearly
    
    # Complexity analysis:
    # - Loading: O(users + activities + evidence_files)
    # - Processing per request: O(evidence_files_per_request + activities_per_request)
    # - Evidence parsing: O(evidence_size) per file
    
    load_scale_factor = (target_users + target_activities + target_evidence) / (current_users + current_activities + current_evidence)
    # Processing scales with requests * evidence_files (each request checks all evidence files)
    process_scale_factor = (target_requests / current_requests) * (target_evidence / current_evidence)
    
    estimated_load = benchmark_results["avg_load"] * load_scale_factor
    estimated_process = benchmark_results["avg_process"] * process_scale_factor
    estimated_total = estimated_load + estimated_process
    
    return {
        "estimated_load_time_seconds": estimated_load,
        "estimated_process_time_seconds": estimated_process,
        "estimated_total_time_seconds": estimated_total,
        "estimated_total_time_hours": estimated_total / 3600,
        "load_scale_factor": load_scale_factor,
        "process_scale_factor": process_scale_factor
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Stress test for Ghost Data Still Exists")
    parser.add_argument("--scale", choices=["small", "medium", "large", "xlarge"], default="small",
                       help="Dataset scale for testing")
    parser.add_argument("--runs", type=int, default=3, help="Number of benchmark runs")
    parser.add_argument("--generate-only", action="store_true", help="Only generate data, don't run benchmark")
    args = parser.parse_args()
    
    scale_configs = {
        "small": {"users": 1000, "requests": 1000, "activities": 5000, "evidence": 20},
        "medium": {"users": 10000, "requests": 10000, "activities": 50000, "evidence": 50},
        "large": {"users": 100000, "requests": 100000, "activities": 500000, "evidence": 100},
        "xlarge": {"users": 1000000, "requests": 1000000, "activities": 5000000, "evidence": 200},
    }
    
    config = scale_configs[args.scale]
    
    # Generate dataset
    dataset_dir = Path(f"benchmark_data_{args.scale}")
    generate_large_dataset(dataset_dir, config["users"], config["requests"], 
                          config["activities"], config["evidence"])
    
    if args.generate_only:
        print("Data generation complete. Exiting.")
        return
    
    # Run benchmark
    print(f"\nRunning benchmark on {args.scale} scale...")
    results = run_benchmark(dataset_dir, args.runs)
    
    print(f"\n=== BENCHMARK RESULTS ({args.scale}) ===")
    print(f"Average load time: {results['avg_load']:.2f}s")
    print(f"Average process time: {results['avg_process']:.2f}s")
    print(f"Average total time: {results['avg_total']:.2f}s")
    print(f"Throughput: {config['requests'] / results['avg_total']:.1f} requests/sec")
    
    # Estimate 50M performance
    print(f"\n=== 50M SCALE ESTIMATION ===")
    estimate = estimate_50m_performance(results, config)
    print(f"Estimated load time: {estimate['estimated_load_time_seconds'] / 3600:.2f} hours")
    print(f"Estimated process time: {estimate['estimated_process_time_seconds'] / 3600:.2f} hours")
    print(f"Estimated total time: {estimate['estimated_total_time_seconds'] / 3600:.2f} hours")
    print(f"Load scale factor: {estimate['load_scale_factor']:.1f}x")
    print(f"Process scale factor: {estimate['process_scale_factor']:.1f}x")
    
    # Save results
    output = {
        "scale": args.scale,
        "config": config,
        "benchmark_results": results,
        "estimation_50m": estimate
    }
    with open(f"benchmark_results_{args.scale}.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to benchmark_results_{args.scale}.json")


if __name__ == "__main__":
    main()