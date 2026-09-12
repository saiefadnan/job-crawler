import yaml
from typing import Dict, Any

class Selector:
    def __init__(self, bank_path: str = 'data/bullet_bank.yaml'):
        self.bank_path = bank_path
        self.bank: Dict[str, Any] = self.load_bank()
        self.verified_texts = {
            b["text"] for proj in self.bank.get("projects", []) for b in proj.get("bullets",[])
        }

    def load_bank(self) -> Dict[str, Any]:
        try:
            with open(self.bank_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                return content if isinstance(content, dict) else {}
        except FileNotFoundError:
            print(f"[Warning] Bullet bank file not found at '{self.bank_path}'.")
            return {}
        except yaml.YAMLError as e:
            print(f"[Warning] Bullet bank YAML parsing error: {e}.")
            return {}
        except Exception as e:
            print(f"[Warning] Unexpected error reading bullet bank: {e}.")
            return {}

    def select_for_job(self, matched_keywords: list[str]) -> dict:
        kw = {k.lower() for k in matched_keywords}
        scored_projects = []
        for project in self.bank.get("projects", []):
            scored_bullets = []
            for bullet in project.get("bullets", []):
                tags_set = {tag.lower() for tag in bullet["tags"]}
                score = len(tags_set & kw)
                scored_bullets.append((score, bullet))

            scored_bullets.sort(key=lambda x: x[0], reverse=True)
            total_project_score = sum(score for score, _ in scored_bullets)
            best_bullets = [b for _,b in scored_bullets[:2]]

            scored_projects.append((total_project_score, {
                "name": project["name"],
                "bullets": best_bullets,
                "tech_stack": project["tech_stack"],
                "github": project.get("github", ""),
            }))

        scored_projects.sort(key=lambda x: x[0], reverse=True)

        top_projects = [p for _, p in scored_projects[:3]]

        for p in top_projects:
            for b in p["bullets"]:
                assert b["text"] in self.verified_texts,  f"IMMUTABILITY VIOLATION in {p['name']}!"

        return {
            "candidate": self.bank.get("candidate", {}),
            "education": self.bank.get("education", []),
            "experience": self.bank.get("experience", []),
            "projects": top_projects,
            "cp": self.bank.get("competitive_programming", {}),
            "certifications": self.bank.get("certifications", []),
        }