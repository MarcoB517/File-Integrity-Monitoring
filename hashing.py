import hashlib
from pathlib import Path

def sha256_file(filepath: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute SHA-256 hash of a file by reading it in chunks.
    chunk_size default = 1MB.
    Returns hex string.
    """
    filepath = Path(filepath)

    h = hashlib.sha256()
    with filepath.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()