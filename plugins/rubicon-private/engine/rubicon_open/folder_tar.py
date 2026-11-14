"""A folder as one gzipped tar and back, the way a run's folder or a conversation's is kept in object storage: by Ruby
(`rubicon.coordinator.storage`) and by the hosted MCP server (`rubicon/mcp/hosted_store.py`)."""
from __future__ import annotations

import io
import tarfile
from pathlib import Path


def pack(folder: Path, kept=lambda path, folder: True) -> bytes:
    """The folder as a gzipped tar, of the files `kept(path, folder)` keeps."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in sorted(folder.rglob("*")):
            if p.is_file() and kept(p, folder):
                tar.add(p, arcname=p.relative_to(folder).as_posix(), recursive=False)
    return buf.getvalue()


def unpack(data: bytes, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        # `data` refuses any member that would land outside the folder or is not a plain file.
        tar.extractall(folder, filter="data")
