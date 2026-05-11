#!/usr/bin/env python3
"""
main.py — File Integrity Monitoring System Entry Point

This module serves as the command-line interface and orchestration layer
for the FIM system. It parses command-line arguments, invokes the scanner,
saves results to the database, and prints a summary.

Usage:
    python3 main.py [directory]
    python3 main.py [directory] --label baseline

Arguments:
    directory   Path to the directory to scan (default: current directory)
    --label     Optional label for the scan (e.g., "baseline", "weekly")

Example:
    $ python3 main.py /home/user/documents --label baseline
    Scanned: /home/user/documents
    Files found: 42
    Saved as scan ID: 1 (label: baseline)

Author: Marco Buritica
Course: CISC 4900
"""

import sys
from pathlib import Path

from logger import get_logger
from scanner import collect_file_metadata
from database import get_connection, init_db, create_scan_run, insert_file_snapshots

logger = get_logger(__name__)


def main() -> None:
    """
    Main entry point for the File Integrity Monitoring CLI.

    Parses command-line arguments, runs a scan, saves to the database,
    and prints a summary. Exits with code 1 if the target directory is
    invalid or a database error occurs.

    Command-line Arguments:
        sys.argv[1]: Optional. The directory path to scan.
                     Defaults to current directory if not provided.
        --label:     Optional. A descriptive label for the scan.

    Exit Codes:
        0: Success
        1: Invalid directory or unexpected error
    """
    # Parse directory argument
    root = sys.argv[1] if len(sys.argv) > 1 else "."

    # Validate the directory exists
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        print(f"Error: Directory not found: {root}")
        logger.error(f"Scan aborted — directory not found: {root}")
        sys.exit(1)

    if not root_path.is_dir():
        print(f"Error: Path is not a directory: {root}")
        logger.error(f"Scan aborted — path is not a directory: {root}")
        sys.exit(1)

    # Parse optional label
    label = None
    if "--label" in sys.argv:
        label_index = sys.argv.index("--label") + 1
        if label_index < len(sys.argv):
            label = sys.argv[label_index]
        else:
            print("Error: --label flag requires a value (e.g. --label baseline)")
            logger.error("--label flag provided with no value")
            sys.exit(1)

    logger.info(f"Scan started — target: {root_path}, label: {label}")

    # Run the scan
    try:
        files = collect_file_metadata(str(root_path))
    except Exception as e:
        print(f"Error during scan: {e}")
        logger.error(f"Scan failed unexpectedly: {e}")
        sys.exit(1)

    # Save to database
    try:
        conn = get_connection("fim.db")
        init_db(conn)
        scan_id = create_scan_run(conn, str(root_path), label=label)
        insert_file_snapshots(conn, scan_id, files)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving to database: {e}")
        logger.error(f"Database error during scan save: {e}")
        sys.exit(1)

    # Print summary
    label_str = f" (label: {label})" if label else ""
    print(f"Scanned:       {root_path}")
    print(f"Files found:   {len(files)}")
    print(f"Saved as scan ID: {scan_id}{label_str}")
    print(f"Log written to:   fim.log")

    logger.info(f"Scan complete — scan_id={scan_id}, files={len(files)}, label={label}")


if __name__ == "__main__":
    main()
