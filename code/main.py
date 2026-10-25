#!/usr/bin/env python3
"""Main entry point for Deletion Audit Agent (Northstar Shop Deletion Audit).

Usage:
    python code/main.py [dataset_dir] [output_csv_path]

Defaults:
    dataset_dir: 'dataset'
    output_csv_path: 'output.csv'
"""

import sys
import os

# Ensure package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audit.pipeline import run_audit


def main():
    dataset_dir = sys.argv[1] if len(sys.argv) > 1 else "dataset"
    output_csv_path = sys.argv[2] if len(sys.argv) > 2 else "output.csv"

    # Support passing direct path to deletion_requests.csv as first arg
    if os.path.isfile(dataset_dir):
        req_file = dataset_dir
        dataset_dir = os.path.dirname(dataset_dir) or "."
    else:
        req_file = os.path.join(dataset_dir, "deletion_requests.csv")

    print(f"Executing Deletion Audit Agent...")
    print(f"Dataset directory: {dataset_dir}")
    print(f"Requests file:     {req_file}")
    print(f"Output CSV path:   {output_csv_path}")

    run_audit(dataset_dir=dataset_dir, req_file=req_file, output_path=output_csv_path)


if __name__ == "__main__":
    main()
