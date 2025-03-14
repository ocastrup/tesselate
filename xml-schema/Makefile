# A self-documenting Makefile
# You can set these variables from the command line, and also
# from the environment for the first two.

SOURCEDIR = ./src

# The Makefile depends on the following assumptions
# Prerequisites:
# 	1. A python version must be installed
#   2. uv installed in your environment
#      	uv standalone installer (on Windows):
#		powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
#   3. On Windows, install in a dev environment
#		- m2w64-make # GNU mMake for windows
#       - m2-grep # Grep for windows. For Makefile sh
#       - m2-gawk # awk for windows. for Makefile sh
# We need this to use the Make features on Windows

# PROJECT init using uv and powershell
venv:  ## Initialize the project using uv and create the virtual environment
	@uv venv
	@.venv\Scripts\activate

python-version:  ## The Python version used for this project
	@python --version
py-v:
	@python --version
list:  ## Lista all packages installed in current environment
	@uv pip list
tools: ## List all tools installed
	@uv tool list

init-tools:  ## Install the common tools
	@uv tool install ruff
	@uv tool install pre-commit
	@uv tool install tbump
	@uv tool list
# Color output
BLUE='\033[0;34m'
NC='\033[0m' # No Color

check:
	@echo ${PYPI_USER}
	@echo {$PSWD}
.PHONY: check

# DOCUMENTATION ##############################################################
SPHINXBUILD = sphinx-build -E -b html docs dist/docs
COVDIR = "htmlcov"

doc-serve: ## Open the the html docs built by Sphinx
	@cmd /c start "_build/index.html"

ds: doc-serve
.PHINY: ds

doc: ## Build the html docs using Sphinx. For other Sphinx options, run make in the docs folder
	@sphinx-build docs _build
PHONY: doc

doc-links: ## Check the internal and external links after building the documentation
	@sphinx-build docs -W -b linkcheck -d _build/doctrees _build/html
PHONY: doc-links
# POETRY ########################################################################
build:   ## Build the package dist with poetry
	@poetry update
	@poetry build
.PHONY: build

poetry-fix:  ## Force pip poetry re-installation
	@pip install poetry --upgrade
.PHONY: poetry-fix

poetry-export:   ## Export the dependencies to docs/requirements.txt
	@poetry export --with=docs --without-hashes -o ./docs/requirements.txt


# Poetry run CLI
poetry-run:  ## Run the CLI
	@poetry run  databinding
.PHONY: poetry-run
# pre-commit ######################################################################
pre-commit:	## Run any pre-commit hooks
	@pre-commit run --all-files

# TESTS #######################################################################

FAILURES := .pytest_cache/pytest/v/cache/lastfailed


test:  ## Run unit and integration tests
	@pytest --durations=5  --cov-report html --cov ${source_dir} .
.PHONY: test

test-cov:  ## View the test coverage report
	cmd /c start $(CURDIR)/htmlcov/index.html
.PHONY: test-cov


# HELP ########################################################################


.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

#-----------------------------------------------------------------------------------------------
