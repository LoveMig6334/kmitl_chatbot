"""Strip ``<think>…</think>`` blocks from a token stream, incrementally.

Thinking models (pathumma-…-think) stream their reasoning inside ``<think>``
tags; the tags themselves can be split across deltas (``"<thi"`` + ``"nk>"``).
``ThinkStripper`` is a tiny state machine: feed each delta, get back the text
that is safe to show; call ``flush()`` at the end.
"""

from __future__ import annotations

OPEN = "<think>"
CLOSE = "</think>"


def _partial_suffix(buf: str, tag: str) -> int:
    """Length of the longest suffix of ``buf`` that is a proper prefix of ``tag``."""
    for n in range(min(len(tag) - 1, len(buf)), 0, -1):
        if buf.endswith(tag[:n]):
            return n
    return 0


class ThinkStripper:
    def __init__(self) -> None:
        self.in_think = False
        self._buf = ""
        self._emitted_any = False
        self.think_text = ""  # kept for debugging / eval logs, never shown to the client

    def feed(self, delta: str) -> str:
        self._buf += delta
        out: list[str] = []
        while self._buf:
            if self.in_think:
                idx = self._buf.find(CLOSE)
                if idx < 0:
                    keep = _partial_suffix(self._buf, CLOSE)
                    self.think_text += self._buf[: len(self._buf) - keep]
                    self._buf = self._buf[len(self._buf) - keep :]
                    break
                self.think_text += self._buf[:idx]
                self._buf = self._buf[idx + len(CLOSE) :]
                self.in_think = False
                continue
            idx = self._buf.find(OPEN)
            if idx >= 0:
                out.append(self._buf[:idx])
                self._buf = self._buf[idx + len(OPEN) :]
                self.in_think = True
                continue
            keep = _partial_suffix(self._buf, OPEN)
            out.append(self._buf[: len(self._buf) - keep])
            self._buf = self._buf[len(self._buf) - keep :]
            break
        return self._finish("".join(out))

    def flush(self) -> str:
        """Release whatever is still buffered (an unterminated ``<think>`` is dropped)."""
        if self.in_think:
            self.think_text += self._buf
            self._buf = ""
            return ""
        out, self._buf = self._buf, ""
        return self._finish(out)

    def _finish(self, text: str) -> str:
        if not self._emitted_any:
            text = text.lstrip()  # models emit "\n\n" right after </think>
            if text:
                self._emitted_any = True
        return text
