import re
import yaml
from typing import List, Dict, Any, Optional, Set
from src.sourcing.models import Job


def match_keyword(keyword: str, text: str) -> bool:
    """Robust word-boundary search that handles special tech terms like c++, c#, node.js."""
    kw = keyword.strip().lower()
    target = text.lower()

    # If keyword has trailing symbols like 'c++' or 'c#' where \b fails:
    if kw.endswith("++") or kw.endswith("#"):
        pattern = r"(?:^|[\s,.(/])" + re.escape(kw) + r"(?:$|[\s,.)/:;?!])"
    else:
        # Standard word boundary with punctuation tolerance
        pattern = r"\b" + re.escape(kw) + r"\b"

    return bool(re.search(pattern, target))


class Matcher:
    """Scores Job objects against candidate profile defined in profile.yaml."""

    def __init__(self, profile_path: str = "data/profile.yaml"):
        self.profile_path = profile_path
        self.profile = self._load_profile()

        # Unpack profile config
        self.target_roles: List[str] = [r.lower() for r in self.profile.get("target_roles", [])]
        self.role_synonyms: Dict[str, List[str]] = self.profile.get("role_synonyms", {})
        self.primary_skills: Dict[str, float] = self.profile.get("skills", {}).get("primary", {})
        self.secondary_skills: Dict[str, float] = self.profile.get("skills", {}).get("secondary", {})
        self.negative_keywords: List[str] = [k.lower() for k in self.profile.get("negative_keywords", [])]

        # Weights & thresholds
        weights = self.profile.get("scoring_weights", {})
        self.w_title = float(weights.get("title", 0.35))
        self.w_skills = float(weights.get("skills", 0.50))
        self.w_synergy = float(weights.get("synergy", 0.15))

        thresholds = self.profile.get("thresholds", {})
        self.discard_below = float(thresholds.get("discard_below", 40.0))
        self.qualified_above = float(thresholds.get("qualified_above", 65.0))

        # Experience & Seniority filters
        exp_cfg = self.profile.get("experience_filter", {})
        self.max_years = int(exp_cfg.get("max_years", 1))
        self.target_seniority = [s.lower() for s in exp_cfg.get("target_seniority", [])]
        self.disallowed_seniority = [s.lower() for s in exp_cfg.get("disallowed_seniority", [])]

    def _load_profile(self) -> Dict[str, Any]:
        with open(self.profile_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def check_negative_filter(self, text: str) -> Optional[str]:
        """Returns the first matched negative keyword if found, else None."""
        for neg in self.negative_keywords:
            if match_keyword(neg, text):
                return neg
        return None

    def check_seniority_filter(self, title: str) -> Optional[str]:
        """Checks if title contains disallowed senior-level keywords."""
        title_lower = title.lower()
        for term in self.disallowed_seniority:
            if term in ("sr.", "sr"):
                if re.search(r"\b(?:sr\.|sr)\b", title_lower):
                    return term
            elif term in ("iii", "iv", "v"):
                if re.search(r"\b(?:iii|iv|v)\b", title_lower):
                    return f"Level {term.upper()}"
            elif match_keyword(term, title_lower):
                return term
        return None

    def check_experience_requirement(self, text: str) -> Optional[int]:
        """Extracts required experience years from description; returns years if > max_years."""
        cleaned = re.sub(
            r"(?:we have|our company has|in business for|established|founded)\s+\d+\+?\s*years",
            "",
            text,
            flags=re.IGNORECASE,
        )
        pattern = (
            r"(?:must have|should have|require[sd]?|minimum|at least|\b)\s*"
            r"(\d+)\+?\s*(?:to|-)?\s*\d*\s*years?(?:\s+of)?\s+"
            r"(?:relevant|professional|software|hands-on|industry|commercial|work|coding|development)?\s*experience"
        )
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        years = [int(m) for m in matches if m.isdigit()]
        if not years:
            return None
        min_required = min(years)
        if min_required > self.max_years:
            return min_required
        return None

    def check_target_seniority_bonus(self, title: str) -> bool:
        """Checks if title explicitly targets candidate level (junior, entry-level, graduate)."""
        title_lower = title.lower()
        for term in self.target_seniority:
            if match_keyword(term, title_lower):
                return True
        return False

    def calculate_title_score(self, title: str) -> float:
        """Scores job title against target roles, synonyms, and seniority bonus (0.0 to 1.0)."""
        title_lower = title.lower()
        base_score = 0.0

        # Exact target role match
        for role in self.target_roles:
            if match_keyword(role, title_lower):
                base_score = 1.0
                break

        # Check role synonyms if no exact match
        if base_score == 0.0:
            for _, synonyms in self.role_synonyms.items():
                for syn in synonyms:
                    if match_keyword(syn, title_lower):
                        base_score = 0.95
                        break
                if base_score > 0:
                    break

        # Partial token overlap if still 0
        if base_score == 0.0:
            title_tokens = set(re.findall(r"\b[a-z]{3,}\b", title_lower))
            role_tokens: Set[str] = set()
            for r in self.target_roles:
                role_tokens.update(re.findall(r"\b[a-z]{3,}\b", r))

            role_tokens -= {"developer", "engineer", "software"}
            if role_tokens:
                overlap = len(title_tokens.intersection(role_tokens))
                base_score = min(1.0, overlap * 0.4)

        # Apply target seniority bonus (+15% for junior/entry-level/graduate)
        if self.check_target_seniority_bonus(title):
            base_score = min(1.0, base_score + 0.15) if base_score > 0 else 0.70

        return base_score

    def calculate_skills_score(self, text: str, tags: List[str]) -> (float, List[str]):
        """Scores presence of primary skills in description & tags."""
        matched: List[str] = []
        matched_weight = 0.0

        tags_lower = [t.lower() for t in tags]

        for skill, weight in self.primary_skills.items():
            # Check either in tags or inside description/title
            if skill in tags_lower or match_keyword(skill, text):
                matched.append(skill)
                matched_weight += weight

        # Satiation model: matching 4-5 core skills gives near full 1.0 score
        # Target weight sum of 4.0 yields 1.0
        score = min(1.0, matched_weight / 4.0)
        return score, matched

    def calculate_synergy_score(self, text: str, tags: List[str]) -> (float, List[str]):
        """Scores presence of secondary/bonus technologies."""
        matched: List[str] = []
        tags_lower = [t.lower() for t in tags]

        for skill in self.secondary_skills.keys():
            if skill in tags_lower or match_keyword(skill, text):
                matched.append(skill)

        # 3 secondary skills achieve full 1.0 synergy
        score = min(1.0, len(matched) / 3.0)
        return score, matched

    def score_job(self, job: Job) -> Dict[str, Any]:
        """Calculates final score and gate decision for a single Job."""
        full_text = f"{job.title} {job.description}"

        # 1. Hard Gate: Negative Keywords
        hit_negative = self.check_negative_filter(full_text)
        if hit_negative:
            return {
                "job_id": job.id,
                "score": 0.0,
                "status": "DISCARDED",
                "reason": f"Disqualified by negative keyword: '{hit_negative}'",
                "matched_primary": [],
                "matched_synergy": [],
                "matched_keywords": [],
            }

        # 2. Hard Gate: Seniority Level in Title
        hit_seniority = self.check_seniority_filter(job.title)
        if hit_seniority:
            return {
                "job_id": job.id,
                "score": 0.0,
                "status": "DISCARDED",
                "reason": f"Disqualified by seniority in title: '{hit_seniority}' (target: junior/entry-level/fresh graduate)",
                "matched_primary": [],
                "matched_synergy": [],
                "matched_keywords": [],
            }

        # 3. Hard Gate: Experience Requirement
        required_exp = self.check_experience_requirement(full_text)
        if required_exp:
            return {
                "job_id": job.id,
                "score": 0.0,
                "status": "DISCARDED",
                "reason": f"Requires {required_exp}+ years of experience (target: max {self.max_years} year)",
                "matched_primary": [],
                "matched_synergy": [],
                "matched_keywords": [],
            }

        # 4. Component Scores
        title_score = self.calculate_title_score(job.title)
        skills_score, matched_primary = self.calculate_skills_score(full_text, job.tags)
        synergy_score, matched_synergy = self.calculate_synergy_score(full_text, job.tags)

        # 3. Final Weighted Score
        weighted = (
            (self.w_title * title_score)
            + (self.w_skills * skills_score)
            + (self.w_synergy * synergy_score)
        )
        final_score = round(weighted * 100.0, 2)

        # 4. Gate Decision
        if final_score >= self.qualified_above:
            status = "QUALIFIED"
        elif final_score >= self.discard_below:
            status = "SKIPPED_LOW_SCORE"
        else:
            status = "DISCARDED"

        all_matched = sorted(list(set(matched_primary + matched_synergy)))

        return {
            "job_id": job.id,
            "score": final_score,
            "status": status,
            "title_score": round(title_score * 100, 1),
            "skills_score": round(skills_score * 100, 1),
            "synergy_score": round(synergy_score * 100, 1),
            "matched_primary": matched_primary,
            "matched_synergy": matched_synergy,
            "matched_keywords": all_matched,
        }
