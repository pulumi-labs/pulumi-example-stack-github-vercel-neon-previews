"""Copy the small application closure without following PR-controlled symlinks."""

import os
import shutil
from pathlib import Path
from typing import Final

FILES: Final = ("main.py", "requirements.txt", ".python-version")
MAX_BYTES: Final = 1_000_000
source = Path(os.environ["PREVIEW_APP_SOURCE"])
destination = Path("upload")
if destination.exists() or destination.is_symlink():
    message = "upload/ must be absent before staging"
    raise SystemExit(message)
for name in FILES:
    file = source / name
    if (
        source.is_symlink()
        or source.parent.is_symlink()
        or file.parent.is_symlink()
        or file.is_symlink()
        or not file.is_file()
        or file.stat().st_size > MAX_BYTES
    ):
        message = f"App input is missing, oversized or a symlink: {name}"
        raise SystemExit(message)
for name in FILES:
    target = destination / name
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = shutil.copyfile(source / name, target)
