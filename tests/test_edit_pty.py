#!/usr/bin/env python3
"""
PTY-based integration tests for nyx-edit.

Drives the real editor binary through a pseudo-terminal: sends keystrokes,
reads the rendered output, and verifies on-disk results. Pure stdlib
(pty + subprocess + select) — no pexpect.

Usage:
    python3 tests/test_edit_pty.py

Prerequisites: nyx-edit binary must exist in the stack root (make build).
Override the binary path with NYX_EDIT_BIN if needed.
"""

import fcntl
import os
import pty
import re
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY = os.environ.get("NYX_EDIT_BIN", os.path.join(ROOT, "nyx-edit"))

# CSI/OSC sequences plus lone ESC-char pairs; enough to make screen text greppable
ANSI_RE = re.compile(rb"\x1b\[[0-9;?<]*[a-zA-Z~]|\x1b[()][A-Z0-9]")

CTRL_F = b"\x06"
CTRL_G = b"\x07"
CTRL_K = b"\x0b"
CTRL_Q = b"\x11"
CTRL_S = b"\x13"
CTRL_Y = b"\x19"
CTRL_Z = b"\x1a"

passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  PASS {name}")
        passed += 1
    else:
        print(f"  FAIL {name}")
        if detail:
            print(f"     {detail}")
        failed += 1


def _make_ctty():
    # Give the child the pty as controlling terminal so the kernel delivers
    # SIGWINCH on TIOCSWINSZ (needed by the resize tests).
    os.setsid()
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)


class Editor:
    """One nyx-edit process attached to a fresh pty."""

    def __init__(self, path=None, cols=80, rows=24):
        self.master, slave = pty.openpty()
        fcntl.ioctl(self.master, termios.TIOCSWINSZ,
                    struct.pack("HHHH", rows, cols, 0, 0))
        args = [BINARY] + ([path] if path else [])
        env = dict(os.environ, TERM="xterm-256color")
        self.proc = subprocess.Popen(
            args, stdin=slave, stdout=slave, stderr=slave,
            preexec_fn=_make_ctty, close_fds=True, env=env)
        os.close(slave)
        self.buf = b""

    def send(self, data):
        if isinstance(data, str):
            data = data.encode()
        os.write(self.master, data)

    def pump(self, timeout=0.05):
        """Read whatever the editor wrote; False once the pty is closed."""
        try:
            r, _, _ = select.select([self.master], [], [], timeout)
        except OSError:
            return False
        if not r:
            return True
        try:
            chunk = os.read(self.master, 65536)
        except OSError:  # EIO: slave side closed (process exited)
            return False
        if not chunk:
            return False
        self.buf += chunk
        return True

    def plain(self):
        return ANSI_RE.sub(b"", self.buf)

    def expect(self, text, timeout=5.0):
        """Poll with deadline until text appears in the ANSI-stripped output."""
        if isinstance(text, str):
            text = text.encode()
        deadline = time.time() + timeout
        while time.time() < deadline:
            if text in self.plain():
                return True
            if not self.pump(0.05):
                break
        return text in self.plain()

    def mark(self):
        """Position in the output stream; use with expect_after for freshness."""
        return len(self.buf)

    def expect_after(self, pos, text, timeout=5.0):
        if isinstance(text, str):
            text = text.encode()
        deadline = time.time() + timeout
        while time.time() < deadline:
            if text in ANSI_RE.sub(b"", self.buf[pos:]):
                return True
            if not self.pump(0.05):
                break
        return text in ANSI_RE.sub(b"", self.buf[pos:])

    def resize(self, cols, rows):
        fcntl.ioctl(self.master, termios.TIOCSWINSZ,
                    struct.pack("HHHH", rows, cols, 0, 0))

    def quit(self, timeout=5.0):
        """Ctrl+Q, wait for exit; returns the exit code (or None if killed)."""
        try:
            self.send(CTRL_Q)
        except OSError:
            pass
        deadline = time.time() + timeout
        while self.proc.poll() is None and time.time() < deadline:
            self.pump(0.05)
        while self.pump(0.05):  # drain remaining output
            pass
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        os.close(self.master)
        return self.proc.returncode

    def close(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        try:
            os.close(self.master)
        except OSError:
            pass


def make_file(content):
    fd, path = tempfile.mkstemp(prefix="nyx_edit_test_", suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def read_file(path):
    with open(path, "rb") as f:
        return f.read()


# ---------------------------------------------------------------- tests

def test_open_and_statusbar():
    print("open + status bar:")
    path = make_file("alpha\nbeta\ngamma\n")
    ed = Editor(path)
    try:
        check("renders file content", ed.expect("alpha"))
        check("status bar shows filename",
              ed.expect(os.path.basename(path)))
        check("status bar shows Ln 1/3", ed.expect("Ln 1/3"))
        code = ed.quit()
        check("clean exit code 0", code == 0, f"exit code: {code}")
        check("goodbye message", b"bye!" in ed.plain())
        check("alt screen enter (?1049h)", b"\x1b[?1049h" in ed.buf)
        check("alt screen leave (?1049l)", b"\x1b[?1049l" in ed.buf)
        check("synchronized output (?2026)",
              b"\x1b[?2026h" in ed.buf and b"\x1b[?2026l" in ed.buf)
    finally:
        ed.close()
        os.unlink(path)


def test_edit_save():
    print("edit + save:")
    path = make_file("hello\n")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/1")
        ed.send("XY")
        check("modified marker [+]", ed.expect("[+]"))
        ed.send(CTRL_S)
        check("save message", ed.expect("Saved: "))
        ed.quit()
        content = read_file(path)
        check("file contains typed text", content == b"XYhello\n",
              f"got: {content!r}")
    finally:
        ed.close()
        os.unlink(path)


def test_undo():
    print("undo:")
    path = make_file("abc\n")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/1")
        ed.send("Z")
        ed.expect("[+]")
        ed.send(CTRL_Z)
        check("undo message", ed.expect("Undo"))
        ed.send(CTRL_S)
        ed.expect("Saved: ")
        ed.quit()
        content = read_file(path)
        check("undo reverted the insertion", content == b"abc\n",
              f"got: {content!r}")
    finally:
        ed.close()
        os.unlink(path)


def test_newline_and_delete_line():
    print("newline + Ctrl+K:")
    path = make_file("one\n")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/1")
        ed.send("\x1b[F")      # End
        ed.send("\r")           # split -> new empty line 2
        ed.send("two")
        check("two lines now", ed.expect("Ln 2/2"))
        ed.send(CTRL_K)
        check("line deleted message", ed.expect("Line deleted"))
        ed.send(CTRL_S)
        ed.expect("Saved: ")
        ed.quit()
        content = read_file(path)
        check("Ctrl+K removed the new line", content == b"one\n",
              f"got: {content!r}")
    finally:
        ed.close()
        os.unlink(path)


def test_undo_coalescing_redo():
    print("undo con coalescing + redo:")
    path = make_file("base\n")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/1")
        ed.send("hola")            # 4 chars contiguos → 1 solo grupo de undo
        ed.expect("[+]")
        ed.send(CTRL_Z)
        ed.expect("Undo")
        m = ed.mark()
        ed.send(CTRL_S)
        ed.expect_after(m, "Saved: ")
        check("1 undo revierte la palabra entera (coalescing)",
              read_file(path) == b"base\n", f"got: {read_file(path)!r}")
        ed.send(CTRL_Y)
        check("redo message", ed.expect("Redo"))
        m = ed.mark()
        ed.send(CTRL_S)
        ed.expect_after(m, "Saved: ")
        check("redo restaura la palabra", read_file(path) == b"holabase\n",
              f"got: {read_file(path)!r}")
        ed.quit()
    finally:
        ed.close()
        os.unlink(path)


def test_undo_multiline():
    print("undo multilínea (split de línea):")
    path = make_file("ab\n")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/1")
        ed.send("\r")              # split en (0,0) → dos líneas
        ed.expect("Ln 2/2")
        ed.send(CTRL_Z)
        ed.expect("Undo")
        check("vuelve a 1 línea", ed.expect("Ln 1/1"))
        m = ed.mark()
        ed.send(CTRL_S)
        ed.expect_after(m, "Saved: ")
        check("contenido restaurado", read_file(path) == b"ab\n",
              f"got: {read_file(path)!r}")
        ed.quit()
    finally:
        ed.close()
        os.unlink(path)


def test_utf8_editing():
    print("edición UTF-8 (codepoints 2-3 bytes):")
    # borrar por codepoint: End + 2 backspaces borran "x" y "本" enteros
    path = make_file("áé日本x\n")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/1")
        ed.send("\x1b[F")          # End
        ed.send("\x7f\x7f")        # backspace ×2
        ed.send(CTRL_S)
        ed.expect("Saved: ")
        ed.quit()
        content = read_file(path)
        check("backspace borra codepoints enteros", content == "áé日\n".encode(),
              f"got: {content!r}")
    finally:
        ed.close()
        os.unlink(path)

    # mover por codepoint: Right sobre "á" salta los 2 bytes; insertar no corrompe
    path = make_file("áb\n")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/1")
        ed.send("\x1b[C")          # Right (debe saltar á entero)
        ed.send("X")
        ed.send(CTRL_S)
        ed.expect("Saved: ")
        ed.quit()
        content = read_file(path)
        check("cursor no cae en medio de un codepoint", content == "áXb\n".encode(),
              f"got: {content!r}")
    finally:
        ed.close()
        os.unlink(path)

    # tipeo UTF-8 directo: bytes multibyte del teclado se insertan enteros
    path = make_file("")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/1")
        ed.send("ñ日".encode())    # llegan como bytes multibyte crudos
        ed.send(CTRL_S)
        ed.expect("Saved: ")
        ed.quit()
        content = read_file(path)
        check("tipeo UTF-8 inserta codepoints enteros", content == "ñ日\n".encode(),
              f"got: {content!r}")
    finally:
        ed.close()
        os.unlink(path)


def test_bracketed_paste():
    print("bracketed paste:")
    path = make_file("")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/1")
        check("editor habilita ?2004h", b"\x1b[?2004h" in ed.buf)
        # paste envelope con \r intercalado (como mandan los terminales)
        ed.send(b"\x1b[200~line1\rline2\x1b[201~")
        check("paste multilínea insertado", ed.expect("Ln 2/2"))
        m = ed.mark()
        ed.send(CTRL_S)
        ed.expect_after(m, "Saved: ")
        check("contenido literal en disco", read_file(path) == b"line1\nline2\n",
              f"got: {read_file(path)!r}")
        ed.send(CTRL_Z)
        ed.expect("Undo")
        m = ed.mark()
        ed.send(CTRL_S)
        ed.expect_after(m, "Saved: ")
        check("1 solo undo revierte el paste entero",
              read_file(path) == b"\n", f"got: {read_file(path)!r}")
        ed.quit()
        check("?2004l al salir", b"\x1b[?2004l" in ed.buf)
    finally:
        ed.close()
        os.unlink(path)


def test_syntax_highlighting():
    print("syntax highlighting (operadores + llamadas a función):")
    path = make_file("fn demo() { let x = 1 + 2 }\n")
    ed = Editor(path)
    try:
        ed.expect("demo")
        # colores exactos emitidos por render_line (truecolor 38;2;r;g;b)
        check("keywords coloreadas (fn/let)", b"\x1b[38;2;86;156;214m" in ed.buf)
        check("números coloreados", b"\x1b[38;2;181;206;168m" in ed.buf)
        check("operadores coloreados (= +)", b"\x1b[38;2;86;182;194m" in ed.buf)
        check("llamadas a función coloreadas (demo()",
              b"\x1b[38;2;220;220;170m" in ed.buf)
        ed.quit()
    finally:
        ed.close()
        os.unlink(path)


def test_mouse_sgr():
    print("mouse SGR:")
    path = make_file("alpha\nbeta\ngamma\n")
    ed = Editor(path)
    try:
        ed.expect("Ln 1/3")
        check("editor habilita mouse SGR (?1006h)", b"\x1b[?1006h" in ed.buf)
        # click en fila 3, col 10 de pantalla → gamma, col de texto 2 (0-based)
        m = ed.mark()
        ed.send(b"\x1b[<0;10;3M\x1b[<0;10;3m")
        check("click posiciona el cursor (Ln 3)",
              ed.expect_after(m, "Ln 3/3", timeout=3.0))
        check("click posiciona la columna (Col 3)",
              ed.expect_after(m, "Col 3 ", timeout=3.0))
        # rueda arriba ×1 (3 líneas) → vuelve a Ln 1
        m = ed.mark()
        ed.send(b"\x1b[<64;1;1M")
        check("rueda scrollea hacia arriba",
              ed.expect_after(m, "Ln 1/3", timeout=3.0))
        ed.quit()
        check("mouse OFF al salir (?1006l)", b"\x1b[?1006l" in ed.buf)
        check("tracking OFF al salir (?1002l)", b"\x1b[?1002l" in ed.buf)
    finally:
        ed.close()
        os.unlink(path)


def test_resize_sigwinch():
    print("resize en vivo (SIGWINCH):")
    path = make_file("uno\ndos\ntres\n")
    ed = Editor(path, cols=80, rows=24)
    try:
        ed.expect("Ln 1/3")
        pos = ed.mark()
        ed.resize(100, 30)
        # sin mandar ninguna tecla: el editor debe despertar y re-renderizar
        check("re-render tras SIGWINCH sin teclas",
              ed.expect_after(pos, os.path.basename(path), timeout=3.0))
        # la status bar se paddea exactamente a g_cols: tras el resize debe
        # aparecer una línea "Ln 1/3" de ~100 chars (antes eran 80)
        ed.expect_after(pos, "Ln 1/3", timeout=3.0)
        status_lines = [l for l in ANSI_RE.sub(b"", ed.buf[pos:]).split(b"\r\n")
                        if b"Ln 1/3" in l]
        check("status bar usa el ancho nuevo (~100 cols)",
              any(len(l) >= 95 for l in status_lines),
              f"anchos vistos: {[len(l) for l in status_lines]}")
        ed.quit()
    finally:
        ed.close()
        os.unlink(path)


def main():
    if not os.path.exists(BINARY):
        print(f"SKIP: {BINARY} not built (make build)")
        sys.exit(1)
    print(f"nyx-edit PTY tests — binary: {BINARY}")
    test_open_and_statusbar()
    test_edit_save()
    test_undo()
    test_newline_and_delete_line()
    test_undo_coalescing_redo()
    test_undo_multiline()
    test_utf8_editing()
    test_bracketed_paste()
    test_syntax_highlighting()
    test_mouse_sgr()
    test_resize_sigwinch()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
