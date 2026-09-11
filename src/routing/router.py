import re
import yaml
from pathlib import Path
from typing import Dict, Any


class ApplicationRouter:
    def __init__(self, output_dir: str = "output", profile_path: str = "data/profile.yaml"):
        self.output_dir = Path(output_dir)
        self.drafts_dir = self.output_dir / "email_drafts"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.digest_file = self.output_dir / "pending_review.md"
        self.profile = self._load_profile(profile_path)
        self.candidate = self.profile.get("candidate", {})

    def _load_profile(self, profile_path: str) -> Dict[str, Any]:
        p = Path(profile_path)
        if not p.is_absolute():
            for parent in [Path.cwd(), Path(__file__).resolve().parent.parent.parent]:
                cand = parent / profile_path
                if cand.exists():
                    p = cand
                    break
        try:
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def route(self, job_data: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
        """Routes a qualified job into either an Email draft or ATS queue."""
        url = job_data.get("url", "")

        # Detect if application link is an email address
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", url)

        if email_match:
            email = email_match.group(0)
            return self._handle_email_route(job_data, email, pdf_path)
        else:
            return self._handle_ats_route(job_data, pdf_path)

    def _handle_email_route(self, job_data: Dict[str, Any], email: str, pdf_path: str) -> Dict[str, Any]:
        company = job_data.get("company", "Hiring Team")
        title = job_data.get("title", "Software Engineer")
        skills = ", ".join(job_data.get("matched_keywords", [])[:4]) or "Software Development"

        cand_name = self.candidate.get("name", "Applicant")
        cand_email = self.candidate.get("email", "")
        cand_phone = self.candidate.get("phone", "")
        cand_github = self.candidate.get("github", "")
        cand_linkedin = self.candidate.get("linkedin", "")
        edu = self.candidate.get("education", {})
        degree = edu.get("degree", "Computer Science and Engineering")
        institution = edu.get("institution", "")
        cgpa = edu.get("cgpa", "")

        edu_details = f"a {degree}" + (f" from {institution}" if institution else "") + (f" (CGPA {cgpa})" if cgpa else "")
        subject = f"Application for {title} - {cand_name}"

        safe_name = "".join(c for c in f"{company}_{title}" if c.isalnum() or c in ('_', '-'))[:40]
        draft_file = self.drafts_dir / f"{safe_name}_email.txt"

        github_link = f"https://{cand_github.replace('https://', '')}" if cand_github else ""
        linkedin_link = f"https://{cand_linkedin.replace('https://', '')}" if cand_linkedin else ""

        body = (
            f"Dear Hiring Team at {company},\n\n"
            f"I am writing to express my strong interest in the {title} role. With hands-on experience "
            f"in {skills}, {edu_details}, I am confident in my ability to contribute effectively to your engineering team.\n\n"
            f"I have attached my tailored CV for your review."
            + (f" You can also explore my projects and code at {github_link}\n\n" if github_link else "\n\n")
            + f"Thank you for your time and consideration. I look forward to hearing from you.\n\n"
            f"Best regards,\n"
            f"{cand_name}\n"
            + (f"{cand_email}" if cand_email else "")
            + (f" | {cand_phone}\n" if cand_phone else "\n")
            + (f"GitHub: {github_link}\n" if github_link else "")
            + (f"LinkedIn: {linkedin_link}\n" if linkedin_link else "")
        )

        with open(draft_file, "w", encoding="utf-8") as f:
            f.write(f"TO: {email}\nSUBJECT: {subject}\nATTACHMENT: {pdf_path}\n{'='*60}\n\n{body}")

        print(f"Created email draft at: {draft_file}")

        return {
            "apply_method": "email",
            "email_to": email,
            "email_subject": subject,
            "email_body": body,
            "apply_status": "EMAIL_DRAFTED",
            "draft_path": str(draft_file),
        }

    def _handle_ats_route(self, job_data: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
        company = job_data.get("company", "Unknown")
        title = job_data.get("title", "Role")
        score = job_data.get("score", 0)
        url = job_data.get("url", "#")

        # Append to pending_review.md digest
        if not self.digest_file.exists() or self.digest_file.stat().st_size == 0:
            with open(self.digest_file, "w", encoding="utf-8") as f:
                f.write("# Pending ATS Applications Review Queue\n\n")
                f.write("| Company | Role | Match Score | Apply Link | Tailored CV PDF |\n")
                f.write("| :--- | :--- | :---: | :--- | :--- |\n")

        with open(self.digest_file, "a", encoding="utf-8") as f:
            f.write(f"| **{company}** | {title} | {score}% | [Apply Here]({url}) | `{pdf_path}` |\n")

        print(f"Queued for ATS review in: {self.digest_file}")

        return {
            "apply_method": "ats",
            "email_to": "",
            "email_subject": "",
            "email_body": "",
            "apply_status": "ATS_PENDING_REVIEW",
            "draft_path": "",
        }
