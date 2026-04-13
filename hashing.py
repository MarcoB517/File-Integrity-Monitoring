"""
hashing.py — Cryptographic Hashing Module

This module provides SHA-256 hash computation for files, using chunked
reading to safely handle files of any size without exhausting memory.

Design Decisions:
    - SHA-256 chosen over MD5 because MD5 is cryptographically broken
    - Chunked reading (default 1MB) prevents memory exhaustion on large files
    - Returns hex digest for human-readable storage and comparison

Example:
    >>> from hashing import sha256_file
    >>> hash_value = sha256_file("/etc/passwd")
    >>> print(hash_value[:16])
    a1b2c3d4e5f67890

Author: Marco Buritica
Course: CISC 4900
"""

import hashlib
from pathlib import Path
from typing import Union


def sha256_file(filepath: Union[str, Path], chunk_size: int = 1024 * 1024) -> str:
    """
    Compute the SHA-256 hash of a file using chunked reading.

    This function reads the file in chunks to compute its hash incrementally,
    making it safe to use on files of any size. A 10GB file will use the same
    amount of memory as a 10KB file.

    Args:
        filepath: Path to the file to hash. Can be a string or Path object.
        chunk_size: Number of bytes to read at a time. Default is 1MB (1024*1024).
                    Smaller values use less memory but may be slower.
                    Larger values may be faster but use more memory.

    Returns:
        A 64-character hexadecimal string representing the SHA-256 hash.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read due to permissions.
        IsADirectoryError: If the path points to a directory.

    Example:
        >>> sha256_file("example.txt")
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

        >>> # Using smaller chunks for memory-constrained environments
        >>> sha256_file("large_file.bin", chunk_size=65536)
        'abc123...'

    Note:
        The empty file always has this SHA-256 hash:
        e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

    Security:
        SHA-256 is part of the SHA-2 family and is considered cryptographically
        secure. No practical collision attacks are known. It is suitable for
        integrity verification in security applications.
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
