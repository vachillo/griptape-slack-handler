SHELL = bash
.DEFAULT_GOAL := help

.PHONY: deploy-griptape
deploy-griptape: ## Deploy to Griptape structure.
	@uv run inv deploy-griptape

.PHONY: deploy-griptape-dev
deploy-griptape-dev: ## Deploy to Griptape dev structure.
	@uv run inv deploy-griptape --dev

.PHONY: deploy-griptape-env
deploy-griptape-env: ## Deploy the environment variables for the structure.
	@uv run inv deploy-griptape-env

.PHONY: deploy-griptape-env-dev
deploy-griptape-env-dev: ## Deploy the environment variables for the dev structure.
	@uv run inv deploy-griptape-env --dev

.PHONY: install
install: ## Install dependencies and create a requirements.txt file.
	@uv run inv install

.PHONY: format
format: ## Format code.
	@uv run inv format

.PHONY: setup
setup: ## Initial project setup.
	@uv run python -m venv .venv
	@uv lock --no-update && uv install --only dev
	@make install
	@uv run inv setup-branches


.PHONY: help
help: ## Print Makefile help text.
	@grep -E '^[a-zA-Z_\/%-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| awk 'BEGIN {FS = ":.*?## "}; \
	{printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
