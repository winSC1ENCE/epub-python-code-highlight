.PHONY: install run

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
STYLE ?= friendly

install:
	$(PIP) install -e .

run:
	$(PYTHON) epub_python_highlight.py $(INPUT) $(OUTPUT) --style $(STYLE)
