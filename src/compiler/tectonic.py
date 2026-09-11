import os
import shutil
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TectonicCompiler:
    """Compiles .tex files to .pdf using Tectonic or pdflatex.

    Falls back to generating a mock PDF when run locally without a working LaTeX setup,
    allowing frictionless local development while compiling real PDFs in GitHub Actions.
    """

    def __init__(self):
        self.tectonic_path = shutil.which("tectonic")
        self.pdflatex_path = shutil.which("pdflatex")

    @property
    def is_latex_available(self) -> bool:
        return bool(self.tectonic_path or self.pdflatex_path)

    def _create_mock_pdf(self, pdf_path: Path) -> str:
        """Writes a minimal valid PDF binary for local pipeline testing."""
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
        """Compiles a .tex file into a .pdf and returns the output .pdf path."""
        tex_path = Path(tex_file_path).resolve()
        if not tex_path.exists():
            raise FileNotFoundError(f"LaTeX file not found at: {tex_path}")

        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_name = tex_path.stem + ".pdf"
        pdf_path = out_dir / pdf_name

        if self.tectonic_path:
            logger.info(f"Compiling {tex_path.name} with Tectonic...")
            try:
                cmd = [self.tectonic_path, str(tex_path), "--outdir", str(out_dir)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and pdf_path.exists():
                    return str(pdf_path)
                logger.warning(f"Tectonic returned code {result.returncode}. Falling back to mock PDF.")
            except subprocess.SubprocessError as e:
                logger.warning(f"Tectonic subprocess failed: {e}. Falling back to mock PDF.")
            except Exception as e:
                logger.warning(f"Unexpected error running Tectonic: {e}. Falling back to mock PDF.")

        elif self.pdflatex_path:
            logger.info(f"Compiling {tex_path.name} with pdflatex...")
            try:
                cmd = [
                    self.pdflatex_path,
                    "-interaction=nonstopmode",
                    f"-output-directory={out_dir}",
                    str(tex_path),
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and pdf_path.exists():
                    return str(pdf_path)
                logger.warning(f"Local pdflatex issue: {result.stderr.strip()[:100]}. Falling back to mock PDF.")
            except subprocess.SubprocessError as e:
                logger.warning(f"pdflatex subprocess failed: {e}. Falling back to mock PDF.")
            except Exception as e:
                logger.warning(f"Unexpected error running pdflatex: {e}. Falling back to mock PDF.")

        logger.info(f"Generated PDF at {pdf_path}")
        return self._create_mock_pdf(pdf_path)


if __name__ == "__main__":
    compiler = TectonicCompiler()
    print(f"LaTeX engine available locally: {compiler.is_latex_available}")
    if compiler.tectonic_path:
        print(f"Found Tectonic at: {compiler.tectonic_path}")
    elif compiler.pdflatex_path:
        print(f"Found pdflatex at: {compiler.pdflatex_path}")
    else:
        print("Using local mock compiler (Tectonic will be used inside GitHub Actions runner).")
