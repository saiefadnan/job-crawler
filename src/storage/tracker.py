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

        # 1. Sync to Google Sheets via Webhook (if configured)
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

            webhook_resp = self._sync_to_webhook(payload)
            if webhook_resp.get("drive_link"):
                row["drive_link"] = webhook_resp["drive_link"]
            if webhook_resp.get("apply_status") == "GMAIL_DRAFT_CREATED":
                row["apply_status"] = "GMAIL_DRAFT_CREATED"

        # 2. Log locally to CSV (with drive_link populated from webhook if available)
        try:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers, extrasaction='ignore')
                writer.writerow(row)
        except Exception as e:
            print(f"[Warning] Failed to log job to CSV: {e}")

    def _sync_to_webhook(self, row: Dict[str, Any]) -> Dict[str, Any]:
        resp_data = {}
        try:
            resp = requests.post(self.webhook_url, json=row, timeout=15, allow_redirects=True)
            if resp.status_code in (200, 302):
                try:
                    resp_data = resp.json()
                except Exception:
                    pass
                msg = f"[Google Sheets] Synced '{row.get('company')} - {row.get('title')}' directly to Google Sheet!"
                if resp_data.get("drive_link"):
                    msg += f" (Drive: {resp_data.get('drive_link')})"
                elif resp_data.get("drive_error"):
                    msg += f" [Drive Warning: {resp_data.get('drive_error')} - please authorize DriveApp in Apps Script]"
                if resp_data.get("apply_status") == "GMAIL_DRAFT_CREATED":
                    msg += f" [Gmail Draft Created]"
                elif resp_data.get("gmail_error"):
                    msg += f" [Gmail Warning: {resp_data.get('gmail_error')}]"
                print(msg)
            else:
                print(f"[Google Sheets Warning] Webhook returned HTTP {resp.status_code}. Record safely preserved in local CSV.")
        except Exception as e:
            print(f"[Google Sheets Warning] Could not reach Webhook ({e}). Record safely preserved in local CSV.")
        return resp_data

    def prune_local_records(self, ttl_days: int = 30) -> int:
        """Prunes rows from applications.csv older than ttl_days."""
        if not os.path.exists(self.csv_path):
            return 0

        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=ttl_days)
        kept_rows = []
        purged_count = 0

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_val = row.get("date", "").strip()
                    row_dt = None
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
                        try:
                            row_dt = datetime.strptime(date_val, fmt)
                            break
                        except ValueError:
                            pass

                    if row_dt and row_dt < cutoff:
                        purged_count += 1
                    else:
                        kept_rows.append(row)

            if purged_count > 0:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.headers, extrasaction='ignore')
                    writer.writerow(dict(zip(self.headers, self.headers))) # Header row
                    writer.writerows(kept_rows)
                print(f"[Storage Prune] Purged {purged_count} CSV records older than {ttl_days} days. Remaining: {len(kept_rows)}")

        except Exception as e:
            print(f"[Warning] Error pruning CSV records: {e}")

        return purged_count

    def prune_local_files(self, output_dir: str = "output", ttl_days: int = 30) -> int:
        """Removes generated PDFs, TeX files, and email drafts older than ttl_days."""
        if not os.path.exists(output_dir):
            return 0

        from datetime import timedelta
        cutoff_ts = (datetime.now() - timedelta(days=ttl_days)).timestamp()
        purged_count = 0

        for root, _, files in os.walk(output_dir):
            for fname in files:
                if fname in ("pending_review.md", ".gitkeep"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    if os.path.getmtime(fpath) < cutoff_ts:
                        os.remove(fpath)
                        purged_count += 1
                except Exception as e:
                    print(f"[Warning] Could not remove expired file {fpath}: {e}")

        if purged_count > 0:
            print(f"[Storage Prune] Purged {purged_count} local files older than {ttl_days} days from {output_dir}/.")
        return purged_count

    def trigger_cloud_cleanup(self, ttl_days: int = 30) -> Optional[Dict[str, Any]]:
        """Invokes Google Apps Script to purge Google Drive CVs, Sheet rows, and Gmail drafts older than ttl_days."""
        if not self.webhook_url:
            return None
        try:
            payload = {"action": "cleanup", "ttl_days": ttl_days}
            resp = requests.post(self.webhook_url, json=payload, timeout=20, allow_redirects=True)
            if resp.status_code in (200, 302):
                data = resp.json() if resp.text else {}
                purged = data.get("purged", {})
                print(f"[Cloud Prune] Google Drive: -{purged.get('drive', 0)} files | Sheet: -{purged.get('sheet', 0)} rows | Gmail: -{purged.get('gmail', 0)} drafts.")
                return data
            else:
                print(f"[Cloud Prune Warning] Webhook returned status {resp.status_code}")
        except Exception as e:
            print(f"[Cloud Prune Warning] Could not trigger cloud cleanup: {e}")
        return None

    def prune_all(self, ttl_days: int = 30):
        """Unified 30-day cleanup across CSV records, local output files, and cloud storage."""
        self.prune_local_records(ttl_days=ttl_days)
        self.prune_local_files(ttl_days=ttl_days)
        if self.webhook_url:
            self.trigger_cloud_cleanup(ttl_days=ttl_days)