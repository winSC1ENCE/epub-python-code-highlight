# Epub "Python Code Highlight" Tool

Small CLI tool to highlight Python code blocks in EPUB files using Pygments.

## Requirements
- Python 3.8+
- Pygments (installed via `pyproject.toml`)

## Install
```bash
python3 -m pip install -e .
```

## Usage
```bash
python3 epub_python_highlight.py input.epub output.epub --style friendly
```

## Makefile helpers
```bash
make install
make run INPUT=input.epub OUTPUT=output.epub STYLE=friendly
```

## CLI entrypoint (optional)
After `make install`, you can also run:
```bash
epub-python-highlight input.epub output.epub --style friendly
```
