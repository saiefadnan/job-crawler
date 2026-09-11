import csv
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class ApplicationTracker:
    def __init__(self, csv_path: str = 'data/applications.csv', webhook_url: Optional[str] = None):
        self.csv_path = csv_path
        self.webhook_url = webhook_url if webhook_url is not None else os.getenv("GOOGLE_SHEET_WEBHOOK_URL")
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
            "drive_link",
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

        # 1. Log locally to CSV
        try:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers, extrasaction='ignore')
                writer.writerow(row)
        except Exception as e:
            print(f"[Warning] Failed to log job to CSV: {e}")

        # 2. Sync to Google Sheets via Webhook (if configured)
        if self.webhook_url:
            payload = dict(row)
            cv_path = payload.get("cv_path")
            if cv_path and os.path.exists(cv_path):
                try:
                    import base64
                    with open(cv_path, "rb") as f:
                        payload["pdf_base64"] = base64.b64encode(f.read()).decode("utf-8")
                    payload["cv_filename"] = os.path.basename(cv_path)
                except Exception as e:
                    print(f"[Warning] Failed to encode PDF for cloud sync: {e}")

            self._sync_to_webhook(payload)

    def _sync_to_webhook(self, row: Dict[str, Any]):
        try:
            resp = requests.post(self.webhook_url, json=row, timeout=15, allow_redirects=True)
            if resp.status_code in (200, 302):
                data = {}
                try:
                    data = resp.json()
                except Exception:
                    pass
                msg = f"[Google Sheets] Synced '{row.get('company')} - {row.get('title')}' directly to Google Sheet!"
                if data.get("drive_link"):
                    msg += f" (Drive: {data.get('drive_link')})"
                if data.get("apply_status") == "GMAIL_DRAFT_CREATED":
                    msg += f" [Gmail Draft Created]"
                print(msg)
            else:
                print(f"[Google Sheets Warning] Webhook returned status code {resp.status_code}")
        except Exception as e:
            print(f"[Google Sheets Warning] Failed to reach Google Sheet Webhook: {e}")