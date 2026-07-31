# nyx-edit — Documentation

## Overview

nyx-edit is a terminal text editor written entirely in Nyx (~1090 lines, single file). It uses only language builtins — no imports, no FFI, no C glue code.

## Architecture

The editor is implemented in `src/main.nx` as a single file with these logical sections:

| Section | Description |
|---------|-------------|
| Constants | Key codes (arrows, Ctrl combos, special keys) |
| Global state | Buffer (array of lines), cursor, scroll, selection, undo stack, clipboard |
| Input | `read_key()` — raw mode byte reader with escape sequence parser |
| Buffer ops | Insert/delete char, insert/delete line, indent/dedent |
| Selection | Shift+arrow selection, copy/cut/paste to internal clipboard |
| Undo | Stack-based undo (100 levels) with insert/delete/line operations |
| Search | Ctrl+F incremental search with wrap-around |
| Rendering | `render()` — full screen redraw with syntax highlighting |
| Syntax highlighting | Keyword/string/comment/number colorization |
| File I/O | Open file on startup, Ctrl+S save |
| Main loop | `read_key()` → dispatch → `render()` cycle |

## Builtins Used

These Nyx builtins power the editor without any imports:

- `raw_mode_enter()` / `raw_mode_exit()` — switch terminal to raw mode
- `read_byte()` — read a single byte from stdin (non-blocking in raw mode)
- `chr(code)` — convert ASCII code to single-character string
- `term_cols()` / `term_rows()` — query terminal dimensions
- `read_file(path)` / `write_file(path, content)` — file I/O
- `arr.insert(idx, val)` / `arr.remove(idx)` — buffer line manipulation
- `defer { ... }` — ensure `raw_mode_exit()` runs on any exit path

## Limitations

- ASCII only — no UTF-8 multi-byte character support
- Internal clipboard — does not interact with system clipboard
- No mouse support
- No split panes or multiple buffers
- Syntax highlighting is heuristic-based, not grammar-aware
