from .models import Job
import abc
import requests

class BaseFetcher(abc.ABC):
    def __init__(self, timeout: int =15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "JobSearchPipeline/1.0"
        })
    @abc.abstractmethod
    def fetch_jobs(self, limit: int =50) -> list[Job]:
        pass