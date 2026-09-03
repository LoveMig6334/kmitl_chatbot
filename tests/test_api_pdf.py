"""``GET /pdf/{program}``: the curriculum PDFs for the frontend source viewer (Range-capable)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api.answerer import StubAnswerer
from api.main import create_app
from tests.test_api import GATE_SETTINGS

pytestmark = pytest.mark.anyio


@pytest.fixture
def pdf_app(tmp_path, monkeypatch):
    (tmp_path / "AIT.pdf").write_bytes(b"0123456789abcdef")
    monkeypatch.setenv("PDF_DIR", str(tmp_path))
    return create_app(answerer=StubAnswerer(), gate_settings=GATE_SETTINGS)


async def _get(app, path: str, **headers: str):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(path, headers=headers)


async def test_pdf_whole_file(pdf_app):
    r = await _get(pdf_app, "/pdf/ait")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["accept-ranges"] == "bytes"
    assert r.content == b"0123456789abcdef"


async def test_pdf_ranges(pdf_app):
    r = await _get(pdf_app, "/pdf/AIT", range="bytes=2-5")
    assert (r.status_code, r.headers["content-range"], r.content) == (206, "bytes 2-5/16", b"2345")
    r = await _get(pdf_app, "/pdf/AIT", range="bytes=12-")
    assert (r.status_code, r.content) == (206, b"cdef")
    r = await _get(pdf_app, "/pdf/AIT", range="bytes=-4")
    assert (r.status_code, r.headers["content-range"]) == (206, "bytes 12-15/16")
    r = await _get(pdf_app, "/pdf/AIT", range="bytes=99-")
    assert r.status_code == 416


async def test_pdf_404s_and_head(pdf_app):
    assert (await _get(pdf_app, "/pdf/nope")).status_code == 404
    assert (await _get(pdf_app, "/pdf/DSBA")).status_code == 404  # file absent
    async with AsyncClient(transport=ASGITransport(app=pdf_app), base_url="http://t") as c:
        head = await c.head("/pdf/AIT")
    assert head.status_code == 200
    assert head.content == b""
    assert head.headers["content-length"] == "16"
