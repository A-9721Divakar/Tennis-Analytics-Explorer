"""Command-line ETL runner.

Examples
--------
    python run_etl.py                 # live Sportradar data (needs SPORTRADAR_API_KEY)
    python run_etl.py --use-cache     # re-load previously downloaded raw JSON (no API calls)
    python run_etl.py --demo          # fictional demo data, no API key required
    python run_etl.py --only rankings # refresh a single dataset
"""
import argparse
import logging
import sys

from src import database as db
from src import etl
from src.api_client import SportradarError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Load Sportradar tennis data into the SQL database.")
    parser.add_argument("--demo", action="store_true", help="load fictional demo data instead of calling the API")
    parser.add_argument("--use-cache", action="store_true", help="reuse raw JSON saved in data/raw")
    parser.add_argument("--only", nargs="+", choices=etl.DATASETS, help="run only these datasets")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    engine = db.get_engine()
    try:
        results = etl.run_etl(
            engine, datasets=args.only or etl.DATASETS, use_cache=args.use_cache, demo=args.demo,
            progress=lambda message: logging.info(message),
        )
    except SportradarError as exc:
        logging.error("%s", exc)
        return 2

    print("\nETL summary")
    print("-" * 60)
    for r in results:
        print(f"{r['dataset']:<14}{r['status']:<9}{r['message']}")
    print("-" * 60)
    print("Row counts:", db.table_counts(engine))
    return 0 if all(r["status"] == "success" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
