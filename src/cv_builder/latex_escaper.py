import jinja2

# Simple mapping of LaTeX characters to their escaped versions
LATEX_REPLACEMENTS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text: str) -> str:
    r"""Replaces characters like & and % with \& and \% so LaTeX doesn't crash."""
    if not text:
        return ""
    text = str(text)
    for char, escaped in LATEX_REPLACEMENTS.items():
        text = text.replace(char, escaped)
    return text


def create_latex_jinja_env(template_dir: str = "templates") -> jinja2.Environment:
    """Configures Jinja to use \\VAR{...} and \\BLOCK{...} to avoid LaTeX brace conflicts."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        block_start_string=r"\BLOCK{",
        block_end_string=r"}",
        variable_start_string=r"\VAR{",
        variable_end_string=r"}",
        comment_start_string=r"\%{",
        comment_end_string=r"}",
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["latex_escape"] = escape_latex
    return env
