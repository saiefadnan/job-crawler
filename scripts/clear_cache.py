#!/usr/bin/env python3
"""
Cache & Log Reset Utility for Job Search Crawler
Resets data/processed_cache.json, data/applications.csv, and output/
so that new users or new runs can start with a fresh, clean pipeline.
"""

import os
import sys
import csv
import json
import argparse
from pathlib import Path

# Ensure Windows terminal handles unicode gracefully
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CSV_HEADERS = [
    "date",
    "job_id",
    "company",
    "title",
    "score",
    "status",
    "url",
    "matched_keywords",
    "cv_path",
    "drive_link",
    "apply_method",
    "email_to",
    "email_subject",
    "email_body",
    "draft_path",
    "apply_status",
]


def clear_cache(cache_path: str = "data/processed_cache.json") -> bool:
    """Resets processed_cache.json to an empty active state."""
    p = Path(cache_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    initial_content = {
        "version": "2.0",
        "ttl_days": 30,
        "total_active": 0,
        "entries": {},
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(initial_content, f, indent=2)
    print(f"[OK] Reset cache: {cache_path} (0 active entries)")
    return True


def clear_applications_log(csv_path: str = "data/applications.csv") -> bool:
    """Resets applications.csv with only the standard header row."""
    p = Path(csv_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
    print(f"[OK] Reset application log: {csv_path} (header row preserved)")
    return True


def clear_output_artifacts(output_dir: str = "output") -> bool:
    """Deletes any temporary local files and drafts from output/ directory."""
    p = Path(output_dir)
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
        return True

    count = 0
    for item in p.rglob("*"):
        if item.is_file():
            try:
                item.unlink()
                count += 1
            except Exception as e:
                print(f"[Warning] Could not remove {item.name}: {e}")

    # Remove empty subdirectories in output/
    for sub in p.iterdir():
        if sub.is_dir():
            try:
                sub.rmdir()
            except Exception:
                pass

    print(f"[OK] Cleaned output directory: {output_dir} ({count} local files removed)")
    return True


def reset_all(
    cache_path: str = "data/processed_cache.json",
    csv_path: str = "data/applications.csv",
    output_dir: str = "output",
    cache_only: bool = False,
):
    print("\n=======================================================")
    print("      Autonomous Job Crawler: Cache Reset Tool         ")
    print("=======================================================\n")

    clear_cache(cache_path)

    if not cache_only:
        clear_applications_log(csv_path)
        clear_output_artifacts(output_dir)

    print("\n[SUCCESS] Pipeline state reset cleanly!")
    print("The job crawler is ready to evaluate all available jobs from scratch.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Reset deduplication cache and local application logs for the job crawler."
    )
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Only reset processed_cache.json without clearing applications.csv or output artifacts.",
    )
    parser.add_argument(
        "--cache-file",
        default="data/processed_cache.json",
        help="Path to processed_cache.json (default: data/processed_cache.json)",
    )
    parser.add_argument(
        "--csv-file",
        default="data/applications.csv",
        help="Path to applications.csv (default: data/applications.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Path to output directory (default: output)",
    )
    args = parser.parse_args()

    reset_all(
        cache_path=args.cache_file,
        csv_path=args.csv_file,
        output_dir=args.output_dir,
        cache_only=args.cache_only,
    )


if __name__ == "__main__":
    main()
