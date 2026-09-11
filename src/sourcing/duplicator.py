import json
import os
from datetime import datetime, timedelta
from typing import Dict, Set, List
from .models import Job


class Duplicator:
    """Manages deduplication cache with a self-cleaning 30-day rolling TTL window.
    
    Prevents cache bloat and allows reposted jobs to be naturally re-evaluated
    after 30 days.
    """

    def __init__(self, cache_file: str = "data/processed_cache.json", ttl_days: int = 30):
        self.cache_file = cache_file
        self.ttl_days = ttl_days
        self.cache: Dict[str, str] = self.load_cache()

    @property
    def seen_ids(self) -> Set[str]:
        """Set of all active job IDs."""
        return set(self.cache.keys())

    def load_cache(self) -> Dict[str, str]:
        """Loads active cache mapping job_id to date string."""
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                data = json.loads(content)
                if isinstance(data.get("entries"), dict):
                    return data["entries"]
                return {}
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            print("[Warning] Cache file was empty or corrupted. Re-initializing cache.")
            return {}
        except Exception as e:
            print(f"[Warning] Unexpected error reading cache: {e}. Starting with empty cache.")
            return {}

    def filter_new(self, jobs: List[Job]) -> List[Job]:
        """Filters out jobs that exist in active cache."""
        new_jobs = []
        for job in jobs:
            if job.id and job.id in self.cache:
                continue
            new_jobs.append(job)
        return new_jobs

    def prune_expired(self) -> int:
        """Removes entries older than ttl_days. Returns number of purged entries."""
        cutoff_date = (datetime.now() - timedelta(days=self.ttl_days)).strftime("%Y-%m-%d")
        initial_count = len(self.cache)
        self.cache = {job_id: date_str for job_id, date_str in self.cache.items() if date_str >= cutoff_date}
        purged_count = initial_count - len(self.cache)
        if purged_count > 0:
            print(f"[Cache Prune] Automatically purged {purged_count} entries older than {self.ttl_days} days. Active: {len(self.cache)}")
        return purged_count

    def commit(self, new_jobs: List[Job]):
        """Records new jobs with today's timestamp, prunes expired entries, and writes to disk."""
        today_str = datetime.now().strftime("%Y-%m-%d")

        for job in new_jobs:
            if job.id:
                self.cache[job.id] = today_str

        # Automatically prune old entries
        self.prune_expired()

        dir_name = os.path.dirname(self.cache_file)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": "2.0",
                    "ttl_days": self.ttl_days,
                    "total_active": len(self.cache),
                    "entries": self.cache,
                },
                f,
                indent=2,
            )
        
        
    
