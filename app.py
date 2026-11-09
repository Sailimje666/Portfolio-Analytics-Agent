"""
Application entry point for Portfolio Analytics Agent.
Supports both Streamlit web interface and CLI diagnostic inspection.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.config import DatabaseConfig
from database.connection import DatabaseManager
from database.validator import DatabaseValidator


def run_cli_diagnostic():
    """CLI diagnostic view of the database status."""
    print("==================================================")
    print(" PL Capital Portfolio Analytics Agent - Diagnostic")
    print("==================================================")
    db = DatabaseManager()
    validator = DatabaseValidator(db_manager=db)
    report = validator.run_full_validation()

    print(f"Status: {report['status']}")
    print(f"Target Database: {db.db_path}")
    print("\nTables and Record Counts:")
    for tbl, count_info in report["record_counts"].items():
        print(f"  - {tbl:<25}: {count_info['db_count']:>5} rows (matches CSV: {count_info['matches']})")

    print("\nForeign Key Check:")
    print(f"  - Violations: {report['foreign_keys']['violations_count']}")
    print(f"  - Status: {report['foreign_keys']['status']}")
    print("\nDatabase is initialized and ready.")
    print("To launch the Streamlit web dashboard, run:")
    print("  streamlit run streamlit_app.py")


if __name__ == "__main__":
    # If run through streamlit (e.g. streamlit run app.py), forward to streamlit_app
    try:
        import streamlit as st
        # Detect if running inside Streamlit runtime
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx():
            import streamlit_app
        else:
            run_cli_diagnostic()
    except Exception:
        run_cli_diagnostic()
