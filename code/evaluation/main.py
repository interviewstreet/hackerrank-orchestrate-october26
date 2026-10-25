"""Evaluation runner entry point."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import main

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <pred.csv> <gold.csv>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
