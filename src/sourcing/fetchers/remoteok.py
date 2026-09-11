import sys
from pathlib import Path
from typing import List

# Ensure project root is in sys.path when running script directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.sourcing.base import BaseFetcher
from src.sourcing.models import Job


class RemoteOKFetcher(BaseFetcher):
    API_URL = "https://remoteok.com/api"

    def __init__(self, timeout: int = 15):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 JobCrawler/1.0",
            "Accept": "application/json",
        })

    def fetch_jobs(self, limit: int = 100) -> List[Job]:
        try:
            response = self.session.get(self.API_URL, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[Warning] Failed to fetch jobs from RemoteOK: {e}")
            return []

        # First item in RemoteOK response is always API metadata/disclaimer
        items = data[1:] if isinstance(data, list) and len(data) > 1 else []
        jobs = []

        for item in items:
            if not isinstance(item, dict):
                continue

            title = item.get("position", "").strip()
            company = item.get("company", "").strip()
            apply_url = item.get("apply_url") or item.get("url") or ""

            if not title or not company:
                continue

            job = Job(
                title=title,
                company=company,
                description=item.get("description", ""),
                url=apply_url,
                source="remoteok",
                created_at=str(item.get("date", "")),
                country=item.get("location", "Remote"),
                tags=item.get("tags", []) if isinstance(item.get("tags"), list) else [],
            )
            jobs.append(job)
            if len(jobs) >= limit:
                break

        print(f"Fetched {len(jobs)} jobs from RemoteOK.")
        return jobs
