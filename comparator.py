"""
comparator.py — Scan Comparison Module

Provides functionality to compare two scan snapshots and identify
files that have been added, deleted, or modified between scans.

Author: Marco Buritica
Course: CISC 4900
"""

import sqlite3
from typing import Dict, List, Any, Tuple

from logger import get_logger

logger = get_logger(__name__)


def compare_scans(
    conn: sqlite3.Connection,
    old_scan_id: int,
    new_scan_id: int
) -> Dict[str, List[Any]]:
    """
    Compare two scan snapshots and return the differences.

    Args:
        conn: An open SQLite database connection.
        old_scan_id: The ID of the baseline/earlier scan.
        new_scan_id: The ID of the newer scan.

    Returns:
        A dictionary with keys: "added", "deleted", "modified".

    Raises:
        ValueError: If either scan ID does not exist in the database.
        sqlite3.Error: If a database query fails.
    """
    # Validate both scan IDs exist
    for scan_id in (old_scan_id, new_scan_id):
        row = conn.execute(
            "SELECT id FROM scan_runs WHERE id = ?", (scan_id,)
        ).fetchone()
        if not row:
            logger.error(f"Scan ID not found: {scan_id}")
            raise ValueError(f"No scan found with ID {scan_id}")

    logger.info(f"Comparing scans: {old_scan_id} → {new_scan_id}")

    try:
        # Added files
        added_rows = conn.execute("""
            SELECT n.path
            FROM file_snapshots n
            LEFT JOIN file_snapshots o ON o.path = n.path AND o.scan_run_id = ?
            WHERE n.scan_run_id = ? AND o.path IS NULL
            ORDER BY n.path
        """, (old_scan_id, new_scan_id)).fetchall()
        added = [row[0] for row in added_rows]

        # Deleted files
        deleted_rows = conn.execute("""
            SELECT o.path
            FROM file_snapshots o
            LEFT JOIN file_snapshots n ON n.path = o.path AND n.scan_run_id = ?
            WHERE o.scan_run_id = ? AND n.path IS NULL
            ORDER BY o.path
        """, (new_scan_id, old_scan_id)).fetchall()
        deleted = [row[0] for row in deleted_rows]

        # Modified files
        modified_rows = conn.execute("""
            SELECT o.path, o.sha256, n.sha256
            FROM file_snapshots o
            JOIN file_snapshots n ON o.path = n.path
            WHERE o.scan_run_id = ? AND n.scan_run_id = ? AND o.sha256 != n.sha256
            ORDER BY o.path
        """, (old_scan_id, new_scan_id)).fetchall()
        modified = [(row[0], row[1], row[2]) for row in modified_rows]

    except sqlite3.Error as e:
        logger.error(f"Database error during comparison: {e}")
        raise

    logger.info(
        f"Comparison complete: {len(added)} added, "
        f"{len(deleted)} deleted, {len(modified)} modified"
    )

    return {"added": added, "deleted": deleted, "modified": modified}


def format_comparison_report(diff: Dict[str, List[Any]]) -> str:
    """
    Format a comparison result as a human-readable text report.

    Args:
        diff: The dictionary returned by compare_scans().

    Returns:
        A formatted string report suitable for printing or saving.
    """
    lines = []
    lines.append("\n=== File Integrity Comparison Report ===\n")

    added_count = len(diff["added"])
    lines.append(f"ADDED ({added_count} {'file' if added_count == 1 else 'files'}):")
    for path in diff["added"]:
        lines.append(f"  + {path}")
    if not diff["added"]:
        lines.append("  (none)")

    lines.append("")
    deleted_count = len(diff["deleted"])
    lines.append(f"DELETED ({deleted_count} {'file' if deleted_count == 1 else 'files'}):")
    for path in diff["deleted"]:
        lines.append(f"  - {path}")
    if not diff["deleted"]:
        lines.append("  (none)")

    lines.append("")
    modified_count = len(diff["modified"])
    lines.append(f"MODIFIED ({modified_count} {'file' if modified_count == 1 else 'files'}):")
    for path, old_hash, new_hash in diff["modified"]:
        lines.append(f"  ~ {path}")
        lines.append(f"      old: {old_hash[:16]}...")
        lines.append(f"      new: {new_hash[:16]}...")
    if not diff["modified"]:
        lines.append("  (none)")

    lines.append("")
    lines.append(
        f"SUMMARY: {added_count} added, {deleted_count} deleted, {modified_count} modified"
    )

    return "\n".join(lines)


def get_scan_summary(conn: sqlite3.Connection, scan_id: int) -> Dict[str, Any]:
    """
    Get summary information about a specific scan.

    Args:
        conn: An open SQLite database connection.
        scan_id: The ID of the scan to summarize.

    Returns:
        A dictionary with scan_id, scan_time, root_path, label,
        file_count, and total_size_bytes.

    Raises:
        ValueError: If no scan exists with the given ID.
        sqlite3.Error: If a database query fails.
    """
    try:
        scan_row = conn.execute(
            "SELECT id, scan_time, root_path, label FROM scan_runs WHERE id = ?",
            (scan_id,)
        ).fetchone()

        if not scan_row:
            logger.error(f"Scan ID not found: {scan_id}")
            raise ValueError(f"No scan found with ID {scan_id}")

        stats_row = conn.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(size_bytes), 0)
            FROM file_snapshots WHERE scan_run_id = ?
            """,
            (scan_id,)
        ).fetchone()

    except sqlite3.Error as e:
        logger.error(f"Database error fetching scan summary for id={scan_id}: {e}")
        raise

    return {
        "scan_id":          scan_row[0],
        "scan_time":        scan_row[1],
        "root_path":        scan_row[2],
        "label":            scan_row[3],
        "file_count":       stats_row[0],
        "total_size_bytes": stats_row[1],
    }
