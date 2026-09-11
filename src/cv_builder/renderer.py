from pathlib import Path
from typing import Dict, Any, List, Optional
from ..cv_builder.latex_escaper import create_latex_jinja_env


class CVRenderer:
    """Renders customized CVs to ModernCV .tex files using Jinja2."""

    def __init__(
        self,
        template_name: Optional[str] = None,
        template_dir: str = "templates",
        profile_path: str = "data/profile.yaml",
    ):
        if not template_name:
            import yaml
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    pdata = yaml.safe_load(f) or {}
                    template_name = pdata.get("cv_template", "moderncv_classic_blue.tex.j2")
            except Exception:
                template_name = "moderncv_classic_blue.tex.j2"

        self.template_name = template_name
        self.env = create_latex_jinja_env(template_dir=template_dir)
        self.template = self.env.get_template(template_name)

    def render(
        self,
        candidate: Dict[str, Any],
        education: List[Dict[str, Any]],
        experience: List[Dict[str, Any]],
        projects: List[Dict[str, Any]],
        cp: Dict[str, Any],
        certifications: List[str],
        output_file_path: str,
    ) -> str:
        """Renders LaTeX template with provided data and writes to output_file_path."""
        name_parts = candidate.get("name", "Candidate Name").split()
        first_name = name_parts[0] if name_parts else "Candidate"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        rendered_tex = self.template.render(
            candidate=candidate,
            first_name=first_name,
            last_name=last_name,
            education=education,
            experience=experience,
            projects=projects,
            cp=cp,
            certifications=certifications,
        )

        out_path = Path(output_file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(rendered_tex)

        return str(out_path)
