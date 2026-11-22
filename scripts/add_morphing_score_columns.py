"""
add_morphing_score_columns.py — SQLite migration script for DeepGuard AI v2.

Adds the 4 new morphing/face-swap detection score columns to the
`analysis_results` table for existing databases. Safe to run multiple
times (checks column existence before adding).

Usage:
    python add_morphing_score_columns.py
    python add_morphing_score_columns.py --db-path path/to/custom.db
"""

import argparse
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB = SCRIPT_DIR.parent / "backend" / "deepguard.db"

NEW_COLUMNS = [
    ("morphing_score",               "FLOAT"),
    ("boundary_discontinuity_score", "FLOAT"),
    ("lbp_entropy_score",            "FLOAT"),
    ("color_mismatch_score",         "FLOAT"),
]


def run_migration(db_path: Path) -> None:
    if not db_path.is_file():
        logger.warning("Database not found at %s — skipping migration (will be created fresh on first start).", db_path)
        return

    logger.info("Connecting to SQLite database: %s", db_path)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Fetch existing columns
    cursor.execute("PRAGMA table_info(analysis_results)")
    existing = {row[1] for row in cursor.fetchall()}

    added = 0
    for col_name, col_type in NEW_COLUMNS:
        if col_name in existing:
            logger.info("  Column already exists — skipping: %s", col_name)
        else:
            cursor.execute(f"ALTER TABLE analysis_results ADD COLUMN {col_name} {col_type}")
            logger.info("  Added column: %s %s", col_name, col_type)
            added += 1

    conn.commit()
    conn.close()

    if added:
        logger.info("Migration complete: %d column(s) added.", added)
    else:
        logger.info("Migration complete: database already up-to-date.")


def main():
    parser = argparse.ArgumentParser(description="DeepGuard AI v2 — DB migration for morphing score columns")
    parser.add_argument("--db-path", type=str, default=str(DEFAULT_DB),
                        help="Path to SQLite database (default: backend/deepguard.db)")
    args = parser.parse_args()

    run_migration(Path(args.db_path))


if __name__ == "__main__":
    main()
