import shutil
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.errors import FileTooLargeError, InvalidFileError

ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "wagesheet": {".xlsx", ".xls"},
    "pf_ecr": {".pdf"},
    "esic_ecr": {".pdf"},
}

_CHUNK_SIZE = 1024 * 1024  # 1 MB


def validate_extension(filename: str | None, file_type: str) -> str:
    """Returns the lowercase extension if valid, else raises InvalidFileError."""
    ext = Path(filename or "").suffix.lower()
    allowed = ALLOWED_EXTENSIONS[file_type]
    if ext not in allowed:
        raise InvalidFileError(
            f"{file_type} must be one of {sorted(allowed)}, got '{ext or '(no extension)'}'"
        )
    return ext


def _upload_dir(data_dir: Path, verification_id: str) -> Path:
    return data_dir / "uploads" / verification_id


async def save_upload(
    data_dir: Path,
    verification_id: str,
    file_type: str,
    upload_file: UploadFile,
    max_file_mb: int,
) -> Path:
    """Streams the upload to disk, enforcing max_file_mb. Raises FileTooLargeError
    and removes the partial file if the limit is exceeded."""
    ext = validate_extension(upload_file.filename, file_type)
    dest_dir = _upload_dir(data_dir, verification_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{file_type}{ext}"
    max_bytes = max_file_mb * 1024 * 1024

    size = 0
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await upload_file.read(_CHUNK_SIZE):
            size += len(chunk)
            if size > max_bytes:
                await f.close()
                dest.unlink(missing_ok=True)
                raise FileTooLargeError(f"{file_type} exceeds max size of {max_file_mb} MB")
            await f.write(chunk)
    return dest


def get_file_path(data_dir: Path, verification_id: str, file_type: str) -> Path | None:
    dest_dir = _upload_dir(data_dir, verification_id)
    matches = list(dest_dir.glob(f"{file_type}.*"))
    return matches[0] if matches else None


def delete_verification_files(data_dir: Path, verification_id: str) -> None:
    shutil.rmtree(_upload_dir(data_dir, verification_id), ignore_errors=True)
    export_dir = data_dir / "exports"
    for path in export_dir.glob(f"{verification_id}.*"):
        path.unlink(missing_ok=True)
    for path in export_dir.glob(f"{verification_id}_unmatched.json"):
        path.unlink(missing_ok=True)
