"""
scanner.py — Directory Traversal and Metadata Collection Module

This module provides functionality to recursively scan a directory tree
and collect metadata for each regular file found.

Author: Marco Buritica
Course: CISC 4900
"""

import os
import stat
from pathlib import Path
from typing import List, Dict, Any

from hashing import sha256_file
from logger import get_logger

logger = get_logger(__name__)


def collect_file_metadata(root_dir: str) -> List[Dict[str, Any]]:
    """
    Recursively scan a directory and collect metadata for all regular files.

    Args:
        root_dir: Path to the directory to scan.

    Returns:
        A sorted list of dictionaries containing file metadata:
        path, size_bytes, mtime, permissions, owner_uid, owner_gid,
        inode, hard_links, sha256.

    Raises:
        FileNotFoundError: If root_dir does not exist.
        NotADirectoryError: If root_dir is not a directory.
    """
    results = []
    skipped = 0

    root_path = Path(root_dir).expanduser().resolve()

    if not root_path.exists():
        logger.error(f"Directory not found: {root_path}")
        raise FileNotFoundError(f"Directory not found: {root_path}")

    if not root_path.is_dir():
        logger.error(f"Path is not a directory: {root_path}")
        raise NotADirectoryError(f"Not a directory: {root_path}")

    logger.info(f"Scan started: {root_path}")

    for dirpath, dirnames, filenames in os.walk(root_path):
        for filename in filenames:
            filepath = Path(dirpath) / filename
            try:
                # Skip non-regular files
                if not filepath.is_file():
                    logger.debug(f"Skipped (not a regular file): {filepath}")
                    skipped += 1
                    continue

                # Skip symlinks to prevent infinite loops
                if filepath.is_symlink():
                    logger.debug(f"Skipped (symlink): {filepath}")
                    skipped += 1
                    continue

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
                logger.debug(f"Scanned: {filepath}")

            except PermissionError:
                logger.warning(f"Permission denied, skipping: {filepath}")
                skipped += 1
            except FileNotFoundError:
                logger.warning(f"File disappeared during scan, skipping: {filepath}")
                skipped += 1
            except OSError as e:
                logger.warning(f"OS error on {filepath}: {e}")
                skipped += 1

    results.sort(key=lambda x: x["path"])

    logger.info(f"Scan complete: {len(results)} files scanned, {skipped} skipped")
    return results
