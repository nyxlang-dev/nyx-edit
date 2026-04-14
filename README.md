# nyx-edit

A terminal text editor written entirely in Nyx (~1090 lines, single file). Supports raw mode, syntax highlighting, undo, search, and selection — with no external dependencies.

Editor de texto para terminal escrito completamente en Nyx (~1090 líneas, archivo único). Soporta modo raw, resaltado de sintaxis, undo, búsqueda y selección — sin dependencias externas.

---

## Install

Install the Nyx toolchain:

```bash
curl -sSf https://nyxlang.com/install.sh | sh
```

## Quick start

```bash
git clone https://github.com/nyxlang-dev/nyx-edit
cd nyx-edit
nyx build
./nyx-edit [file.txt]
```

## Usage

```bash
./nyx-edit                  # open empty buffer
./nyx-edit file.txt         # open existing file
```

## Features

- Raw mode terminal input (byte-by-byte, no buffering)
- Heuristic syntax highlighting (keywords, strings, comments, numbers)
- Text selection with Shift+arrows
- Internal clipboard (copy / cut / paste)
- Undo stack (100 levels)
- Search with wrap-around (`Ctrl+F`)
- Go to line number (`Ctrl+G`)
- Dynamic terminal size detection (`term_cols` / `term_rows`)
- Automatic terminal cleanup via `defer`

## Keybindings

| Key | Action |
|-----|--------|
| Arrows | Move cursor |
| Shift+Arrows | Extend selection |
| `Ctrl+S` | Save file |
| `Ctrl+Q` | Quit |
| `Ctrl+Z` | Undo |
| `Ctrl+F` | Search (wrap-around) |
| `Ctrl+G` | Go to line number |
| `Ctrl+C` | Copy selection |
| `Ctrl+X` | Cut selection |
| `Ctrl+V` | Paste |
| `Ctrl+K` | Delete current line |
| `Tab` | Insert 4 spaces |
| `Home` / `End` | Start / end of line |
| `PgUp` / `PgDn` | Page up / down |

## Documentation

Internal architecture and implementation notes: [`docs/README.md`](./docs/README.md)

## Limitations

- ASCII only — no UTF-8 multi-byte character support
- Internal clipboard only — no integration with the system clipboard
- Syntax highlighting is heuristic, not grammar-based
- No mouse support, no split panes

## License

Apache 2.0 — see [LICENSE](../../LICENSE)
