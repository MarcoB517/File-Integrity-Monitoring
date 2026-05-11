#!/usr/bin/env python3
"""
test_comparator.py — CLI Helper for Comparing Scans

Usage:
    python3 test_comparator.py --list
    python3 test_comparator.py 1 2
    python3 test_comparator.py 1 2 --export txt
    python3 test_comparator.py 1 2 --export csv
    python3 test_comparator.py 1 2 --export json
    python3 test_comparator.py 1 2 --export txt --output reports/my_report.txt

Author: Marco Buritica
Course: CISC 4900
"""

import sqlite3
import sys
from datetime import datetime

from comparator import compare_scans, format_comparison_report, get_scan_summary
from reporter import export_txt, export_csv, export_json


def list_scans(conn: sqlite3.Connection) -> None:
    """Display all available scans in the database."""
    print("\n=== Available Scans ===\n")
    print(f"{'ID':<4} {'Date/Time':<20} {'Label':<12} {'Files':<6} {'Path'}")
    print("-" * 70)

    scans = conn.execute("""
        SELECT
            sr.id,
            datetime(sr.scan_time, 'unixepoch', 'localtime') as time,
            sr.label,
            sr.root_path,
            COUNT(fs.path) as file_count
        FROM scan_runs sr
        LEFT JOIN file_snapshots fs ON sr.id = fs.scan_run_id
        GROUP BY sr.id
        ORDER BY sr.id
    """).fetchall()

    for scan in scans:
        scan_id, time, label, path, count = scan
        label = label or "(none)"
        print(f"{scan_id:<4} {time:<20} {label:<12} {count:<6} {path}")
    print()


def show_scan_details(conn: sqlite3.Connection, scan_id: int) -> None:
    """Show detailed info about a specific scan."""
    summary = get_scan_summary(conn, scan_id)
    scan_time = datetime.fromtimestamp(summary["scan_time"])

    print(f"\n--- Scan {scan_id} Details ---")
    print(f"  Time:       {scan_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Path:       {summary['root_path']}")
    print(f"  Label:      {summary['label'] or '(none)'}")
    print(f"  Files:      {summary['file_count']}")
    print(f"  Total size: {summary['total_size_bytes']:,} bytes")


def run_comparison(
    conn: sqlite3.Connection,
    old_id: int,
    new_id: int,
    export_fmt: str = None,
    output_path: str = None,
) -> None:
    """Compare two scans, print the report, and optionally export it."""

    print("\n" + "=" * 60)
    print("COMPARING SCANS")
    print("=" * 60)

    try:
        show_scan_details(conn, old_id)
        show_scan_details(conn, new_id)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    diff = compare_scans(conn, old_scan_id=old_id, new_scan_id=new_id)

    # Print report to terminal
    print(format_comparison_report(diff))

    # Export if requested
    if export_fmt:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"report_{old_id}_vs_{new_id}_{timestamp}"

        if export_fmt == "txt":
            path = output_path or f"reports/{default_name}.txt"
            export_txt(diff, path, old_scan_id=old_id, new_scan_id=new_id)

        elif export_fmt == "csv":
            path = output_path or f"reports/{default_name}.csv"
            export_csv(diff, path)

        elif export_fmt == "json":
            path = output_path or f"reports/{default_name}.json"
            export_json(diff, path, old_scan_id=old_id, new_scan_id=new_id)

        else:
            print(f"Unknown export format: {export_fmt}")
            print("Valid formats: txt, csv, json")
            sys.exit(1)


def main():
    conn = sqlite3.connect("fim.db")

    # --list
    if len(sys.argv) == 2 and sys.argv[1] == "--list":
        list_scans(conn)
        return

    # Need at least two scan IDs
    if len(sys.argv) < 3 or not sys.argv[1].isdigit() or not sys.argv[2].isdigit():
        print("Usage:")
        print("  python3 test_comparator.py --list")
        print("  python3 test_comparator.py <old_id> <new_id>")
        print("  python3 test_comparator.py <old_id> <new_id> --export txt|csv|json")
        print("  python3 test_comparator.py <old_id> <new_id> --export txt --output path/to/file.txt")
        sys.exit(1)

    old_id = int(sys.argv[1])
    new_id = int(sys.argv[2])

    # Parse --export flag
    export_fmt = None
    if "--export" in sys.argv:
        export_index = sys.argv.index("--export") + 1
        if export_index < len(sys.argv):
            export_fmt = sys.argv[export_index]
        else:
            print("Error: --export requires a format: txt, csv, or json")
            sys.exit(1)

    # Parse --output flag
    output_path = None
    if "--output" in sys.argv:
        output_index = sys.argv.index("--output") + 1
        if output_index < len(sys.argv):
            output_path = sys.argv[output_index]
        else:
            print("Error: --output requires a file path")
            sys.exit(1)

    run_comparison(conn, old_id, new_id, export_fmt=export_fmt, output_path=output_path)
    conn.close()


if __name__ == "__main__":
    main()
