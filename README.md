# Project Title
File Integrity Monitoring System

## Overview
This project is a Python based File Integrity Monitoring (FIM) system designed to detect changes in files within a target directory. The system collects file metadata, computes SHA-256 hashes, stores scan results, and compares snapshots over time to identify created, deleted, and modified files. The goal of the project is to demonstrate practical cybersecurity concepts such as integrity verification, change detection, and audit logging using a lightweight local database.

## Objectives
- Monitor files in a selected directory
- Record file metadata such as path, size, permissions, owner, inode, and timestamps
- Compute SHA-256 hashes to verify integrity
- Store scan results in SQLite
- Compare two scan runs to detect:
  - new files
  - deleted files
  - modified files
- Provide a foundation for future alerting and reporting features

## Features Completed So Far
- Recursive file scanning
- SHA-256 hashing of files
- SQLite database setup
- Tables for scan runs and file snapshots
- Queries for comparing scan results between two scan runs

## Planned Features
- Command-line options for labeling scans
- Better reporting of scan differences
- Exportable reports
- Exception handling and logging improvements
- Unit testing
- Possible real-time monitoring in a future version

## Tech Stack
- Language: Python3
- Database: SQLite
- Environment: Debian Linux VM
- Version Control: GitHub

## How It Works
1. The user selects a target directory to scan.
2. The scanner scans through the directory recursively.
3. For each file, the system collects metadata and computes a SHA-256 hash.
4. The scan results are saved as a snapshot in SQLite.
5. A later scan can be compared against an earlier baseline.
6. The comparison identifies file additions, deletions, and modifications.

## Example Use Case
A user performs an initial baseline scan on a directory. Later, after files have been edited, added, or deleted, the user runs a second scan. The system compares the two snapshots and highlights what changed, allowing the user to verify whether the changes were expected.

### Example Command
```bash
python3 main.py /home/marco/fim_test
```

## Example Database Queries
### Show all scan runs
```sql
SELECT id, datetime(scan_time, 'unixepoch') AS scan_time, label, root_path
FROM scan_runs
ORDER BY id;
```

### Show newly added files between scan 1 and scan 2
```sql
SELECT n.path
FROM file_snapshots n
LEFT JOIN file_snapshots o
  ON o.path = n.path AND o.scan_run_id = 1
WHERE n.scan_run_id = 2
  AND o.path IS NULL
ORDER BY n.path;
```

### Show deleted files between scan 1 and scan 2
```sql
SELECT o.path
FROM file_snapshots o
LEFT JOIN file_snapshots n
  ON n.path = o.path AND n.scan_run_id = 2
WHERE o.scan_run_id = 1
  AND n.path IS NULL
ORDER BY o.path;
```

## Why This Project Matters
File integrity monitoring is an important cybersecurity tool because it helps identify unauthorized or unexpected changes to files. This project demonstrates the core ideas behind how monitoring tools can establish a baseline and later detect deviations that may indicate normal updates, user mistakes, or malicious tampering.

## Future Improvements
- Add configuration file support
- Add logging to file
- Generate human-readable comparison reports
- Add a simple dashboard
- Package the project more cleanly into modules

## Author
Marco Buritica
