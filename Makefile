# Makefile — nyx-edit-stack
# El toolchain Nyx (compilador, runtime, std) vive fuera de este repo.
# Se apunta vía NYX_HOME (patrón nyx-kv-stack).

NYX_HOME ?= /home/admin/nyx/lang
export NYX_HOME

.PHONY: build test-edit clean

build:
	nyx build

test-edit: build
	python3 tests/test_edit_pty.py

clean:
	rm -f nyx-edit script.nx script.ll nyx.lock
