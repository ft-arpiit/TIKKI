from __future__ import annotations

from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "PROJECT_TIKKI_v1.0.zip"

EXCLUDE_DIRS = {".venv", "__pycache__", ".git", ".pytest_cache"}
EXCLUDE_NAMES = {".env"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    if path.suffix in {".pyc", ".pyo"}:
        return False
    return True


def build() -> Path:
    if OUTPUT.exists():
        OUTPUT.unlink()

    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and should_include(path):
                arcname = Path("PROJECT_TIKKI") / path.relative_to(ROOT)
                zf.write(path, arcname.as_posix())

    print(f"Created: {OUTPUT}")
    return OUTPUT


if __name__ == "__main__":
    build()
