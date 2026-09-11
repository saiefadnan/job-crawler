import csv
import os
from datetime import datetime
from typing import Dict, Any, Optional


class ApplicationTracker:
    def __init__(self, csv_path: str = 'data/applications.csv'):
        self.csv_path = csv_path
        self.headers = [
            "date",
            "job_id",
            "company",
            "title",
            "score",
            "status",
            "url",
            "matched_keywords",
            "cv_path",
            "apply_method",
            "email_to",
            "email_subject",
            "email_body",
            "draft_path",
            "apply_status",
        ]
        self.ensure_path()

    def ensure_path(self):
        dir_name = os.path.dirname(self.csv_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        if not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0:
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
            print(f"Successfully initialized new CSV log file: {self.csv_path}")

    def log_job(self, job_data: Dict[str, Any]):
        row = dict(job_data)

        # Auto-fill timestamp if not provided
        if not row.get("date"):
            row["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Format list of keywords into a readable comma-separated string
        if isinstance(row.get("matched_keywords"), list):
            row["matched_keywords"] = ", ".join(row["matched_keywords"])

        # Default apply_status if not provided
        if not row.get("apply_status"):
            row["apply_status"] = "PENDING_REVIEW" if row.get("status") == "QUALIFIED" else "N/A"

        try:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers, extrasaction='ignore')
                writer.writerow(row)
        except Exception as e:
            print(f"[Warning] Failed to log job to CSV: {e}")