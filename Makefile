.PHONY: help install clean data pipeline run run-fast run-bonus test lint format

VENV = .geovenv
PYTHON = $(VENV)/Scripts/python
PIP = $(VENV)/Scripts/pip

help:
	@echo "GeoGeometric Project - Available Commands:"
	@echo "  make install  - Install Python dependencies"
	@echo "  make data     - Download and preprocess all datasets"
	@echo "  make run      - Run the complete execution pipeline"
	@echo "  make run-fast - Run the pipeline in draft mode (150 DPI)"
	@echo "  make run-bonus- Run only the bonus features"
	@echo "  make format   - Format code using Black"
	@echo "  make lint     - Check code quality with flake8"
	@echo "  make test     - Run pytest unit tests"
	@echo "  make clean    - Remove cached files and pycache"

install:
	$(PIP) install -r requirements.txt

data:
	$(PYTHON) scripts/utils/data_loader.py
	$(PYTHON) scripts/utils/preprocess.py

run:
	$(PYTHON) run_all.py

run-fast:
	$(PYTHON) run_all.py --draft

run-bonus:
	$(PYTHON) run_all.py --bonus --skip-download --skip-preprocess

format:
	$(PYTHON) -m black scripts/ tests/ run_all.py

lint:
	$(PYTHON) -m flake8 scripts/ tests/ run_all.py

test:
	$(PYTHON) -m pytest tests/

clean:
	$(PYTHON) -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
	$(PYTHON) -c "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"
