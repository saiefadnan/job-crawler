import json
from .models import Job
import os 

class Duplicator:
    def __init__(self, cache_file: str = 'data/processed_cache.json'):
        self.cache_file = cache_file
        self.seen_ids = self.load_cache()
    
    def load_cache(self) -> set[str]:
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get("seen_ids", []))
        except FileNotFoundError:
            return set()
        
    def filter_new(self, jobs: list[Job]) -> list[Job]:
        new_jobs = []
        for job in jobs:
            if job.id in self.seen_ids:
                continue
            new_jobs.append(job)
        return new_jobs
    
    def commit(self, new_jobs: list[Job]):
        for job in new_jobs:
            if job.id:
                self.seen_ids.add(job.id)
       
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump({"seen_ids": list(self.seen_ids)}, f, indent=2)
        
        
    
