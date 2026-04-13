# User Guide

A practical guide to using the File Integrity Monitoring (FIM) system.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Running Your First Scan](#running-your-first-scan)
3. [Comparing Scans](#comparing-scans)
4. [Common Use Cases](#common-use-cases)
5. [Working with the Database](#working-with-the-database)
6. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Linux/macOS/Windows with Python installed
- Read access to the directories you want to monitor

### Installation

```bash
# Clone the repository
git clone https://github.com/MarcoB517/File-Integrity-Monitoring.git
cd File-Integrity-Monitoring

# Verify Python version
python3 --version
```

No additional packages need to be installed — the system uses only Python's standard library.

---

## Running Your First Scan

### Basic Usage

```bash
python3 main.py /path/to/directory
```

### With a Label (Recommended)

```bash
python3 main.py /path/to/directory --label baseline
```

### Example

```bash
$ python3 main.py /home/marco/fim_test --label baseline
Scanned: /home/marco/fim_test
Files found: 3
Saved as scan ID: 1 (label: baseline)
```

Every scan is automatically saved to `fim.db` with a unique ID.

---

## Comparing Scans

### List All Scans

```bash
python3 test_comparator.py --list
```

Example output:
```
=== Available Scans ===

ID   Date/Time            Label        Files  Path
----------------------------------------------------------------------
1    2026-03-11 02:22:00  baseline     2      /home/marco/fim_test
2    2026-03-11 03:10:20  scan2        2      /home/marco/fim_test
3    2026-03-11 15:31:51  after-edit   3      /home/marco/fim_test
```

### Compare Two Scans

```bash
python3 test_comparator.py 1 3
```

Example output:
```
============================================================
COMPARING SCANS
============================================================

--- Scan 1 Details ---
  Time:       2026-03-11 02:22:00
  Path:       /home/marco/fim_test
  Label:      baseline
  Files:      2
  Total size: 29 bytes

--- Scan 3 Details ---
  Time:       2026-03-11 15:31:51
  Path:       /home/marco/fim_test
  Label:      after-edit
  Files:      3
  Total size: 45 bytes

=== File Integrity Comparison Report ===

ADDED (1 file):
  + /home/marco/fim_test/newfile.txt

DELETED (0 files):
  (none)

MODIFIED (1 file):
  ~ /home/marco/fim_test/config.txt
      old: 26e112d62ecc40c4...
      new: 24bcf336821a8464...

SUMMARY: 1 added, 0 deleted, 1 modified
```

### What the Report Tells You

| Symbol | Meaning |
|--------|---------|
| `+` | File was **added** (exists in new scan, not in old) |
| `-` | File was **deleted** (exists in old scan, not in new) |
| `~` | File was **modified** (same path, different hash) |

---

## Common Use Cases

### Use Case 1: Establishing a Baseline

When setting up monitoring for a new directory:

```bash
python3 main.py /home/marco/important_files --label baseline
```

### Use Case 2: Check for Changes Later

After some time passes, run another scan:

```bash
python3 main.py /home/marco/important_files --label weekly-check
```

Then compare:

```bash
python3 test_comparator.py --list   # Find the scan IDs
python3 test_comparator.py 1 2      # Compare them
```

### Use Case 3: Before/After System Changes

Before making changes:
```bash
python3 main.py /etc --label before-update
```

After making changes:
```bash
python3 main.py /etc --label after-update
```

Compare to see exactly what changed:
```bash
python3 test_comparator.py 1 2
```

---

## Working with the Database

### Where is the Database?

The database file `fim.db` is created in the directory where you run the commands.

### Viewing Scans with SQLite

```bash
sqlite3 fim.db "SELECT id, datetime(scan_time, 'unixepoch', 'localtime') AS time, label, root_path FROM scan_runs;"
```

### Using Comparator in Your Own Code

```python
from database import get_connection
from comparator import compare_scans, format_comparison_report

conn = get_connection("fim.db")

# Get the differences
diff = compare_scans(conn, old_scan_id=1, new_scan_id=2)

# Access raw data
print(f"Added files: {diff['added']}")
print(f"Deleted files: {diff['deleted']}")
print(f"Modified files: {diff['modified']}")

# Or print a formatted report
print(format_comparison_report(diff))
```

---

## Troubleshooting

### "Permission denied" errors

Some files may be unreadable due to permissions. The scanner skips these silently. To scan system directories, run as root:

```bash
sudo python3 main.py /etc --label system-baseline
```

### "No module named 'scanner'"

Make sure you're running from the project directory:

```bash
cd /path/to/File-Integrity-Monitoring
python3 main.py /target/dir
```

### Scan takes too long

Large directories with many files will take time, especially for hashing. Tips:

- Start with smaller directories to test
- The bottleneck is usually disk I/O for reading file contents

### Database is locked

SQLite only allows one writer at a time. Make sure no other process is accessing `fim.db`. Close any open database browsers or scripts.

### Symlinks are not being scanned

This is by design. The scanner deliberately skips symbolic links to prevent:
- Infinite loops from circular symlinks
- Double-counting files
- Potential security issues

If you need to monitor symlink targets, scan the target directory directly.

---

## Quick Reference

| Task | Command |
|------|---------|
| Run a scan | `python3 main.py /path --label name` |
| List all scans | `python3 test_comparator.py --list` |
| Compare scans | `python3 test_comparator.py 1 2` |

---

## Tips and Best Practices

1. **Always label your scans** — Makes it much easier to identify them later
2. **Scan at consistent times** — Helps reduce false positives from temp files
3. **Keep your database backed up** — The `fim.db` file contains your scan history
4. **Review changes regularly** — The tool detects changes; you interpret whether they're expected

---

## Next Steps

- Learn about the [Architecture](ARCHITECTURE.md) to understand how the system works
- Check the [README](README.md) for project status and roadmap
- Review the [CHANGELOG](CHANGELOG.md) for version history
