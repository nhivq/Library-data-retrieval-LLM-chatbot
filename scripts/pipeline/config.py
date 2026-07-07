import sys
from pathlib import Path


PAGE_SIZE = 1000

DEFAULT_SEARCH_LIMIT = 1000

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

RAW_WORK_FOLDER = f"{PROJECT_ROOT}/data/raw/works"
RAW_EDITION_FOLDER = f"{PROJECT_ROOT}/data/raw/editions"
CLEAN_FOLDER = f"{PROJECT_ROOT}/data/clean/works"
STATE_FILE = f"{PROJECT_ROOT}/scripts/logs/pipeline_state.json"
PROCESSED_KEYS_FILE = f"{PROJECT_ROOT}/scripts/logs/processed_key.json"