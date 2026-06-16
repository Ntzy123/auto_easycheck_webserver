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
	@echo "  setup    Create venv, auto-clone missing deps & install"
	@echo "  mirror   Switch pip to Tsinghua mirror"
	@echo "  run      Run the application (port 3624)"
	@echo "  test     Run tests with pytest"
	@echo "  help     Show this help"

setup: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install --upgrade pip > $(NULL) 2>&1
	$(VENV_PIP) install -e .
ifeq ($(OS),Windows_NT)
	@set "GIT_HTTP_LOW_SPEED_TIME=30" && set "GIT_HTTP_LOW_SPEED_LIMIT=1" && \
	if not exist "..\auto_easycheck" ( \
		echo Cloning auto_easycheck... && \
		git clone https://github.com/Ntzy123/auto_easycheck.git ..\auto_easycheck || \
		( echo ERROR: auto_easycheck 克隆失败，请检查网络连接 && exit 1 ) \
	) else (echo auto_easycheck 已存在)
	@set "GIT_HTTP_LOW_SPEED_TIME=30" && set "GIT_HTTP_LOW_SPEED_LIMIT=1" && \
	if not exist "..\easycheck_manager" ( \
		echo Cloning easycheck_manager... && \
		git clone https://github.com/Ntzy123/easycheck_manager.git ..\easycheck_manager || \
		( echo ERROR: easycheck_manager 克隆失败，请检查网络连接 && exit 1 ) \
	) else (echo easycheck_manager 已存在)
else
	@if [ ! -d "../auto_easycheck" ]; then \
		echo "Cloning auto_easycheck..."; \
		GIT_HTTP_LOW_SPEED_TIME=30 GIT_HTTP_LOW_SPEED_LIMIT=1 git clone https://github.com/Ntzy123/auto_easycheck.git ../auto_easycheck || \
		{ echo "ERROR: auto_easycheck 克隆失败，可能是网络超时或连接异常，请检查网络后重试"; exit 1; }; \
	else \
		echo "auto_easycheck 已存在"; \
	fi
	@if [ ! -d "../easycheck_manager" ]; then \
		echo "Cloning easycheck_manager..."; \
		GIT_HTTP_LOW_SPEED_TIME=30 GIT_HTTP_LOW_SPEED_LIMIT=1 git clone https://github.com/Ntzy123/easycheck_manager.git ../easycheck_manager || \
		{ echo "ERROR: easycheck_manager 克隆失败，可能是网络超时或连接异常，请检查网络后重试"; exit 1; }; \
	else \
		echo "easycheck_manager 已存在"; \
	fi
endif
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
