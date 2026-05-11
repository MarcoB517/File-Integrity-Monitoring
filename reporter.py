"""
reporter.py — Report Export Module

Provides functionality to export scan comparison results to different
file formats: plain text (.txt), CSV (.csv), and JSON (.json).

Usage:
    from reporter import export_txt, export_csv, export_json

    diff = compare_scans(conn, 1, 2)

    export_txt(diff, "report.txt", old_scan_id=1, new_scan_id=2)
    export_csv(diff, "report.csv")
    export_json(diff, "report.json", old_scan_id=1, new_scan_id=2)

Author: Marco Buritica
Course: CISC 4900
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from logger import get_logger

logger = get_logger(__name__)


def _timestamp() -> str:
    """Return current datetime as a readable string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def export_txt(
    diff: Dict[str, List[Any]],
    output_path: str,
    old_scan_id: int = None,
    new_scan_id: int = None,
) -> None:
    """
    Export a comparison report as a plain text file.

    Args:
        diff: The dictionary returned by compare_scans().
        output_path: Path to write the .txt file.
        old_scan_id: Optional. ID of the baseline scan (for header).
        new_scan_id: Optional. ID of the newer scan (for header).

    Raises:
        OSError: If the file cannot be written.

    Example:
        >>> export_txt(diff, "reports/report.txt", old_scan_id=1, new_scan_id=2)
        Report saved: reports/report.txt
    """
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        added    = diff["added"]
        deleted  = diff["deleted"]
        modified = diff["modified"]

        with path.open("w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("  FILE INTEGRITY MONITORING — COMPARISON REPORT\n")
            f.write("=" * 60 + "\n")
            f.write(f"  Generated: {_timestamp()}\n")
            if old_scan_id and new_scan_id:
                f.write(f"  Comparing: Scan {old_scan_id} → Scan {new_scan_id}\n")
            f.write("=" * 60 + "\n\n")

            # Added
            f.write(f"ADDED ({len(added)} {'file' if len(added) == 1 else 'files'}):\n")
            if added:
                for p in added:
                    f.write(f"  + {p}\n")
            else:
                f.write("  (none)\n")

            # Deleted
            f.write(f"\nDELETED ({len(deleted)} {'file' if len(deleted) == 1 else 'files'}):\n")
            if deleted:
                for p in deleted:
                    f.write(f"  - {p}\n")
            else:
                f.write("  (none)\n")

            # Modified
            f.write(f"\nMODIFIED ({len(modified)} {'file' if len(modified) == 1 else 'files'}):\n")
            if modified:
                for file_path, old_hash, new_hash in modified:
                    f.write(f"  ~ {file_path}\n")
                    f.write(f"      old hash: {old_hash}\n")
                    f.write(f"      new hash: {new_hash}\n")
            else:
                f.write("  (none)\n")

            # Summary
            f.write("\n" + "-" * 60 + "\n")
            f.write(
                f"SUMMARY: {len(added)} added, {len(deleted)} deleted, "
                f"{len(modified)} modified\n"
            )

        logger.info(f"TXT report saved: {path}")
        print(f"Report saved: {path}")

    except OSError as e:
        logger.error(f"Failed to write TXT report to {output_path}: {e}")
        raise


def export_csv(
    diff: Dict[str, List[Any]],
    output_path: str,
) -> None:
    """
    Export a comparison report as a CSV file.

    Each row contains: change_type, path, old_hash, new_hash.
    Added and deleted files have empty hash fields where not applicable.

    Args:
        diff: The dictionary returned by compare_scans().
        output_path: Path to write the .csv file.

    Raises:
        OSError: If the file cannot be written.

    Example:
        >>> export_csv(diff, "reports/report.csv")
        Report saved: reports/report.csv
    """
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["change_type", "path", "old_hash", "new_hash"])

            for p in diff["added"]:
                writer.writerow(["ADDED", p, "", ""])

            for p in diff["deleted"]:
                writer.writerow(["DELETED", p, "", ""])

            for file_path, old_hash, new_hash in diff["modified"]:
                writer.writerow(["MODIFIED", file_path, old_hash, new_hash])

        logger.info(f"CSV report saved: {path}")
        print(f"Report saved: {path}")

    except OSError as e:
        logger.error(f"Failed to write CSV report to {output_path}: {e}")
        raise


def export_json(
    diff: Dict[str, List[Any]],
    output_path: str,
    old_scan_id: int = None,
    new_scan_id: int = None,
) -> None:
    """
    Export a comparison report as a JSON file.

    Args:
        diff: The dictionary returned by compare_scans().
        output_path: Path to write the .json file.
        old_scan_id: Optional. ID of the baseline scan.
        new_scan_id: Optional. ID of the newer scan.

    Raises:
        OSError: If the file cannot be written.

    Example:
        >>> export_json(diff, "reports/report.json", old_scan_id=1, new_scan_id=2)
        Report saved: reports/report.json
    """
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "generated": _timestamp(),
            "old_scan_id": old_scan_id,
            "new_scan_id": new_scan_id,
            "summary": {
                "added":    len(diff["added"]),
                "deleted":  len(diff["deleted"]),
                "modified": len(diff["modified"]),
            },
            "added":   diff["added"],
            "deleted": diff["deleted"],
            "modified": [
                {"path": p, "old_hash": o, "new_hash": n}
                for p, o, n in diff["modified"]
            ],
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"JSON report saved: {path}")
        print(f"Report saved: {path}")

    except OSError as e:
        logger.error(f"Failed to write JSON report to {output_path}: {e}")
        raise
