#!/usr/bin/env python3
"""
main.py — File Integrity Monitoring System Entry Point

This module serves as the command-line interface and orchestration layer
for the FIM system. It parses command-line arguments, invokes the scanner,
and saves results to the database.

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

from scanner import collect_file_metadata
from database import get_connection, init_db, create_scan_run, insert_file_snapshots


def main() -> None:
    """
    Main entry point for the File Integrity Monitoring CLI.

    Parses command-line arguments to determine the target directory,
    runs a scan, saves results to the database, and prints a summary.

    Command-line Arguments:
        sys.argv[1]: Optional. The directory path to scan.
                     If not provided, defaults to the current directory (".").
        --label:     Optional. A descriptive label for the scan.

    Output:
        Prints a summary showing files found and the assigned scan ID.

    Exit Codes:
        0: Success (implicit)

    Example:
        # Scan current directory
        $ python3 main.py
        
        # Scan specific directory with label
        $ python3 main.py /etc --label baseline
    """
    # Parse command-line arguments
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    
    # Check for optional label
    label = None
    if "--label" in sys.argv:
        label_index = sys.argv.index("--label") + 1
        if label_index < len(sys.argv):
            label = sys.argv[label_index]
    
    # Run the scan
    files = collect_file_metadata(root)

    # Save to database
    conn = get_connection("fim.db")
    init_db(conn)
    scan_id = create_scan_run(conn, root, label=label)
    insert_file_snapshots(conn, scan_id, files)
    conn.commit()
    conn.close()

    # Print summary
    print(f"Scanned: {root}")
    print(f"Files found: {len(files)}")
    print(f"Saved as scan ID: {scan_id}" + (f" (label: {label})" if label else ""))


if __name__ == "__main__":
    main()