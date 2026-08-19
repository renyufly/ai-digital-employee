"""Initialize the project-local mock ERP database with fixed sample data."""

import sys
from pathlib import Path

# Keep the documented `python scripts/seed_erp.py` entry point runnable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from mock_erp.seed import seed_database


def main() -> None:
    settings = get_settings()
    count = seed_database(settings.mock_erp_database_path)
    print(f"Seeded {count} orders into {settings.mock_erp_database_path}")


if __name__ == "__main__":
    main()
