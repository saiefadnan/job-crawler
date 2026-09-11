
from ..duplicator import Duplicator
from ..base import BaseFetcher
from ..models import Job

class JobicyFetcher(BaseFetcher):
    API_URL = "https://jobicy.com/api/v2/remote-jobs"

    def fetch_jobs(self, limit: int= 50)-> list[Job]:
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
                country=data.get("jobGeo"),
                tags=data.get("jobIndustry", []) if isinstance(data.get("jobIndustry"), list) else [],
            )
            jobs.append(job)
            if len(jobs) >= limit:
                break

        print(f"Fetched {len(jobs)} jobs from Jobicy.")
        return jobs


if __name__ == '__main__':
    fetcher = JobicyFetcher()
    results = fetcher.fetch_jobs(limit=10)
    
    duplicator = Duplicator()

    new_jobs = duplicator.filter_new(results)
    duplicator.commit(new_jobs)

    print(f"Found {len(new_jobs)} new jobs.")
    for j in new_jobs:
        print(f"[{j.id}] {j.title} @ {j.company} ({j.url})")
        