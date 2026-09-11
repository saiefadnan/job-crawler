from typing import Optional, List
import hashlib
from pydantic import BaseModel, Field, model_validator

class Job(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    position: Optional[str] = None
    company: str
    created_at: Optional[str] = None
    url: str
    source: str  # e.g. "remoteok", "arbeitnow", "hackernews"
    apply_method: str = "unknown"  # "email", "ats", "unknown"
    apply_target: Optional[str] = None  # direct email or application URL
    salary_range: Optional[str] = None
    status: Optional[str] = "NEW"
    address: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    remote_option: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def generate_job_id(cls, data: dict)->dict:
        if isinstance(data, dict) and not data.get("id"):
            title = data.get("title", "").lower().strip()
            company = data.get("company", "").lower().strip()
            url = data.get("url", "").split("?")[0].lower().strip()
            raw_key = f"{title}|{company}|{url}"
            data["id"] = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
        return data
