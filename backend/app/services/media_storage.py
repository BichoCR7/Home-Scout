"""Contained local storage adapter for validated listing images."""

from pathlib import Path

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class LocalMediaStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def _path(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        if path.parent != self.root or path.name != storage_key:
            raise ValueError("Invalid storage object key.")
        return path

    def put(self, storage_key: str, contents: bytes) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self._path(storage_key)
        temporary = destination.with_name(f".{destination.name}.tmp")
        try:
            temporary.write_bytes(contents)
            try:
                temporary.chmod(0o600)
            except OSError:
                pass
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, storage_key: str) -> Path | None:
        candidate = self._path(storage_key)
        return candidate if candidate.is_file() else None

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)
