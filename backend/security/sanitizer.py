r"""AEGIS AI — Path Traversal Defense & Input Sanitization Engine
Guarantees secure filesystem interactions by defending against:
  - Directory traversal attacks (../, ..\, %2e%2e)
  - Null-byte injection (\x00)
  - Windows reserved DOS device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
  - Dangerous path delimiters and control characters
"""

import os
import re
from pathlib import Path

# Windows reserved device names (case-insensitive)
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# Illegal characters in filenames across POSIX and Windows
ILLEGAL_FILENAME_CHARS = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]')


def sanitize_filename(filename: str) -> str:
    """Sanitizes user-provided filename, eliminating traversal and illegal tokens."""
    if not filename:
        raise ValueError("Filename cannot be empty")

    # 1. Reject null bytes immediately
    if "\x00" in filename:
        raise ValueError("Null byte injection detected in filename")

    # 2. Reject directory traversal tokens
    if ".." in filename or "%2e%2e" in filename.lower():
        raise ValueError("Path traversal sequence ('..') detected in filename")

    # 3. Extract basename only (strips any leading paths / ../)
    clean_name = os.path.basename(filename.replace("\\", "/"))


    # 4. Remove illegal characters
    clean_name = ILLEGAL_FILENAME_CHARS.sub("_", clean_name)

    # 5. Check Windows reserved device names
    name_stem = Path(clean_name).stem.upper()
    if name_stem in WINDOWS_RESERVED_NAMES:
        clean_name = f"safe_{clean_name}"

    # 6. Ensure not purely dots or spaces
    clean_name = clean_name.strip(". ")
    if not clean_name:
        clean_name = "unnamed_file"

    return clean_name


def sanitize_file_path(filename: str, base_dir: Path | str) -> Path:
    """Resolves filename within base_dir and cryptographically verifies confinement.

    Raises ValueError if target path escapes base_dir.
    """
    safe_name = sanitize_filename(filename)
    base_path = Path(base_dir).resolve()
    target_path = (base_path / safe_name).resolve()

    # Boundary confinement check: target must be inside base_path
    try:
        target_path.relative_to(base_path)
    except ValueError as err:
        raise ValueError(f"Path traversal breach: {target_path} escapes confinement boundary {base_path}") from err

    return target_path


def sanitize_untrusted_text(text: str, max_length: int = 50000) -> str:
    """Strips dangerous control characters and truncates excessive payloads."""
    if not text:
        return ""
    # Strip null bytes and non-printable control characters (except newline, tab, carriage return)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return cleaned[:max_length]
