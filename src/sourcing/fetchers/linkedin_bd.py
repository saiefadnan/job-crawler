import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from src.sourcing.base import BaseFetcher
from src.sourcing.models import Job


class LinkedInBDFetcher(BaseFetcher):
    """
    Fetches real-time software engineering and developer job openings in Dhaka, Bangladesh
    using LinkedIn's public guest jobs endpoint (no auth or API keys required).
    """

    SEARCH_API_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOB_DETAILS_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

    TARGET_SEARCH_QUERIES = [
        "Software Engineer",
        "Full Stack Developer",
        "Frontend Developer",
        "Backend Developer",
        "React Developer",
        "Python Developer",
    ]

    def __init__(self, timeout: int = 15):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 JobCrawler/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def fetch_job_description(self, job_id: str) -> str:
        """Fetches full job description text for a specific LinkedIn job ID."""
        try:
            url = self.JOB_DETAILS_URL.format(job_id=job_id)
            resp = self.session.get(url, timeout=4)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                markup = soup.find("div", class_="show-more-less-html__markup")
                if markup:
                    return markup.get_text(separator=" ", strip=True)
        except Exception:
            pass
        return ""

    def fetch_jobs(self, limit: int = 50) -> List[Job]:
        jobs: List[Job] = []
        seen_ids = set()

        for query in self.TARGET_SEARCH_QUERIES:
            if len(jobs) >= limit:
                break

            params = {
                "keywords": query,
                "location": "Dhaka, Bangladesh",
                "f_E": "1,2",  # Internship, Entry level
                "start": 0,
            }

            try:
                resp = self.session.get(self.SEARCH_API_URL, params=params, timeout=self.timeout)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("li")

                for card in cards:
                    if len(jobs) >= limit:
                        break

                    title_el = card.find("h3", class_="base-search-card__title")
                    company_el = card.find("h4", class_="base-search-card__subtitle")
                    loc_el = card.find("span", class_="job-search-card__location")
                    link_el = card.find("a", class_="base-card__full-link")

                    if not title_el or not company_el or not link_el:
                        continue

                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True)
                    raw_url = link_el.get("href", "")
                    clean_url = raw_url.split("?")[0].strip()

                    # Extract numeric LinkedIn job ID from URL
                    id_match = re.search(r"-(\d+)(?:$|/)", clean_url)
                    job_id = id_match.group(1) if id_match else clean_url

                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    location_str = loc_el.get_text(strip=True) if loc_el else "Dhaka, Bangladesh"

                    # If title indicates senior/lead level, skip heavy description fetch
                    title_lower = title.lower()
                    is_senior = any(term in title_lower for term in ["senior", "sr.", "lead", "principal", "manager", "director", "head of", "vp", "architect"])
                    description = ""
                    if id_match and not is_senior:
                        description = self.fetch_job_description(id_match.group(1))

                    if not description:
                        description = f"{title} position at {company} located in {location_str}."

                    job = Job(
                        id=job_id,
                        title=title,
                        company=company,
                        description=description,
                        url=clean_url,
                        source="linkedin_bd",
                        country=location_str,
                        remote_option="On-site / Hybrid / Remote",
                        tags=["Dhaka", "Bangladesh", "Local"],
                    )
                    jobs.append(job)

            except Exception as e:
                print(f"[Warning] Failed to fetch LinkedIn BD jobs for '{query}': {e}")

        print(f"Fetched {len(jobs)} local jobs in Dhaka, Bangladesh from LinkedIn BD.")
        return jobs
