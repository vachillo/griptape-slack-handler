SHELL = bash
.DEFAULT_GOAL := help

.PHONY: deploy-griptape
deploy-griptape: ## Deploy to Griptape structure.
	@poetry run inv deploy-griptape

.PHONY: deploy-griptape-dev
deploy-griptape-dev: ## Deploy to Griptape dev structure.
	@poetry run inv deploy-griptape --dev

.PHONY: deploy-griptape-env
deploy-griptape-env: ## Deploy the environment variables for the structure.
	@poetry run inv deploy-griptape-env

.PHONY: deploy-griptape-env-dev
deploy-griptape-env-dev: ## Deploy the environment variables for the dev structure.
	@poetry run inv deploy-griptape-env --dev

.PHONY: install
install: ## Install dependencies and create a requirements.txt file.
	@poetry run inv install

.PHONY: format
format: ## Format code.
	@poetry run inv format

.PHONY: setup
setup: ## Initial project setup.
	@poetry run python -m venv .venv
	@poetry lock --no-update && poetry install --only dev
	@make install
	@poetry run inv setup-branches


.PHONY: help
help: ## Print Makefile help text.
	@grep -E '^[a-zA-Z_\/%-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| awk 'BEGIN {FS = ":.*?## "}; \
	{printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
