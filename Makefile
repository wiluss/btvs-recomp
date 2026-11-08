PYTHON ?= python3
CC = clang
TOOLKIT_PYTHON ?= .venv/bin/python
CMAKE_PREFIX ?= /opt/homebrew
JOBS ?= 4

.PHONY: doctor test host-probe
doctor:
	$(PYTHON) tools/doctor.py

test:
	$(PYTHON) -m unittest discover -s tests -v

host-probe:
	mkdir -p build
	$(CC) -std=c11 -Wall -Wextra -Werror -O2 src/host/probe.c -o build/buffy-host-probe
	./build/buffy-host-probe

.PHONY: identify generate runtime game-build
identify:
	$(PYTHON) tools/xbe_inspect.py private/game/Default.xbe > artifacts/xbe-report.json
	$(PYTHON) tools/map_symbols.py private/game/Default.xbe private/game/final.map > artifacts/map-report.json

generate:
	$(TOOLKIT_PYTHON) tools/pipeline.py

runtime:
	cmake -S vendor/xboxrecomp -B build/runtime -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_PREFIX_PATH=$(CMAKE_PREFIX) -DOPENSSL_ROOT_DIR=$(CMAKE_PREFIX)/opt/openssl@3
	cmake --build build/runtime --parallel $(JOBS)

game-build:
	cmake -S . -B build/game -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_PREFIX_PATH=$(CMAKE_PREFIX) -DOPENSSL_ROOT_DIR=$(CMAKE_PREFIX)/opt/openssl@3 -DPython3_EXECUTABLE="$(CURDIR)/$(TOOLKIT_PYTHON)" -DBUFFY_BUILD_GAME=ON -DXBOXRECOMP_ENHANCE=ON
	cmake --build build/game --target buffy-macos --parallel $(JOBS)

# Apply the reviewed runtime patch explicitly as documented in patches/xboxrecomp.
.PHONY: runtime-patch-check

.PHONY: launcher
launcher:
	sh tools/build_launcher.sh

runtime-patch-check:
	git -C vendor/xboxrecomp apply --reverse --check ../../patches/xboxrecomp/0001-screen-w-infinity.patch
	git -C vendor/xboxrecomp apply --reverse --check ../../patches/xboxrecomp/0002-apu-image-sample-dma.patch
	git -C vendor/xboxrecomp apply --reverse --check ../../patches/xboxrecomp/0003-metal-compact-vertices.patch
	git -C vendor/xboxrecomp apply --reverse --check ../../patches/xboxrecomp/0006-launch-page-handoff.patch
	@set -eu; patchdir="$(CURDIR)/patches/xboxrecomp"; tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	for file in $$(sed -n 's|^+++ b/||p' "$$patchdir"/000[45]-*.patch | sort -u); do \
		mkdir -p "$$tmp/$$(dirname "$$file")"; cp "vendor/xboxrecomp/$$file" "$$tmp/$$file"; \
	done; \
	cd "$$tmp"; git apply --reverse "$$patchdir/0005-metal-uhd.patch"; \
	git apply --reverse --check "$$patchdir/0004-metal-hud-anchor.patch"

test runtime game-build: runtime-patch-check
