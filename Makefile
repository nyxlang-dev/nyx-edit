# Makefile — nyx-edit-stack
# El toolchain Nyx (compilador, runtime, std) vive fuera de este repo.
# Se apunta vía NYX_HOME (patrón nyx-kv-stack).

NYX_HOME ?= /home/admin/nyx/lang
export NYX_HOME

.PHONY: build test-edit install uninstall clean

build:
	nyx build

test-edit: build
	python3 tests/test_edit_pty.py

# Deja el binario JUNTO AL TOOLCHAIN, no en el PATH del usuario: así
# `nyx edit` anda desde cualquier proyecto sin pedirle a nadie que agregue un
# directorio más al PATH. El wrapper `nyx` lo busca primero en el PATH (una
# build de desarrollo gana) y después acá.
#
# NYX_BIN sale de NYX_HOME/bin si existe, y si no de ~/.nyx/bin — que es donde
# `make install-local` del repo del lenguaje arma el toolchain.
NYX_BIN ?= $(HOME)/.nyx/bin

install: build
	@mkdir -p "$(NYX_BIN)"
	@cp nyx-edit "$(NYX_BIN)/nyx-edit"
	@echo "✓ nyx-edit instalado en $(NYX_BIN)"
	@echo "  Probalo desde cualquier proyecto:  nyx edit archivo.txt"

uninstall:
	@rm -f "$(NYX_BIN)/nyx-edit"
	@echo "✓ nyx-edit quitado de $(NYX_BIN)"

clean:
	rm -f nyx-edit script.nx script.ll nyx.lock
