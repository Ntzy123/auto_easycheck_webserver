# ============================================================================
# Makefile - auto-easycheck-webserver
# Cross-platform (Windows / Linux / macOS)
# ============================================================================

ifeq ($(OS),Windows_NT)
    PYTHON      = python
    VENV_PYTHON = .venv\Scripts\python
    VENV_PIP    = .venv\Scripts\pip
    NULL        = nul
else
    PYTHON      = python3
    VENV_PYTHON = .venv/bin/python
    VENV_PIP    = .venv/bin/pip
    NULL        = /dev/null
endif

APP_NAME = auto_easycheck_webserver

.PHONY: help setup mirror run test

$(VENV_PYTHON):
	$(PYTHON) -m venv .venv

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "  setup    Create venv and install dependencies"
	@echo "  mirror   Switch pip to Tsinghua mirror"
	@echo "  run      Run the application (port 3624)"
	@echo "  test     Run tests with pytest"
	@echo "  help     Show this help"

setup: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install --upgrade pip > $(NULL) 2>&1
	$(VENV_PIP) install -e .
	$(VENV_PIP) install -e ../auto_easycheck
	$(VENV_PIP) install -e ../easycheck_manager
	@echo "Setup complete."

mirror: $(VENV_PYTHON)
	$(VENV_PIP) config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
	@echo "Mirror set."

run: $(VENV_PYTHON)
	@$(VENV_PYTHON) -m $(APP_NAME)

test: $(VENV_PYTHON)
	$(VENV_PIP) install pytest pytest-cov 2>&1
	$(VENV_PYTHON) -m pytest tests/ -v --cov=src/$(APP_NAME) --cov-report=term-missing
