"""
Database initialization and migration utility for NutriRisk AI.

Usage:
    python init_db.py           # Initializes DB, applies safe migrations, seeds metadata
    python init_db.py --status  # Displays schema status and row counts
"""
import sys
import os
import argparse
import sqlite3
from nutririsk import create_app
from nutririsk.db import safe_migrate, get_active_model_metadata

def print_status(db_path: str):
    """Prints current database schema summary, indexes, and row counts."""
    if not os.path.exists(db_path):
        print(f"[!] Database file does not exist at: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 65)
    print(f"NutriRisk AI Database Status: {db_path}")
    print("=" * 65)

    tables = ["users", "assessments", "model_metadata", "admin_audit_logs"]
    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
        if not cursor.fetchone():
            print(f"[-] Table '{table}': MISSING")
            continue

        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]

        cursor.execute(f"PRAGMA table_info({table});")
        cols = [f"{row['name']} ({row['type']})" for row in cursor.fetchall()]

        print(f"[+] Table '{table}': {count} records")
        print(f"    Columns: {', '.join(cols)}")

    print("-" * 65)
    print("Database Indexes:")
    cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_autoindex%';")
    indexes = cursor.fetchall()
    for idx in indexes:
        print(f"  * {idx['name']} on {idx['tbl_name']}")

    cursor.execute("SELECT model_name, artifact_version, training_date FROM model_metadata WHERE is_active = 1 LIMIT 1;")
    active_model = cursor.fetchone()
    if active_model:
        print("-" * 65)
        print(f"Active Model: {active_model['model_name']} ({active_model['artifact_version']}) trained on {active_model['training_date']}")

    print("=" * 65)
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="NutriRisk AI Database CLI Tool")
    parser.add_argument("--status", action="store_true", help="Print database schema and record counts without modifying")
    args = parser.parse_args()

    app = create_app()
    db_path = app.config.get("DATABASE_PATH", "nutririsk.db")

    if args.status:
        print_status(db_path)
        return

    print("=" * 65)
    print("Initializing NutriRisk AI Database & Applying Safe Migrations...")
    print("=" * 65)

    with app.app_context():
        # create_app() already invokes init_db(app) during creation
        print_status(db_path)
        print("\n[OK] Database successfully initialized and migrated.")

if __name__ == "__main__":
    main()
