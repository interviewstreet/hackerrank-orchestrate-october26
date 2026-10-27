"""
Data Loaders for Evidence Files
Handles CSV, SQL, JSON, PDF, images, and logs
"""
import csv
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import config
from config import DATASET_DIR, EVIDENCE_DIR


def load_csv(filename: str) -> List[Dict[str, str]]:
    """Load CSV file and return list of dictionaries"""
    filepath = DATASET_DIR / filename
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_deletion_requests() -> List[Dict]:
    """Load all deletion requests"""
    return load_csv('deletion_requests.csv')


def load_user_identities() -> List[Dict]:
    """Load current user identities"""
    return load_csv('user_identities.csv')


def load_user_audit_log() -> List[Dict]:
    """Load user audit log (historical identity changes)"""
    return load_csv('user_audit_log.csv')


def load_system_activity() -> List[Dict]:
    """Load system activity log"""
    return load_csv('system_activity.csv')


def load_deletion_rules() -> List[Dict]:
    """Load deletion policy rules"""
    return load_csv('deletion_rules.csv')


def load_evidence_files_manifest() -> List[Dict]:
    """Load evidence files manifest"""
    return load_csv('evidence_files.csv')


def execute_sql_file(sql_file_path: Path) -> Dict[str, Any]:
    """
    Execute a SQL file and extract all table data
    
    Returns:
        Dict with table names as keys and list of rows as values
    """
    # Create in-memory SQLite database
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    try:
        # Read and execute SQL file
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Execute all statements
        cursor.executescript(sql_content)
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Extract data from each table
        result = {}
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            result[table] = [
                dict(zip(columns, row)) for row in rows
            ]
        
        return result
        
    finally:
        conn.close()


def load_json_file(file_path: Path) -> Any:
    """Load and parse JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_text_file(file_path: Path) -> str:
    """Load text file content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_pdf_text(file_path: Path) -> str:
    """
    Extract text from PDF using pdftotext (if available) or fallback
    """
    try:
        # Try using pdftotext command (part of poppler-utils)
        result = subprocess.run(
            ['pdftotext', '-layout', str(file_path), '-'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback: return a note that PDF couldn't be processed
    return f"[PDF file: {file_path.name} - text extraction not available]"


def get_image_description(file_path: Path) -> str:
    """
    Get a description of an image file
    For now, just return filename and note
    Later can be enhanced with OCR or vision models
    """
    return f"[Image file: {file_path.name} - {file_path.stem.replace('_', ' ')}]"


def load_evidence_file(file_id: str, evidence_manifest: List[Dict]) -> tuple[str, Any]:
    """
    Load evidence file by ID
    
    Returns:
        (file_type, content) tuple
    """
    # Find file in manifest
    file_info = next((f for f in evidence_manifest if f['file_id'] == file_id), None)
    if not file_info:
        return ("not_found", None)
    
    file_path = DATASET_DIR / file_info['file_path']
    
    if not file_path.exists():
        return ("not_found", None)
    
    # Determine file type and load accordingly
    suffix = file_path.suffix.lower()
    
    if suffix == '.sql':
        return ("sql", execute_sql_file(file_path))
    elif suffix == '.json':
        return ("json", load_json_file(file_path))
    elif suffix == '.pdf':
        return ("pdf", load_pdf_text(file_path))
    elif suffix in ['.png', '.jpg', '.jpeg', '.gif']:
        return ("image", get_image_description(file_path))
    elif suffix in ['.log', '.txt']:
        return ("text", load_text_file(file_path))
    else:
        return ("unknown", f"[Unknown file type: {suffix}]")


class DataCache:
    """Cache for frequently accessed data"""
    
    def __init__(self):
        self._cache = {}
        self._load_all()
    
    def _load_all(self):
        """Pre-load all CSV data"""
        print("Loading dataset...")
        self._cache['deletion_requests'] = load_deletion_requests()
        self._cache['user_identities'] = load_user_identities()
        self._cache['user_audit_log'] = load_user_audit_log()
        self._cache['system_activity'] = load_system_activity()
        self._cache['deletion_rules'] = load_deletion_rules()
        self._cache['evidence_manifest'] = load_evidence_files_manifest()
        print(f"✓ Loaded {len(self._cache['deletion_requests'])} deletion requests")
        print(f"✓ Loaded {len(self._cache['user_identities'])} user identities")
        print(f"✓ Loaded {len(self._cache['user_audit_log'])} audit log entries")
        print(f"✓ Loaded {len(self._cache['system_activity'])} system activity entries")
        print(f"✓ Loaded {len(self._cache['deletion_rules'])} deletion rules")
        print(f"✓ Loaded {len(self._cache['evidence_manifest'])} evidence files")
    
    def get(self, key: str) -> Any:
        """Get cached data"""
        return self._cache.get(key)
    
    def get_deletion_requests(self) -> List[Dict]:
        return self._cache['deletion_requests']
    
    def get_user_identities(self) -> List[Dict]:
        return self._cache['user_identities']
    
    def get_user_audit_log(self) -> List[Dict]:
        return self._cache['user_audit_log']
    
    def get_system_activity(self) -> List[Dict]:
        return self._cache['system_activity']
    
    def get_deletion_rules(self) -> List[Dict]:
        return self._cache['deletion_rules']
    
    def get_evidence_manifest(self) -> List[Dict]:
        return self._cache['evidence_manifest']


# Global cache instance
data_cache = DataCache()
