"""
scanner.py — Directory Traversal and Metadata Collection Module

This module provides functionality to recursively scan a directory tree
and collect metadata for each regular file found. It is the core data
collection component of the File Integrity Monitoring system.

Features:
    - Recursive directory traversal using os.walk()
    - Comprehensive file metadata extraction via os.stat()
    - SHA-256 hash computation for content verification
    - Symlink skipping to prevent infinite loops
    - Graceful handling of permission errors and missing files

Example:
    >>> from scanner import collect_file_metadata
    >>> files = collect_file_metadata("/home/user/documents")
    >>> print(f"Found {len(files)} files")
    Found 42 files

Author: Marco Buritica
Course: CISC 4900
"""

import os
import stat
from pathlib import Path
from typing import List, Dict, Any

from hashing import sha256_file


def collect_file_metadata(root_dir: str) -> List[Dict[str, Any]]:
    """
    Recursively scan a directory and collect metadata for all regular files.

    This function walks the directory tree starting at root_dir, collecting
    metadata and computing SHA-256 hashes for each regular file encountered.
    Symbolic links are deliberately skipped to prevent infinite loops and
    security issues.

    Args:
        root_dir: Path to the directory to scan. Can be absolute or relative.
                  Supports ~ expansion for home directory.

    Returns:
        A sorted list of dictionaries, each containing metadata for one file:
            - path (str): Absolute path to the file
            - size_bytes (int): File size in bytes
            - mtime (float): Last modification time as Unix timestamp
            - permissions (str): Octal permission string (e.g., "0o644")
            - owner_uid (int): User ID of the file owner
            - owner_gid (int): Group ID of the file owner
            - inode (int): Filesystem inode number
            - hard_links (int): Number of hard links to the file
            - sha256 (str): SHA-256 hex digest of file contents

    Raises:
        No exceptions are raised. Files that cannot be accessed due to
        permissions, deletion during scan, or other OS errors are silently
        skipped.

    Example:
        >>> files = collect_file_metadata("/etc")
        >>> for f in files[:2]:
        ...     print(f"{f['path']}: {f['size_bytes']} bytes")
        /etc/hostname: 8 bytes
        /etc/hosts: 221 bytes

    Note:
        - Symlinks are skipped to avoid infinite loops from circular links
        - Results are sorted by path for consistent ordering
        - Large directories may take significant time due to hashing
    """
    results = []
    root_dir = Path(root_dir).expanduser().resolve()

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            filepath = Path(dirpath) / filename
            try:
                # Skip if not a regular file (e.g., device files, sockets)
                if not filepath.is_file():
                    continue

                # Skip symlinks to prevent infinite loops and security issues
                if filepath.is_symlink():
                    continue

                # Collect file stats
                s = filepath.stat()
                
                metadata = {
                    "path":        str(filepath.resolve()),
                    "size_bytes":  int(s.st_size),
                    "mtime":       float(s.st_mtime),
                    "permissions": oct(stat.S_IMODE(s.st_mode)),
                    "owner_uid":   int(s.st_uid),
                    "owner_gid":   int(s.st_gid),
                    "inode":       int(s.st_ino),
                    "hard_links":  int(s.st_nlink),
                    "sha256":      sha256_file(filepath),
                }
                results.append(metadata)

            except (PermissionError, FileNotFoundError, OSError):
                # File may disappear during scan or be inaccessible
                # Silently skip to allow scan to continue
                continue

    # Sort by path for consistent, reproducible output
    results.sort(key=lambda x: x["path"])
    return results
