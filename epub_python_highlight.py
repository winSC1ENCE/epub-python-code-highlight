#!/usr/bin/env python3
"""
EPUB Python Syntax Highlighting (pre-baked, no JavaScript)
- Finds <pre><code class="language-python">...</code></pre> (and variants)
- Replaces code content with Pygments HTML spans
- Adds required CSS to an existing .css file (or creates one and links it)

Usage:
  python epub_python_highlight.py input.epub output.epub --style friendly
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter


PYTHON_HINT_RE = re.compile(
    r"""(
        class\s*=\s*["'][^"']*\b(language-python|python)\b[^"']*["']
        |
        data-language\s*=\s*["']python["']
        |
        data-lang\s*=\s*["']python["']
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Matches <pre ...><code ...> ... </code></pre> across lines
PRE_CODE_BLOCK_RE = re.compile(
    r"(?P<pre_open><pre\b[^>]*>)\s*(?P<code_open><code\b[^>]*>)"
    r"(?P<inner>.*?)"
    r"(?P<code_close></code>)\s*(?P<pre_close></pre>)",
    re.IGNORECASE | re.DOTALL,
)


def is_python_block(pre_open: str, code_open: str) -> bool:
    return bool(PYTHON_HINT_RE.search(pre_open) or PYTHON_HINT_RE.search(code_open))


def add_class_to_tag_open(tag_open: str, class_name: str) -> str:
    """Add class_name to existing class="" or create one."""
    if re.search(r'\bclass\s*=\s*["\']', tag_open, flags=re.IGNORECASE):
        return re.sub(
            r'(\bclass\s*=\s*["\'])([^"\']*)(["\'])',
            lambda m: m.group(1) + (m.group(2) + " " + class_name).strip() + m.group(3),
            tag_open,
            count=1,
            flags=re.IGNORECASE,
        )
    # insert before closing ">"
    return tag_open[:-1] + f' class="{class_name}">'


def choose_css_file(extracted_root: Path) -> Path | None:
    """
    Pick an existing CSS file to append pygments styles.
    Preference: style.css -> any .css
    """
    preferred = list(extracted_root.rglob("style.css"))
    if preferred:
        return preferred[0]
    css_files = list(extracted_root.rglob("*.css"))
    return css_files[0] if css_files else None


def ensure_css_link_in_xhtml(xhtml_path: Path, css_rel_href: str) -> None:
    """
    Ensure <link rel="stylesheet" href="..."> exists in <head>.
    Uses regex injection (EPUB XHTML is generally simple).
    """
    txt = xhtml_path.read_text(encoding="utf-8", errors="replace")
    if re.search(r'href\s*=\s*["\']' + re.escape(css_rel_href) + r'["\']', txt, re.IGNORECASE):
        return

    # Insert before </head>
    link_tag = f'<link rel="stylesheet" type="text/css" href="{css_rel_href}"/>'
    if "</head>" in txt.lower():
        txt = re.sub(r"</head>", link_tag + "\n</head>", txt, count=1, flags=re.IGNORECASE)
        xhtml_path.write_text(txt, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_epub", type=Path)
    ap.add_argument("output_epub", type=Path)
    ap.add_argument("--style", default="friendly", help="Pygments style (e.g. friendly, default, monokai)")
    args = ap.parse_args()

    if not args.input_epub.exists():
        raise SystemExit(f"Input not found: {args.input_epub}")

    workdir = Path(tempfile.mkdtemp(prefix="epub_highlight_"))
    try:
        # Extract
        with zipfile.ZipFile(args.input_epub, "r") as z:
            z.extractall(workdir)

        # Configure formatter + CSS
        formatter = HtmlFormatter(nowrap=True, style=args.style)
        pygments_css = HtmlFormatter(style=args.style).get_style_defs(".codehilite")

        marker = "/* PYGMENTS_SYNTAX_HIGHLIGHTING */"

        # Process XHTML/HTML files
        changed_files = 0
        changed_blocks = 0

        candidates = []
        for ext in ("*.xhtml", "*.html", "*.htm"):
            candidates.extend(workdir.rglob(ext))

        for fp in sorted(set(candidates)):
            txt = fp.read_text(encoding="utf-8", errors="replace")

            def repl(m: re.Match) -> str:
                nonlocal changed_blocks
                pre_open = m.group("pre_open")
                code_open = m.group("code_open")
                inner = m.group("inner")

                if not is_python_block(pre_open, code_open):
                    return m.group(0)

                # Skip if already highlighted
                if "<span" in inner and "class=" in inner:
                    return m.group(0)

                # Unescape HTML entities to get raw code text
                raw_code = html.unescape(inner)

                highlighted = highlight(raw_code, PythonLexer(), formatter)
                # Add codehilite class to <pre ...>
                pre_open2 = add_class_to_tag_open(pre_open, "codehilite")

                changed_blocks += 1
                return pre_open2 + code_open + highlighted + m.group("code_close") + m.group("pre_close")

            new_txt, n = PRE_CODE_BLOCK_RE.subn(repl, txt)
            if n > 0 and new_txt != txt:
                fp.write_text(new_txt, encoding="utf-8")
                changed_files += 1

        if changed_blocks == 0:
            print("No Python code blocks found (expected class='language-python' etc.).")
        else:
            # Add / append CSS
            css_file = choose_css_file(workdir)
            created_css = False

            if css_file is None:
                # Create a CSS file under OEBPS if possible, else root
                oebps = workdir / "OEBPStrans
                if not oebps.exists():
                    # try common folder
                    oebps = workdir / "OEBPS"
                target_dir = oebps if oebps.exists() else workdir
                css_file = target_dir / "pygments.css"
                css_file.write_text("", encoding="utf-8")
                created_css = True

            css_txt = css_file.read_text(encoding="utf-8", errors="replace")
            if marker not in css_txt:
                base_block = f"""
{marker}
/* Minimal, reader-friendly code block styling */
pre.codehilite {{
  padding: 0.8em;
  border-radius: 6px;
  border: 1px solid #d0d7de;
  background-color: #f6f8fa;
  white-space: pre-wrap;
  word-wrap: break-word;
}}
pre.codehilite code {{
  font-family: monospace;
}}
"""
                css_txt = css_txt + "\n" + base_block + "\n" + pygments_css + "\n"
                css_file.write_text(css_txt, encoding="utf-8")

            # If we created a new css file, link it from all changed xhtml files
            if created_css:
                # Create relative href to the XHTML folder is non-trivial; simplest:
                # place the css next to xhtml? We created it under OEBPS or root.
                # We'll try to link using a path relative to the common parent "OEBPS" if present.
                # If not, we link with just the filename (many readers resolve it if same dir).
                css_href = css_file.name
                # Better: if css under OEBPS, use "pygments.css"
                for fp in sorted(set(candidates)):
                    ensure_css_link_in_xhtml(fp, css_href)

        # Repack EPUB (mimetype must be first and stored)
        with zipfile.ZipFile(args.output_epub, "w") as z:
            mimetype_path = workdir / "mimetype"
            if mimetype_path.exists():
                z.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)

            for root, _, files in os.walk(workdir):
                for f in files:
                    full = Path(root) / f
                    rel = full.relative_to(workdir).as_posix()
                    if rel == "mimetype":
                        continue
                    z.write(full, rel, compress_type=zipfile.ZIP_DEFLATED)

        print(
            f"Done. Highlighted {changed_blocks} Python block(s) "
            f"in {changed_files} file(s) -> {args.output_epub}"
        )

    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
