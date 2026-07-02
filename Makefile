# music-generator dev tasks. Run `make help` for the list.
# All targets use the project venv at ./venv (see `make venv`).

VENV := venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

$(VENV):
	python3 -m venv $(VENV)

.PHONY: venv
venv: $(VENV) ## Create the virtualenv

.PHONY: install
install: $(VENV) ## Install runtime + dev dependencies into the venv
	$(PIP) install -q -r requirements.txt -r requirements-dev.txt

.PHONY: test
test: ## Run the test suite
	$(PY) -m pytest

.PHONY: lint
lint: ## Lint with ruff (see pyproject.toml)
	$(RUFF) check .

.PHONY: format
format: ## Apply ruff's safe autofixes
	$(RUFF) check --fix .

.PHONY: check
check: lint test ## Lint then test — run before committing

.PHONY: demo
demo: ## Play the flagship demo (Kiss On My List) — the "press demo" button
	$(PY) cook_song.py make kiss

.PHONY: gallery
gallery: ## Render the demo highlight set to committable MIDI (site/assets/midi)
	$(PY) cook_song.py gallery
