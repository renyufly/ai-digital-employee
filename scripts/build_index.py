"""Build the persistent local FAISS knowledge index."""

import json
import sys
from pathlib import Path

# Keep the documented `python scripts/build_index.py` entry point runnable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.rag.indexer import build_index


if __name__ == "__main__":
    result = build_index(get_settings())
    print(json.dumps(result, ensure_ascii=False, indent=2))
