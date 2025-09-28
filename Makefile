PACKAGE ?=

.PHONY: list build test publish show detect-version smoke-all check

list:
	@./scripts/package.py

build:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE=<slug>" && exit 1)
	./scripts/package.py build $(PACKAGE)

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
	./scripts/package.py show hive-metastore >/dev/null
