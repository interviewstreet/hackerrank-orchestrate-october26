#!/usr/bin/env python3
"""
Main Entry Point for Deletion Audit Agent
HackerRank Orchestrate - October 2026
Ghost Data Still Exists Challenge
"""
import os
import sys
import csv
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from utils import LLMClient, usage_tracker, data_cache
from models.deletion_agent import DeletionAuditAgent
import config


def write_output_csv(results: list, output_path: Path):
    """Write results to output.csv"""
    print(f"\nWriting results to {output_path}...")
    
    # Sort by case_id
    results_sorted = sorted(results, key=lambda x: x['case_id'])
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['case_id', 'deletion_status', 'steps_json'])
        writer.writeheader()
        
        for result in results_sorted:
            # Remove error field if present (not part of output spec)
            output_row = {
                'case_id': result['case_id'],
                'deletion_status': result['deletion_status'],
                'steps_json': result['steps_json']
            }
            writer.writerow(output_row)
    
    print(f"✓ Wrote {len(results_sorted)} rows to {output_path}")


def main():
    """Main execution function"""
    print("="*80)
    print("DELETION AUDIT AGENT")
    print("HackerRank Orchestrate - October 2026")
    print("="*80)
    print()
    
    start_time = datetime.now()
    
    # Check for command line arguments
    start_idx = 0
    end_idx = None
    
    if len(sys.argv) > 1:
        start_idx = int(sys.argv[1])
    if len(sys.argv) > 2:
        end_idx = int(sys.argv[2])
    
    # Initialize LLM client
    print("Initializing LLM client...")
    llm_client = LLMClient()
    print(f"✓ Using model: {llm_client.model}")
    print()
    
    # Initialize agent
    print("Initializing Deletion Audit Agent...")
    agent = DeletionAuditAgent(llm_client)
    print()
    
    # Load cases
    deletion_requests = data_cache.get_deletion_requests()
    
    if end_idx is None:
        end_idx = len(deletion_requests)
    
    print(f"Processing cases {start_idx} to {end_idx} (total: {end_idx - start_idx})")
    print()
    
    # Process cases
    results = agent.audit_all_cases(deletion_requests, start_idx, end_idx)
    
    # Write output
    write_output_csv(results, config.OUTPUT_PATH)
    
    # Print usage summary
    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80)
    
    usage = usage_tracker.get_summary()
    
    print(f"Total cases processed: {len(results)}")
    print(f"Total API calls: {usage['total_calls']}")
    print(f"Total tokens: {usage['total_tokens']:,}")
    print(f"  - Prompt tokens: {usage['total_prompt_tokens']:,}")
    print(f"  - Completion tokens: {usage['total_completion_tokens']:,}")
    print(f"Average tokens per case: {usage['total_tokens'] / len(results):.0f}" if results else "N/A")
    print(f"Total cost: ${usage['total_cost_usd']:.6f}")
    print(f"Average cost per case: ${usage['total_cost_usd'] / len(results):.6f}" if results else "N/A")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\nTotal time: {duration:.1f} seconds")
    print(f"Average time per case: {duration / len(results):.1f} seconds" if results else "N/A")
    
    print("\n✓ Done!")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
