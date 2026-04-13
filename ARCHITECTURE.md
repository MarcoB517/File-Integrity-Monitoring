# Architecture Documentation

This document describes the technical design and architecture of the File Integrity Monitoring (FIM) system.

---

## System Overview

The FIM system is designed with a modular architecture that separates concerns into distinct components:

```
┌──────────────────────────────────────────────────────────────────┐
│                        FIM SYSTEM                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────┐   │
│  │ main.py │───▶│scanner. │───▶│hashing. │    │ comparator. │   │
│  │  (CLI)  │    │   py    │    │   py    │    │     py      │   │
│  └────┬────┘    └────┬────┘    └─────────┘    └──────┬──────┘   │
│       │              │                               │          │
│       │              │                               │          │
│       ▼              ▼                               ▼          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    database.py                          │    │
│  │         (SQLite connection + query layer)               │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│                            │                                    │
│                            ▼                                    │
│                     ┌─────────────┐                             │
│                     │   fim.db    │                             │
│                     │  (SQLite)   │                             │
│                     └─────────────┘                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Module Descriptions

### `main.py` — Entry Point

**Purpose:** Command-line interface and orchestration layer.

**Responsibilities:**
- Parse command-line arguments (target directory, optional label)
- Invoke the scanner
- Save results to the database
- Print summary to stdout

**Current behavior:**
```python
# Parse arguments
root = sys.argv[1] if len(sys.argv) > 1 else "."
label = None  # parsed from --label flag if provided

# Run the scan
files = collect_file_metadata(root)

# Save to database
conn = get_connection("fim.db")
init_db(conn)
scan_id = create_scan_run(conn, root, label=label)
insert_file_snapshots(conn, scan_id, files)
conn.commit()

# Print summary
print(f"Saved as scan ID: {scan_id}")
```

**CLI flags:**
- `--label NAME`: Tag the scan with a descriptive label (e.g., "baseline", "weekly")

---

### `scanner.py` — Directory Traversal

**Purpose:** Recursively scan a directory tree and collect file metadata.

**Key function:**
```python
def collect_file_metadata(root_dir) -> list[dict]
```

**Behavior:**
1. Resolves the root path to an absolute path
2. Uses `os.walk()` for recursive traversal
3. For each file:
   - Skips non-regular files
   - Skips symbolic links (deliberate design decision)
   - Collects metadata via `os.stat()`
   - Computes SHA-256 hash via `hashing.sha256_file()`
4. Returns sorted list of file metadata dictionaries

**Metadata collected per file:**

| Field | Source | Description |
|-------|--------|-------------|
| `path` | `Path.resolve()` | Absolute file path |
| `size_bytes` | `st_size` | File size in bytes |
| `mtime` | `st_mtime` | Last modification timestamp |
| `permissions` | `st_mode` | Octal permission string |
| `owner_uid` | `st_uid` | Owner user ID |
| `owner_gid` | `st_gid` | Owner group ID |
| `inode` | `st_ino` | Filesystem inode number |
| `hard_links` | `st_nlink` | Hard link count |
| `sha256` | Computed | SHA-256 hash digest |

**Design decisions:**

- **Symlink skipping:** Prevents infinite loops from circular symlinks and avoids double-counting files. This is a deliberate security/stability choice.
- **Silent exception handling:** Files that disappear during scan or are inaccessible are skipped without crashing.

---

### `hashing.py` — Cryptographic Hashing

**Purpose:** Compute SHA-256 hashes of files safely and efficiently.

**Key function:**
```python
def sha256_file(filepath: str | Path, chunk_size: int = 1024 * 1024) -> str
```

**Behavior:**
1. Opens file in binary mode
2. Reads in chunks (default 1 MB)
3. Updates hash incrementally
4. Returns hex digest string

**Design decisions:**

- **SHA-256 over MD5:** SHA-256 was chosen because MD5 is considered cryptographically broken. SHA-256 provides stronger collision resistance.
- **Chunked reading:** Prevents memory exhaustion when hashing large files. A 10 GB file would crash if loaded entirely into memory.
- **Configurable chunk size:** Allows tuning for different environments (smaller chunks for memory-constrained systems).

---

### `database.py` — Persistence Layer

**Purpose:** Manage SQLite database connections, schema, and queries.

**Key functions:**

| Function | Description |
|----------|-------------|
| `get_connection(db_path)` | Opens SQLite connection with FK enforcement |
| `init_db(conn)` | Creates tables and indexes if not exist |
| `create_scan_run(conn, root_path, label)` | Inserts new scan record, returns ID |
| `insert_file_snapshots(conn, scan_run_id, files)` | Bulk inserts file metadata |

**Schema design:**

```
┌─────────────────────────────────────────────────────────────┐
│                       scan_runs                             │
├─────────────────────────────────────────────────────────────┤
│ id (PK)  │ scan_time  │ root_path        │ label           │
│ INTEGER  │ REAL       │ TEXT             │ TEXT (nullable) │
├──────────┼────────────┼──────────────────┼─────────────────┤
│ 1        │ 1712345678 │ /home/user/docs  │ baseline        │
│ 2        │ 1712432078 │ /home/user/docs  │ weekly          │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ 1:N
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     file_snapshots                          │
├─────────────────────────────────────────────────────────────┤
│ scan_run_id (PK,FK) │ path (PK)  │ sha256   │ size │ ...   │
│ INTEGER             │ TEXT       │ TEXT     │ INT  │       │
├─────────────────────┼────────────┼──────────┼──────┼───────┤
│ 1                   │ /docs/a.tx │ abc123...│ 1024 │ ...   │
│ 1                   │ /docs/b.tx │ def456...│ 2048 │ ...   │
│ 2                   │ /docs/a.tx │ abc123...│ 1024 │ ...   │
│ 2                   │ /docs/c.tx │ ghi789...│ 512  │ ...   │
└─────────────────────────────────────────────────────────────┘
```

**Design decisions:**

- **Two-table schema:** Separates scan metadata from file snapshots. This allows clean querying of scan history and enables efficient comparisons between any two scans.
- **Composite primary key:** `(scan_run_id, path)` ensures each file appears once per scan.
- **Foreign key with CASCADE:** Deleting a scan automatically removes its snapshots.
- **Indexes on `path` and `sha256`:** Speeds up comparison queries and duplicate detection.

---

### `comparator.py` — Diff Engine

**Purpose:** Compare two scan snapshots and identify changes.

**Key functions:**

| Function | Description |
|----------|-------------|
| `compare_scans(conn, old_id, new_id)` | Returns dict with added, deleted, modified files |
| `format_comparison_report(diff)` | Formats diff as human-readable text |
| `get_scan_summary(conn, scan_id)` | Returns metadata and stats for a scan |

**Core function:**

```python
def compare_scans(conn, old_scan_id: int, new_scan_id: int) -> dict:
    """
    Returns:
        {
            "added": [list of new file paths],
            "deleted": [list of removed file paths],
            "modified": [list of tuples (path, old_hash, new_hash)]
        }
    """
```

**Comparison logic:**

| Change Type | Detection Method |
|-------------|------------------|
| Added | File exists in new scan but not in old |
| Deleted | File exists in old scan but not in new |
| Modified | File exists in both, but `sha256` differs |

---

### `test_comparator.py` — CLI Helper

**Purpose:** Convenient command-line wrapper for comparing scans.

**Usage:**
```bash
python3 test_comparator.py --list        # List all scans
python3 test_comparator.py 1 2           # Compare scan 1 to scan 2
```

---

## Data Flow

### Scan Operation

```
1. User runs: python3 main.py /target/dir --label baseline

2. main.py:
   └─▶ parses arguments (path, label)
   └─▶ calls scanner.collect_file_metadata("/target/dir")

3. scanner.py:
   └─▶ os.walk() traverses directory tree
   └─▶ for each file:
       └─▶ stat() collects metadata
       └─▶ hashing.sha256_file() computes hash
   └─▶ returns list of file dicts

4. main.py:
   └─▶ calls database.get_connection("fim.db")
   └─▶ calls database.init_db(conn)
   └─▶ calls database.create_scan_run(conn, path, label)
   └─▶ calls database.insert_file_snapshots(conn, scan_id, files)
   └─▶ conn.commit()
   └─▶ prints summary
```

### Comparison Operation

```
1. User runs: python3 test_comparator.py 1 2

2. test_comparator.py:
   └─▶ connects to fim.db
   └─▶ calls comparator.compare_scans(conn, 1, 2)

3. comparator.py:
   └─▶ queries file_snapshots for scan 1
   └─▶ queries file_snapshots for scan 2
   └─▶ computes set differences via SQL JOINs
   └─▶ returns {added, deleted, modified}

4. test_comparator.py:
   └─▶ calls format_comparison_report(diff)
   └─▶ prints report
```

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Symlink attacks | Symlinks are skipped entirely |
| Hash collisions | SHA-256 has no known practical collisions |
| Large file DoS | Chunked hashing prevents memory exhaustion |
| SQL injection | Parameterized queries used throughout |
| Race conditions | Files that disappear mid-scan are gracefully skipped |

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Directory scan | O(n) | n = number of files |
| File hashing | O(m) | m = total bytes across all files |
| Database insert | O(n) | Bulk insert via `executemany` |
| Comparison query | O(n) | JOIN on indexed columns |

**Bottleneck:** Hashing large files is the slowest operation. For a directory with many large files, scan time is dominated by disk I/O.

---

## Future Architecture Considerations

### Real-time Monitoring

If real-time monitoring is added, the architecture would expand to include:

```
┌─────────────────┐
│  inotify/FSEvents│  ← OS-level file change notifications
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   watcher.py    │  ← Event handler daemon
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  database.py    │  ← Log events in real-time
└─────────────────┘
```

### Reporting Layer

A future reporting module could generate:

- Human-readable text reports
- CSV exports
- JSON API responses
- HTML dashboards

---

## Dependencies

The system uses **only Python standard library** modules:

| Module | Purpose |
|--------|---------|
| `os` | Directory traversal |
| `stat` | File permission parsing |
| `pathlib` | Path manipulation |
| `hashlib` | SHA-256 hashing |
| `sqlite3` | Database operations |
| `time` | Timestamps |
| `datetime` | Human-readable timestamps |
| `sys` | CLI arguments |

**No external dependencies required.**
