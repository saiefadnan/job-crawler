import sys
from pathlib import Path

# Ensure project root is in sys.path when running script directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.sourcing.base import BaseFetcher
from src.sourcing.models import Job


class JobicyFetcher(BaseFetcher):
    API_URL = "https://jobicy.com/api/v2/remote-jobs"

    def fetch_jobs(self, limit: int= 10)-> list[Job]:
        response = self.session.get(self.API_URL, timeout=self.timeout);
        response.raise_for_status()
        jobs_data = response.json()
        items = jobs_data.get("jobs", [])
        jobs = []
        for data in items:
            job = Job(
                title=data.get("jobTitle", ""),
                company=data.get("companyName", ""),
                description=data.get("jobDescription", ""),
                url=data.get("url", ""),
                source="jobicy",
                created_at=data.get("pubDate"),
                country=data.get("jobGeo", "Worldwide"),
                remote_option="Remote",
                tags=data.get("jobIndustry", []) if isinstance(data.get("jobIndustry"), list) else [],
            )
            jobs.append(job)
            if len(jobs) >= limit:
                break

        print(f"Fetched {len(jobs)} jobs from Jobicy.")
        return jobs
