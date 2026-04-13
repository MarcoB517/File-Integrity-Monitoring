#!/usr/bin/env python3
"""
test_comparator.py — Demonstrates how to use the FIM comparison feature

Usage:
    python3 test_comparator.py                    # Compare scans 1 and 5
    python3 test_comparator.py 1 2                # Compare specific scans
    python3 test_comparator.py --list             # List all available scans
"""

import sqlite3
import sys
from datetime import datetime
from comparator import compare_scans, format_comparison_report, get_scan_summary


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
    
    # Convert timestamp to readable format
    scan_time = datetime.fromtimestamp(summary["scan_time"])
    
    print(f"\n--- Scan {scan_id} Details ---")
    print(f"  Time:       {scan_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Path:       {summary['root_path']}")
    print(f"  Label:      {summary['label'] or '(none)'}")
    print(f"  Files:      {summary['file_count']}")
    print(f"  Total size: {summary['total_size_bytes']:,} bytes")


def run_comparison(conn: sqlite3.Connection, old_id: int, new_id: int) -> None:
    """Compare two scans and print the results."""
    
    # Show details of both scans
    print("\n" + "=" * 60)
    print("COMPARING SCANS")
    print("=" * 60)
    
    show_scan_details(conn, old_id)
    show_scan_details(conn, new_id)
    
    # Run comparison
    diff = compare_scans(conn, old_scan_id=old_id, new_scan_id=new_id)
    
    # Print formatted report
    report = format_comparison_report(diff)
    print(report)
    
    # Return the raw diff for programmatic use
    return diff


def main():
    # Connect to database
    conn = sqlite3.connect("fim.db")
    
    # Parse command-line arguments
    if len(sys.argv) == 2 and sys.argv[1] == "--list":
        list_scans(conn)
        return
    
    elif len(sys.argv) == 3:
        # User specified two scan IDs
        old_id = int(sys.argv[1])
        new_id = int(sys.argv[2])
    
    else:
        # Default: compare scan 1 and 5
        old_id = 1
        new_id = 5
        print("Usage: python3 test_comparator.py [old_scan_id] [new_scan_id]")
        print("       python3 test_comparator.py --list")
        print(f"\nNo arguments provided, defaulting to: scan {old_id} vs scan {new_id}")
    
    # Run the comparison
    diff = run_comparison(conn, old_id, new_id)
    
    # Show how to access the raw data programmatically
    print("\n" + "=" * 60)
    print("RAW DATA (for programmatic use)")
    print("=" * 60)
    print(f"\ndiff['added']    = {diff['added']}")
    print(f"diff['deleted']  = {diff['deleted']}")
    print(f"diff['modified'] = {[(p, o[:8]+'...', n[:8]+'...') for p, o, n in diff['modified']]}")
    
    conn.close()


if __name__ == "__main__":
    main()
