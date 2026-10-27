"""
Configuration for the Deletion Audit Agent
Loads environment variables and defines constants
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
EVIDENCE_DIR = DATASET_DIR / "evidence"
OUTPUT_PATH = PROJECT_ROOT / "output.csv"

# API Configuration
EXPLABS_API_KEY = os.environ.get('EXPLABS_API_KEY')
EXPLABS_BASE_URL = "https://api.experientiallabs.ai/v1"
MODEL_NAME = "claude-haiku-5.5"

# Model costs (per 1M tokens)
MODEL_INPUT_COST = 0.10  # $0.10 per 1M input tokens
MODEL_OUTPUT_COST = 0.50  # $0.50 per 1M output tokens

# Processing constants
BATCH_SIZE = 10  # Process cases in batches
MAX_RETRIES = 3  # Retry failed API calls
REQUEST_TIMEOUT = 120  # Seconds

# Validate API key
if not EXPLABS_API_KEY:
    raise ValueError(
        "EXPLABS_API_KEY not found in environment. "
        "Please set it in .env file or export it."
    )

print(f"✓ Configuration loaded")
print(f"  Model: {MODEL_NAME}")
print(f"  Dataset: {DATASET_DIR}")
print(f"  Output: {OUTPUT_PATH}")
