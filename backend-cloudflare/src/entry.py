from __future__ import annotations

import sys
from pathlib import Path

import asgi
from workers import WorkerEntrypoint


def _ensure_backend_source_on_path() -> None:
    """Allow local/dev packaging to import the backend runtime source tree."""
    backend_src = Path(__file__).resolve().parents[2] / "backend-vercel" / "src"
    backend_src_str = str(backend_src)
    if backend_src.exists() and backend_src_str not in sys.path:
        sys.path.insert(0, backend_src_str)


_ensure_backend_source_on_path()

from immcad_api.main import app  # noqa: E402


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)
