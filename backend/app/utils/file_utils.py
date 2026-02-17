import mimetypes
import os
from pathlib import Path

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx", ".jpg", ".jpeg", ".png"}

# Extensions that need conversion to PDF before AI extraction
CONVERTIBLE_EXTENSIONS = {".docx", ".xlsx", ".pptx"}

# Image extensions (sent directly to Document Intelligence)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def get_extension(filename: str) -> str:
    """Get the file extension in lowercase."""
    return Path(filename).suffix.lower()


def is_supported(filename: str) -> bool:
    """Check if the file extension is supported."""
    return get_extension(filename) in SUPPORTED_EXTENSIONS


def needs_conversion(filename: str) -> bool:
    """Check if the file needs to be converted to PDF."""
    return get_extension(filename) in CONVERTIBLE_EXTENSIONS


def is_image(filename: str) -> bool:
    """Check if the file is an image."""
    return get_extension(filename) in IMAGE_EXTENSIONS


def get_mime_type(filename: str) -> str:
    """Get the MIME type for a file."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def ensure_upload_dir(upload_dir: str) -> Path:
    """Ensure the upload directory exists and return it as a Path."""
    path = Path(upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    import re
    # Keep only the basename
    name = os.path.basename(filename)
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Remove any character that isn't alphanumeric, underscore, dash, or dot
    name = re.sub(r"[^a-zA-Z0-9_.-]", "", name)
    return name
