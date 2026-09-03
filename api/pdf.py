"""``GET /pdf/{program}`` — curriculum PDFs for the frontend source viewer.

Mirrors ``web/src/app/api/pdf/[program]/route.ts`` so the Vercel-hosted frontend can
proxy to this route (``PDF_BASE_URL``) when the PDFs are not on its own filesystem.
Files live in ``PDF_DIR`` (default ``data/raw`` — gitignored on GitHub, Git LFS on the
Hugging Face Space).  Range requests are answered from memory: browsers ask for a few
hundred KB at a time for ``#page=N``; whole-file requests stream via ``FileResponse``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter()

PDF_FILES: dict[str, str] = {"AIT": "AIT.pdf", "DSBA": "DSBA.pdf", "BIT": "IT_inter2565.pdf", "IT": "IT2565.pdf"}
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")
_MEDIA = "application/pdf"


def pdf_dir() -> Path:
    return Path(os.environ.get("PDF_DIR") or Path(__file__).resolve().parents[1] / "data" / "raw")


def _headers(name: str) -> dict[str, str]:
    return {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=3600",
        "Content-Disposition": f'inline; filename="{name}"',
    }


def _read(file: Path, start: int, end: int) -> bytes:
    with file.open("rb") as fh:
        fh.seek(start)
        return fh.read(end - start + 1)


@router.api_route("/pdf/{program}", methods=["GET", "HEAD"])
async def pdf(program: str, request: Request) -> Response:
    name = PDF_FILES.get(program.upper())
    if name is None:
        return JSONResponse({"error": "unknown program"}, status_code=404)
    file = pdf_dir() / name
    if not file.is_file():
        return JSONResponse({"error": "pdf not available"}, status_code=404)
    size = file.stat().st_size
    headers = _headers(name)
    head = request.method == "HEAD"

    m = _RANGE.match((request.headers.get("range") or "").strip())
    if m and (m.group(1) or m.group(2)):
        start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2)))
        end = min(int(m.group(2)), size - 1) if (m.group(1) and m.group(2)) else size - 1
        if start >= size or start > end:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        headers["Content-Length"] = str(end - start + 1)
        body = b"" if head else _read(file, start, end)
        return Response(body, status_code=206, headers=headers, media_type=_MEDIA)

    if head:
        headers["Content-Length"] = str(size)
        return Response(status_code=200, headers=headers, media_type=_MEDIA)
    return FileResponse(file, media_type=_MEDIA, headers=headers)
