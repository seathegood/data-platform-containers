PACKAGE ?=

VENV_BIN := $(CURDIR)/.venv/bin
ifneq ("$(wildcard $(VENV_BIN))","")
export PATH := $(VENV_BIN):$(PATH)
export VIRTUAL_ENV := $(CURDIR)/.venv
endif

.PHONY: list build test publish show detect-version smoke-all check

list:
	@./scripts/package.py

build:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE=<slug>" && exit 1)
	@if [ -n "$(BUILD_LOG)" ]; then \
		LOG_DIR="$(LOG_DIR)"; \
		if [ -z "$$LOG_DIR" ]; then LOG_DIR="$(CURDIR)/logs"; fi; \
		mkdir -p "$$LOG_DIR"; \
		LOG_FILE="$$LOG_DIR/build-$(PACKAGE)-$$(date +%Y%m%d%H%M%S).log"; \
		echo "Writing build log to $$LOG_FILE"; \
		./scripts/package.py build $(PACKAGE)$(if $(PACKAGE_PLATFORMS), --platform $(PACKAGE_PLATFORMS),) 2>&1 | tee "$$LOG_FILE"; \
	else \
		./scripts/package.py build $(PACKAGE)$(if $(PACKAGE_PLATFORMS), --platform $(PACKAGE_PLATFORMS),); \
	fi

test:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE=<slug>" && exit 1)
	./scripts/package.py test $(PACKAGE)

publish:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE=<slug>" && exit 1)
	./scripts/package.py publish $(PACKAGE)

show:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE=<slug>" && exit 1)
	./scripts/package.py show $(PACKAGE)

detect-version:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE=<slug>" && exit 1)
	./scripts/package.py detect-version $(PACKAGE)

smoke-all:
	@for pkg in $$(./scripts/package.py | awk '/^-/{print $$2}'); do \
		echo "==> $$pkg"; \
		./scripts/package.py build $$pkg; \
		./scripts/package.py test $$pkg; \
	done

check:
	@for pkg in $(shell ./scripts/package.py | awk '/^-/{print $$2}' | grep -v '^_'); do \
		printf 'Checking %s\n' $$pkg; \
		./scripts/package.py show $$pkg >/dev/null; \
	done
