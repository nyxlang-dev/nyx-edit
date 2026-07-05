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
- **Live terminal resize** (SIGWINCH) — re-renders instantly, no keypress needed
- **UTF-8 aware** — cursor movement, editing and rendering by codepoint (2-4 bytes)
- **Alternate screen** — your scrollback is intact after quitting (like vim/less)
- **Flicker-free rendering** — one buffered write per frame + synchronized output (?2026)
- **Mouse support (SGR)** — click to position, drag to select, wheel to scroll
- **Bracketed paste** — multiline pastes are inserted literally, as one undo group
- Heuristic syntax highlighting (keywords, strings, comments, numbers, basic types)
- Text selection with Shift+arrows
- Internal clipboard (copy / cut / paste)
- **Incremental undo/redo** — per-operation deltas with typing coalescing (1000 levels)
- Search with wrap-around (`Ctrl+F`)
- Go to line number (`Ctrl+G`)
- Automatic terminal cleanup via `defer` on every exit path

## Keybindings

| Key | Action |
|-----|--------|
| Arrows | Move cursor |
| Shift+Arrows | Extend selection |
| `Ctrl+S` | Save file |
| `Ctrl+Q` | Quit |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| Mouse click / drag / wheel | Position cursor / select / scroll |
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

- UTF-8 codepoints render with width 1 — wide chars (CJK/emoji) misalign the cursor (stage 2)
- Internal clipboard only — no integration with the system clipboard
- Syntax highlighting is heuristic, not grammar-based
- No split panes, no multi-buffer (stage 2)

## License

Apache 2.0 — see [LICENSE](../../LICENSE)
