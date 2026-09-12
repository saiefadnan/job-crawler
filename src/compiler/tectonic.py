import os
import shutil
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TectonicCompiler:
    """Compiles .tex files to real .pdf documents using pdflatex or Tectonic.

    Multi-engine strategy:
    1. Tries pdflatex (fast, native font packages like fontawesome5/lmodern pre-installed).
    2. Tries Tectonic (modern Rust-based engine with on-the-fly package fetching).
    3. If neither engine is installed on the machine, falls back to a mock PDF for offline test suites.
    """

    def __init__(self):
        self.pdflatex_path = shutil.which("pdflatex")
        self.tectonic_path = shutil.which("tectonic")

    @property
    def is_latex_available(self) -> bool:
        return bool(self.pdflatex_path or self.tectonic_path)

    def _create_mock_pdf(self, pdf_path: Path) -> str:
        """Writes a minimal valid PDF binary for local pipeline testing without LaTeX."""
        mock_content = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"
        )
        with open(pdf_path, "wb") as f:
            f.write(mock_content)
        return str(pdf_path)

    def compile(self, tex_file_path: str, output_dir: str = "output") -> str:
        """Compiles a .tex file into a real .pdf and returns the output .pdf path."""
        tex_path = Path(tex_file_path).resolve()
        if not tex_path.exists():
            raise FileNotFoundError(f"LaTeX file not found at: {tex_path}")

        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_name = tex_path.stem + ".pdf"
        pdf_path = out_dir / pdf_name

        errors = []

        # 1. Primary Engine: pdflatex (Standard for Jake's & ModernCV with font packages)
        if self.pdflatex_path:
            try:
                cmd = [
                    self.pdflatex_path,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    f"-output-directory={out_dir}",
                    str(tex_path),
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(tex_path.parent),
                )
                if result.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 1000:
                    return str(pdf_path)

                err_snippet = result.stderr.strip() or result.stdout[-500:].strip()
                errors.append(f"pdflatex failed (exit code {result.returncode}): {err_snippet}")
            except Exception as e:
                errors.append(f"pdflatex execution error: {e}")

        # 2. Secondary Engine: Tectonic
        if self.tectonic_path:
            try:
                cmd = [self.tectonic_path, str(tex_path), "--outdir", str(out_dir)]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(tex_path.parent),
                )
                if result.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 1000:
                    return str(pdf_path)

                err_snippet = result.stderr.strip() or result.stdout[-500:].strip()
                errors.append(f"Tectonic failed (exit code {result.returncode}): {err_snippet}")
            except Exception as e:
                errors.append(f"Tectonic execution error: {e}")

        # If a compiler is installed but failed, report the exact errors
        if self.is_latex_available:
            for err in errors:
                print(f"[Compiler Warning] {err}")
            # Check if a partial or previous compilation succeeded
            if pdf_path.exists() and pdf_path.stat().st_size > 1000:
                return str(pdf_path)
            raise RuntimeError(
                f"LaTeX compilation failed for {tex_path.name}!\n" + "\n".join(errors)
            )

        # 3. Fallback for environments with NO LaTeX installed (e.g., bare dev machine testing)
        print(f"[Compiler Warning] No LaTeX engine (pdflatex/tectonic) found on system. Generating mock PDF for testing.")
        return self._create_mock_pdf(pdf_path)


if __name__ == "__main__":
    compiler = TectonicCompiler()
    print(f"LaTeX engine available: {compiler.is_latex_available}")
    if compiler.pdflatex_path:
        print(f"Found pdflatex at: {compiler.pdflatex_path}")
    if compiler.tectonic_path:
        print(f"Found Tectonic at: {compiler.tectonic_path}")
    if not compiler.is_latex_available:
        print("No LaTeX compiler found. Mock compiler will be used.")
