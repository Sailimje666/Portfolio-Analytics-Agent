"""
Main CLI entry point for the Portfolio Analytics Agent.
Supports pipeline operations (init, ingest, validate), interactive AI Agent orchestration,
and ground truth benchmark evaluation.
"""

import argparse
import sys
from pathlib import Path
from tabulate import tabulate

from database.config import DatabaseConfig, PROJECT_ROOT
from database.connection import DatabaseManager
from database.schema import initialize_schema
from database.ingestion import CSVIngestionService
from database.validator import DatabaseValidator
from database.logger import logger
from agent.portfolio_agent import PortfolioAgent, run_interactive_cli as run_agent_cli
from evaluation.evaluator import run_evaluation_cli


def run_pipeline(
    db_path: str = None,
    data_dir: str = None,
    schema_path: str = None,
    reset: bool = False,
    do_init: bool = True,
    do_ingest: bool = True,
    do_validate: bool = True
) -> bool:
    """
    Executes the database setup, ingestion, and validation pipeline.
    """
    print("\n" + "=" * 70)
    print(" PL CAPITAL - AI PORTFOLIO ANALYTICS AGENT")
    print(" Database Initialization, CSV Ingestion & Validation Pipeline")
    print("=" * 70 + "\n")

    db_manager = DatabaseManager(db_path=db_path)
    logger.info(f"Target Database: {db_manager.db_path}")

    # Step 1: Foreign Keys Verification
    fk_enabled = db_manager.is_foreign_keys_enabled()
    print(f"[*] SQLite PRAGMA foreign_keys: {'ENABLED [OK]' if fk_enabled else 'DISABLED [FAIL]'}")
    if not fk_enabled:
        logger.error("Foreign key constraints are not enabled.")
        return False

    # Step 2: Schema Initialization
    if do_init or reset:
        print("\n--- Step 1: Initializing Database Schema ---")
        try:
            created_tables = initialize_schema(
                db_manager=db_manager,
                schema_path=schema_path,
                drop_existing=reset
            )
            print(f"[OK] Database schema initialized successfully.")
            print(f"     Tables verified ({len(created_tables)}): {', '.join(created_tables)}")
        except Exception as e:
            print(f"[ERROR] Schema initialization failed: {e}")
            logger.exception("Schema initialization failed")
            return False

    # Step 3: CSV Ingestion
    if do_ingest:
        print("\n--- Step 2: Ingesting Assessment CSV Datasets ---")
        ingestion_service = CSVIngestionService(
            db_manager=db_manager,
            data_dir=data_dir
        )
        try:
            results = ingestion_service.ingest_all()
            table_data = []
            total_read = 0
            total_inserted = 0
            total_skipped = 0
            total_in_db = 0

            for tbl, stats in results.items():
                total_read += stats["read"]
                total_inserted += stats["inserted"]
                total_skipped += stats["skipped"]
                total_in_db += stats["total_in_db"]
                table_data.append([
                    tbl,
                    stats["read"],
                    stats["inserted"],
                    stats["skipped"],
                    stats["total_in_db"],
                    "OK"
                ])

            print(tabulate(
                table_data,
                headers=["Table Name", "CSV Rows", "Inserted", "Skipped (Dup)", "Total in DB", "Status"],
                tablefmt="github"
            ))
            print(f"\n[OK] CSV Ingestion completed: {total_read} read, {total_inserted} new inserted, "
                  f"{total_skipped} skipped, {total_in_db} total records in database.")

        except Exception as e:
            print(f"[ERROR] CSV ingestion failed: {e}")
            logger.exception("CSV ingestion failed")
            return False

    # Step 4: Database Validation
    if do_validate:
        print("\n--- Step 3: Validating Database Integrity & Constraints ---")
        validator = DatabaseValidator(db_manager=db_manager, data_dir=data_dir)
        report = validator.run_full_validation()

        # Print validation summary
        print(f"Overall Validation Status: {report['status']}")

        # Foreign Key check
        fk_stat = report["foreign_keys"]["status"]
        fk_viols = report["foreign_keys"]["violations_count"]
        print(f"  - Foreign Key Check: {fk_stat} ({fk_viols} violations)")

        # Record Counts
        rc_matches = all(v["matches"] for v in report["record_counts"].values())
        print(f"  - Record Count Verification: {'PASS [All 9 match]' if rc_matches else 'FAIL'}")

        # Primary Key check
        pk_matches = all(v["valid"] for v in report["primary_keys"].values())
        print(f"  - Primary Key Uniqueness & Non-null: {'PASS [All 9 valid]' if pk_matches else 'FAIL'}")

        # NULL Constraints check
        nc_matches = report["null_constraints"].get("valid", False)
        print(f"  - Asset Type NULL Rules (Bonds/Stocks): {'PASS [Compliant]' if nc_matches else 'FAIL'}")

        if report["status"] != "PASS":
            print("\nValidation Errors encountered:")
            for err in report["errors"]:
                print(f"  [X] {err}")
            return False

    print("\n" + "=" * 70)
    print(" [SUCCESS] Pipeline Execution Complete.")
    print("=" * 70 + "\n")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="PL Capital Portfolio Analytics Agent CLI"
    )
    parser.add_argument(
        "--agent", "-a",
        action="store_true",
        help="Launch interactive AI Portfolio Agent command-line interface"
    )
    parser.add_argument(
        "--ask",
        type=str,
        default=None,
        help="Ask a single question directly through the Portfolio Agent"
    )
    parser.add_argument(
        "--evaluate", "-e",
        action="store_true",
        help="Execute ground truth evaluation benchmark across all 10 questions"
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["mock", "offline", "live"],
        default="mock",
        help="Benchmark evaluation mode: 'mock' (default) or 'live'"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize database schema only"
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Ingest CSV datasets only"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run database validation only"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all existing tables and re-initialize from scratch"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Custom SQLite database file path"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Custom directory containing CSV datasets"
    )

    args = parser.parse_args()

    # Route based on flags
    if args.evaluate:
        run_evaluation_cli(mode=args.mode)
        sys.exit(0)

    if args.agent:
        run_agent_cli()
        sys.exit(0)

    if args.ask:
        agent = PortfolioAgent()
        res = agent.answer_question(args.ask)
        print("\n" + "=" * 70)
        print(f" Question:      {args.ask}")
        print(f" Selected Tool: {res['selected_tool'].upper()}")
        print(f" Status:        {res['status'].upper()}")
        print("-" * 70)
        print(res["answer"])
        print("=" * 70 + "\n")
        sys.exit(0 if res["status"] == "success" else 1)

    if args.init and not (args.ingest or args.validate):
        success = run_pipeline(
            db_path=args.db,
            data_dir=args.data_dir,
            reset=args.reset,
            do_init=True,
            do_ingest=False,
            do_validate=False
        )
    elif args.ingest and not (args.init or args.validate):
        success = run_pipeline(
            db_path=args.db,
            data_dir=args.data_dir,
            reset=False,
            do_init=False,
            do_ingest=True,
            do_validate=False
        )
    elif args.validate and not (args.init or args.ingest):
        success = run_pipeline(
            db_path=args.db,
            data_dir=args.data_dir,
            reset=False,
            do_init=False,
            do_ingest=False,
            do_validate=True
        )
    else:
        # Default: run entire pipeline
        success = run_pipeline(
            db_path=args.db,
            data_dir=args.data_dir,
            reset=args.reset,
            do_init=True,
            do_ingest=True,
            do_validate=True
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
