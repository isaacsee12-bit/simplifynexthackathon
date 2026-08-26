from fastapi import HTTPException, UploadFile
def validate_upload(file: UploadFile, allowed_types: list[str], max_size_mb: int) -> None:
    if file.content_type not in allowed_types:
        allowed = ", ".join(allowed_types)
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Allowed: {allowed}")


def validate_size(content: bytes, max_size_mb: int) -> None:
    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds the {max_size_mb} MB limit.")


def validate_media(file: UploadFile, content: bytes, allowed_types: list[str], max_size_mb: int) -> None:
    validate_upload(file, allowed_types, max_size_mb)
    validate_size(content, max_size_mb)
