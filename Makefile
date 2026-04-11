PACKAGE ?=

VENV_BIN := $(CURDIR)/.venv/bin
ifneq ("$(wildcard $(VENV_BIN))","")
export PATH := $(VENV_BIN):$(PATH)
export VIRTUAL_ENV := $(CURDIR)/.venv
endif

PACKAGES := $(shell ./scripts/package.py | awk '/^-/{print $$2}' | grep -v '^_')

TRIVY_IMAGE ?= aquasec/trivy:0.69.3

.PHONY: bootstrap doctor list build build-all test test-all e2e publish show detect-version smoke-all check lint format format-check unit clean-local shellcheck hadolint trivy trivy-all

bootstrap:
	@python3 -m venv .venv
	@$(VENV_BIN)/python -m pip install --upgrade pip pyyaml

doctor:
	@command -v docker >/dev/null || (echo "docker not found in PATH" && exit 1)
	@command -v python3 >/dev/null || (echo "python3 not found in PATH" && exit 1)
	@$(if $(wildcard $(VENV_BIN)/python),$(VENV_BIN)/python,python3) -c 'import yaml'
	@echo "Environment looks healthy."

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

build-all:
	@for pkg in $(PACKAGES); do \
		echo "==> $$pkg"; \
		./scripts/package.py build $$pkg; \
	done

test:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE=<slug>" && exit 1)
	./scripts/package.py test $(PACKAGE)

test-all:
	@for pkg in $(PACKAGES); do \
		echo "==> $$pkg"; \
		./scripts/package.py test $$pkg; \
	done

e2e:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE=<slug>" && exit 1)
	@test -x "containers/$(PACKAGE)/tests/e2e.sh" || (echo "No e2e.sh for PACKAGE=$(PACKAGE)" && exit 1)
	containers/$(PACKAGE)/tests/e2e.sh

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
	@for pkg in $(PACKAGES); do \
		echo "==> $$pkg"; \
		./scripts/package.py build $$pkg; \
		./scripts/package.py test $$pkg; \
	done

check:
	@for pkg in $(PACKAGES); do \
		printf 'Checking %s\n' $$pkg; \
		./scripts/package.py show $$pkg >/dev/null; \
	done

shellcheck:
	@command -v shellcheck >/dev/null || (echo "shellcheck not found. Install shellcheck to run local lint." && exit 1)
	@sh_files=$$(git ls-files '*.sh'); \
	if [ -n "$$sh_files" ]; then \
		echo "$$sh_files" | xargs -r shellcheck; \
	else \
		echo "No shell scripts to lint."; \
	fi

hadolint:
	@command -v hadolint >/dev/null || (echo "hadolint not found. Install hadolint to run local lint." && exit 1)
	@dockerfiles=$$(git ls-files '*Dockerfile'); \
	if [ -n "$$dockerfiles" ]; then \
		echo "$$dockerfiles" | xargs -n1 hadolint; \
	else \
		echo "No Dockerfiles to lint."; \
	fi

trivy:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE=<slug>" && exit 1)
	@image_ref=$$($(if $(wildcard $(VENV_BIN)/python),$(VENV_BIN)/python,python3) -c 'import yaml; m=yaml.safe_load(open("containers/$(PACKAGE)/container.yaml", encoding="utf-8")); print("{}:{}".format(m["publish"]["image"], m["version"]["current"]))'); \
	echo "Scanning $$image_ref with $(TRIVY_IMAGE)"; \
	docker run --rm \
		-v /var/run/docker.sock:/var/run/docker.sock \
		"$(TRIVY_IMAGE)" \
		image --ignore-unfixed --severity CRITICAL,HIGH --exit-code 1 --scanners vuln "$$image_ref"

trivy-all:
	@for pkg in $(PACKAGES); do \
		echo "==> $$pkg"; \
		$(MAKE) trivy PACKAGE=$$pkg || exit $$?; \
	done

lint: check shellcheck hadolint

format:
	@echo "No repository-wide formatter is configured."

format-check:
	@echo "No repository-wide formatter is configured."

unit: check

clean-local:
	@rm -rf logs _tmp _reports reports
	@rm -rf containers/spark/local/minio
	@rm -rf containers/airflow/local/logs containers/airflow/local/plugins
	@echo "Local artifacts cleaned."
