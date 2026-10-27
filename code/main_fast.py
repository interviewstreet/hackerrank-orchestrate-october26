#!/usr/bin/env python3
"""
Fast Main Entry Point
Uses optimized fast agent
"""
import os
import sys
import csv
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from utils import LLMClient, usage_tracker, data_cache
from models.fast_agent import FastDeletionAgent
import config


def write_output_csv(results: list, output_path: Path):
    """Write results to output.csv"""
    print(f"\nWriting results to {output_path}...")
    
    results_sorted = sorted(results, key=lambda x: x['case_id'])
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['case_id', 'deletion_status', 'steps_json'])
        writer.writeheader()
        
        for result in results_sorted:
            output_row = {
                'case_id': result['case_id'],
                'deletion_status': result['deletion_status'],
                'steps_json': result['steps_json']
            }
            writer.writerow(output_row)
    
    print(f"✓ Wrote {len(results_sorted)} rows")


def main():
    """Main execution"""
    print("="*80)
    print("FAST DELETION AUDIT AGENT")
    print("="*80)
    print()
    
    start_time = datetime.now()
    
    # Args
    start_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end_idx = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Initialize
    llm_client = LLMClient()
    agent = FastDeletionAgent(llm_client)
    
    # Load cases
    deletion_requests = data_cache.get_deletion_requests()
    
    if end_idx is None:
        end_idx = len(deletion_requests)
    
    print(f"Processing cases {start_idx} to {end_idx}")
    print()
    
    # Process
    results = agent.audit_all_cases(deletion_requests, start_idx, end_idx)
    
    # Write
    write_output_csv(results, config.OUTPUT_PATH)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    usage = usage_tracker.get_summary()
    
    print(f"Cases: {len(results)}")
    print(f"API calls: {usage['total_calls']}")
    print(f"Tokens: {usage['total_tokens']:,}")
    print(f"Cost: ${usage['total_cost_usd']:.6f}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"Time: {duration:.1f}s")
    print(f"Per case: {duration / len(results):.1f}s" if results else "N/A")
    
    print("\n✓ Done!")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
