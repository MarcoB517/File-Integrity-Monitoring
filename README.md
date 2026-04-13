# File Integrity Monitoring System

A Python-based File Integrity Monitoring (FIM) tool for detecting unauthorized or unexpected file changes within a target directory.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Database Schema](#database-schema)
- [Example Queries](#example-queries)
- [Roadmap](#roadmap)
- [Author](#author)

---

## Overview

This project implements a lightweight File Integrity Monitoring system designed to:

- Establish a **baseline snapshot** of files in a directory
- Detect **additions, deletions, and modifications** over time
- Provide an **audit trail** of all scans stored in SQLite

FIM tools are a core component of cybersecurity infrastructure, used to identify unauthorized changes that may indicate user error, misconfiguration, or malicious activity.

---

## Features

| Feature | Status |
|---------|--------|
| Recursive directory scanning | ✅ Complete |
| SHA-256 file hashing | ✅ Complete |
| File metadata collection | ✅ Complete |
| SQLite storage with scan history | ✅ Complete |
| Baseline vs. current scan comparison | ✅ Complete |
| Command-line interface with `--label` | ✅ Complete |
| Exportable reports | 📋 Planned |
| Real-time monitoring | 📋 Planned |

---

## Project Structure

```
fim-project/
├── main.py             # Entry point / CLI (scans and saves to database)
├── scanner.py          # Recursive directory traversal & metadata collection
├── hashing.py          # SHA-256 hash computation
├── database.py         # SQLite connection, schema, and queries
├── comparator.py       # Scan comparison logic
├── test_comparator.py  # Helper script for comparing scans
├── fim.db              # SQLite database (generated at runtime)
├── README.md           # This file
├── ARCHITECTURE.md     # Technical design documentation
├── USER_GUIDE.md       # Usage instructions
└── CHANGELOG.md        # Version history
```

---

## Installation

### Prerequisites

- Python 3.8 or higher
- No external dependencies (uses only standard library)

### Setup

```bash
# Clone the repository
git clone https://github.com/MarcoB517/File-Integrity-Monitoring.git
cd File-Integrity-Monitoring

# (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate
```

---

## Quick Start

### Run a scan and save to database

```bash
python3 main.py /path/to/directory --label baseline
```

### Example output

```
Scanned: /home/marco/fim_test
Files found: 3
Saved as scan ID: 1 (label: baseline)
```

### Run another scan later

```bash
python3 main.py /path/to/directory --label after-changes
```

### List all scans

```bash
python3 test_comparator.py --list
```

### Compare two scans

```bash
python3 test_comparator.py 1 2
```

### Example comparison output

```
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

---

## How It Works

```
┌─────────────────┐
│   User Input    │
│  (target path)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    main.py      │  ← Entry point + saves to database
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   scanner.py    │  ← Walks directory tree
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   hashing.py    │  ← Computes SHA-256 per file
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  database.py    │  ← Stores snapshot in SQLite
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    fim.db       │
│  ┌───────────┐  │
│  │ scan_runs │  │  ← Scan metadata (time, path, label)
│  └───────────┘  │
│  ┌───────────┐  │
│  │file_snap- │  │  ← File metadata + hashes
│  │  shots    │  │
│  └───────────┘  │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  comparator.py  │  ← Diffs two snapshots
└─────────────────┘
```

1. **User specifies** a target directory and optional label
2. **Scanner** recursively walks the directory (skipping symlinks)
3. **Hashing module** computes SHA-256 for each file using chunked reads
4. **Database module** stores results as a timestamped snapshot
5. **Comparator** diffs two snapshots to find added, deleted, and modified files

---

## Database Schema

### `scan_runs` — Tracks each scan operation

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key (auto-increment) |
| `scan_time` | REAL | Unix timestamp of scan |
| `root_path` | TEXT | Directory that was scanned |
| `label` | TEXT | Optional label (e.g., "baseline") |

### `file_snapshots` — Stores file state at scan time

| Column | Type | Description |
|--------|------|-------------|
| `scan_run_id` | INTEGER | Foreign key → `scan_runs.id` |
| `path` | TEXT | Absolute file path |
| `size_bytes` | INTEGER | File size |
| `mtime` | REAL | Last modification time |
| `permissions` | TEXT | Octal permission string |
| `owner_uid` | INTEGER | Owner user ID |
| `owner_gid` | INTEGER | Owner group ID |
| `inode` | INTEGER | Filesystem inode |
| `hard_links` | INTEGER | Hard link count |
| `sha256` | TEXT | SHA-256 hash digest |

---

## Example Queries

### List all scans

```sql
SELECT id, datetime(scan_time, 'unixepoch', 'localtime') AS time, label, root_path
FROM scan_runs
ORDER BY id;
```

### Find new files (added between scan 1 and scan 2)

```sql
SELECT n.path
FROM file_snapshots n
LEFT JOIN file_snapshots o ON o.path = n.path AND o.scan_run_id = 1
WHERE n.scan_run_id = 2 AND o.path IS NULL;
```

### Find deleted files

```sql
SELECT o.path
FROM file_snapshots o
LEFT JOIN file_snapshots n ON n.path = o.path AND n.scan_run_id = 2
WHERE o.scan_run_id = 1 AND n.path IS NULL;
```

### Find modified files (same path, different hash)

```sql
SELECT o.path, o.sha256 AS old_hash, n.sha256 AS new_hash
FROM file_snapshots o
JOIN file_snapshots n ON o.path = n.path
WHERE o.scan_run_id = 1 AND n.scan_run_id = 2 AND o.sha256 != n.sha256;
```

---

## Roadmap

- [x] Core scanning and hashing
- [x] SQLite storage layer
- [x] CLI with `--label` flag
- [x] Automated comparison between scans
- [ ] Human-readable diff reports (export to file)
- [ ] Export to CSV/JSON
- [ ] Logging and error handling improvements
- [ ] Unit tests
- [ ] Real-time monitoring (future)

---

## Author

**Marco Buritica**  
CISC 4900 — Brooklyn College

---

## License

This project is for educational purposes as part of a semester-long coursework project.
