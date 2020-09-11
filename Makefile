# To get help type: make help
PKG ?= grape
WHEEL_DEPS    := README.md setup.py $(shell find grape -type f | fgrep -v cache)

.DEFAULT_GOAL := default

# Store the virtual environment in the project space.
export PIPENV_VENV_IN_PROJECT=1

# ================================================================
#
# Macros
#
# ================================================================
define hdr
	@printf '\n'
        @printf '\x1b[35;1m=-=-= Target: %s %s =-=-= \x1b[0m\n' "$1" "$(shell date)"
        @printf '\x1b[35;1m=-=-= Directory: %s %s =-=-= \x1b[0m\n' "$$(pwd)" "$(shell date)"
endef

# ================================================================
#
# Targets
#
# ================================================================
.PHONY: default
default: pkg test  ## Default is to build and test everything.

.PHONY: clean
clean:
	$(call hdr,$@)
	find . -type f -name '*~' -delete
	git clean -xdf -e keep .

# pkg
.PHONY: pkg
pkg: init .wheel-install  ## Build the grape package wheel (same as wheel).

# wheel
.PHONY: wheel
wheel: .wheel-install  ## Build the grape package wheel (same as pkg).

# test
.PHONY: test
test: init  ## Run the unit tests.
	$(call hdr,$@)
	cd test && pipenv run pytest -v --cov=grape .

# pylint
.PHONY: pylint
pylint: init  ## Lint the source code.
	$(call hdr,"$@")
	pipenv run pylint --disable=duplicate-code $(PKG)

# demo01
.PHONY: demo01
demo01:  ## Run samples/demo01.
	$(call hdr,"$@")
	cd samples/$@ && ./run.sh

# demo02
.PHONY: demo02
demo02:  ## Run samples/demo02.
	$(call hdr,"$@")
	cd samples/$@ && ./run.sh

# demo03
.PHONY: demo03
demo03:  ## Run samples/demo03.
	$(call hdr,"$@")
	cd samples/$@ && ./run.sh

# import
.PHONY: import
import:  ## Run the samples/import. It will fail if import.yaml has not been defined.
	$(call hdr,"$@")
	cd samples/$@ && ./run.sh

# backup
.PHONY: backup
backup:  ## Backup the source.
	$(call hdr,"$@")
	@-rm -f $@.tar
	tar -jcf $@.tar $$(git ls-files)
	ls -lh $@.tar

# Help.
.PHONY: help
help:  ## This help message.
	@echo "Targets"
	@egrep '^[ ]*[^:]*[ ]*:.*##' $(MAKEFILE_LIST) 2>/dev/null | \
		egrep -v '^ *#' | \
		egrep -v 'egrep|sed' | \
		sed -e 's/: .*##/##/' -e 's/^[^:#]*://' | \
		column -t -s '##' | \
		sort -f | \
		sed -e 's@^@   @'

# Make wheel with pylint check that only runs when
# updates are detected.
.wheel-install: $(WHEEL_DEPS)
	$(call hdr,"package")
	pipenv run pylint --disable=duplicate-code $(PKG)
	$(MAKE) wheel-install
	touch $@

# Low level wheel targets.
.PHONY: wheel-install
wheel-install: wheel-build  ## Install the wheel.
	$(call hdr,$@)
	-pipenv run pip uninstall -y $(PKG)
	pipenv run pip install dist/$(PKG)*.whl

.PHONY: wheel-build
wheel-build: init  ## Build the wheel.
	$(call hdr,$@)
	pipenv run python setup.py sdist bdist_wheel

.PHONY: init
init:  ## Initialize the environment.
	$(call hdr,$@)
	pipenv install
