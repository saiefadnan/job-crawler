import xml.etree.ElementTree as ET
from typing import List
from src.sourcing.base import BaseFetcher
from src.sourcing.models import Job


class WeWorkRemotelyFetcher(BaseFetcher):
    """
    Fetches remote programming jobs from We Work Remotely (WWR) RSS feed.
    All jobs are 100% remote.
    """

    RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

    def __init__(self, timeout: int = 15):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 JobCrawler/1.0"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        })

    def fetch_jobs(self, limit: int = 50) -> List[Job]:
        try:
            resp = self.session.get(self.RSS_URL, timeout=self.timeout)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            print(f"[Warning] Failed to fetch jobs from WeWorkRemotely: {e}")
            return []

        channel = root.find("channel")
        if channel is None:
            return []

        items = channel.findall("item")
        jobs: List[Job] = []

        for item in items:
            raw_title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            description = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            region = item.findtext("region", "Anywhere in the World").strip()

            if not raw_title or not link:
                continue

            # WWR titles are usually "Company Name: Job Title"
            if ":" in raw_title:
                parts = raw_title.split(":", 1)
                company = parts[0].strip()
                title = parts[1].strip()
            else:
                company = "WeWorkRemotely"
                title = raw_title

            job = Job(
                title=title,
                company=company,
                description=description,
                url=link,
                source="weworkremotely",
                created_at=pub_date,
                country=region if region else "Worldwide Remote",
                remote_option="Remote",
                tags=["Remote", "WWR"],
            )
            jobs.append(job)
            if len(jobs) >= limit:
                break

        print(f"Fetched {len(jobs)} remote programming jobs from WeWorkRemotely.")
        return jobs
