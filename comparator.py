"""
comparator.py — Scan Comparison Module

This module provides functionality to compare two scan snapshots and
identify files that have been added, deleted, or modified between scans.

This is the core integrity monitoring capability — detecting changes
over time that may indicate normal updates, user mistakes, or potentially
malicious tampering.

Example:
    >>> from database import get_connection
    >>> from comparator import compare_scans
    >>> 
    >>> conn = get_connection("fim.db")
    >>> diff = compare_scans(conn, old_scan_id=1, new_scan_id=2)
    >>> 
    >>> print(f"Added: {len(diff['added'])} files")
    >>> print(f"Deleted: {len(diff['deleted'])} files")
    >>> print(f"Modified: {len(diff['modified'])} files")

Author: Marco Buritica
Course: CISC 4900
Status: In Development
"""

import sqlite3
from typing import Dict, List, Any, Tuple


def compare_scans(
    conn: sqlite3.Connection,
    old_scan_id: int,
    new_scan_id: int
) -> Dict[str, List[Any]]:
    """
    Compare two scan snapshots and return the differences.

    This function queries the file_snapshots table to identify files that
    have been added, deleted, or modified between two scans. Modification
    is detected by comparing SHA-256 hashes.

    Args:
        conn: An open SQLite database connection.
        old_scan_id: The ID of the baseline/earlier scan to compare from.
        new_scan_id: The ID of the newer scan to compare to.

    Returns:
        A dictionary containing three lists:
        {
            "added": [list of file paths that exist in new but not old],
            "deleted": [list of file paths that exist in old but not new],
            "modified": [list of tuples (path, old_hash, new_hash) for 
                        files that exist in both but have different hashes]
        }

    Example:
        >>> diff = compare_scans(conn, 1, 2)
        >>> for path in diff['added']:
        ...     print(f"+ {path}")
        >>> for path in diff['deleted']:
        ...     print(f"- {path}")
        >>> for path, old_hash, new_hash in diff['modified']:
        ...     print(f"~ {path}")

    Note:
        - Files with the same path but different sizes, permissions, or
          other metadata (but same hash) are NOT considered modified.
          Only content changes (hash changes) count as modifications.
        - Renamed files appear as one deletion + one addition.
    """
    # Find files that were added (exist in new scan but not in old)
    added_query = """
        SELECT n.path
        FROM file_snapshots n
        LEFT JOIN file_snapshots o 
            ON o.path = n.path AND o.scan_run_id = ?
        WHERE n.scan_run_id = ? 
            AND o.path IS NULL
        ORDER BY n.path;
    """
    added_rows = conn.execute(added_query, (old_scan_id, new_scan_id)).fetchall()
    added = [row[0] for row in added_rows]

    # Find files that were deleted (exist in old scan but not in new)
    deleted_query = """
        SELECT o.path
        FROM file_snapshots o
        LEFT JOIN file_snapshots n 
            ON n.path = o.path AND n.scan_run_id = ?
        WHERE o.scan_run_id = ? 
            AND n.path IS NULL
        ORDER BY o.path;
    """
    deleted_rows = conn.execute(deleted_query, (new_scan_id, old_scan_id)).fetchall()
    deleted = [row[0] for row in deleted_rows]

    # Find files that were modified (same path, different hash)
    modified_query = """
        SELECT o.path, o.sha256, n.sha256
        FROM file_snapshots o
        JOIN file_snapshots n 
            ON o.path = n.path
        WHERE o.scan_run_id = ? 
            AND n.scan_run_id = ? 
            AND o.sha256 != n.sha256
        ORDER BY o.path;
    """
    modified_rows = conn.execute(
        modified_query, (old_scan_id, new_scan_id)
    ).fetchall()
    modified = [(row[0], row[1], row[2]) for row in modified_rows]

    return {
        "added": added,
        "deleted": deleted,
        "modified": modified,
    }


def format_comparison_report(diff: Dict[str, List[Any]]) -> str:
    """
    Format a comparison result as a human-readable text report.

    Args:
        diff: The dictionary returned by compare_scans().

    Returns:
        A formatted string report suitable for printing or saving.

    Example:
        >>> diff = compare_scans(conn, 1, 2)
        >>> report = format_comparison_report(diff)
        >>> print(report)
        
        === File Integrity Comparison Report ===
        
        ADDED (2 files):
          + /home/user/new_file.txt
          + /home/user/another_new.txt
        
        DELETED (1 file):
          - /home/user/removed.txt
        
        MODIFIED (1 file):
          ~ /home/user/changed.txt
              old: abc123...
              new: def456...
        
        SUMMARY: 2 added, 1 deleted, 1 modified
    """
    lines = []
    lines.append("\n=== File Integrity Comparison Report ===\n")

    # Added files
    added_count = len(diff["added"])
    file_word = "file" if added_count == 1 else "files"
    lines.append(f"ADDED ({added_count} {file_word}):")
    if diff["added"]:
        for path in diff["added"]:
            lines.append(f"  + {path}")
    else:
        lines.append("  (none)")

    # Deleted files
    lines.append("")
    deleted_count = len(diff["deleted"])
    file_word = "file" if deleted_count == 1 else "files"
    lines.append(f"DELETED ({deleted_count} {file_word}):")
    if diff["deleted"]:
        for path in diff["deleted"]:
            lines.append(f"  - {path}")
    else:
        lines.append("  (none)")

    # Modified files
    lines.append("")
    modified_count = len(diff["modified"])
    file_word = "file" if modified_count == 1 else "files"
    lines.append(f"MODIFIED ({modified_count} {file_word}):")
    if diff["modified"]:
        for path, old_hash, new_hash in diff["modified"]:
            lines.append(f"  ~ {path}")
            lines.append(f"      old: {old_hash[:16]}...")
            lines.append(f"      new: {new_hash[:16]}...")
    else:
        lines.append("  (none)")

    # Summary
    lines.append("")
    lines.append(
        f"SUMMARY: {added_count} added, {deleted_count} deleted, "
        f"{modified_count} modified"
    )

    return "\n".join(lines)


def get_scan_summary(conn: sqlite3.Connection, scan_id: int) -> Dict[str, Any]:
    """
    Get summary information about a specific scan.

    Args:
        conn: An open SQLite database connection.
        scan_id: The ID of the scan to summarize.

    Returns:
        A dictionary containing:
        {
            "scan_id": int,
            "scan_time": float (Unix timestamp),
            "root_path": str,
            "label": str or None,
            "file_count": int,
            "total_size_bytes": int
        }

    Raises:
        ValueError: If no scan exists with the given ID.

    Example:
        >>> summary = get_scan_summary(conn, 1)
        >>> print(f"Scan {summary['scan_id']}: {summary['file_count']} files")
    """
    # Get scan metadata
    scan_row = conn.execute(
        "SELECT id, scan_time, root_path, label FROM scan_runs WHERE id = ?",
        (scan_id,)
    ).fetchone()

    if not scan_row:
        raise ValueError(f"No scan found with ID {scan_id}")

    # Get file statistics
    stats_row = conn.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(size_bytes), 0)
        FROM file_snapshots
        WHERE scan_run_id = ?
        """,
        (scan_id,)
    ).fetchone()

    return {
        "scan_id": scan_row[0],
        "scan_time": scan_row[1],
        "root_path": scan_row[2],
        "label": scan_row[3],
        "file_count": stats_row[0],
        "total_size_bytes": stats_row[1],
    }
