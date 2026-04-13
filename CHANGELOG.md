# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Export comparison reports to file
- Export to CSV/JSON formats
- Logging and error handling improvements
- Unit test suite

---

## [0.4.0]

### Added
- **Scan comparison feature** (`comparator.py`)
  - `compare_scans()` function to diff two scan snapshots
  - `format_comparison_report()` for human-readable output
  - `get_scan_summary()` for scan metadata and statistics
- **Test comparator script** (`test_comparator.py`)
  - `--list` flag to show all available scans
  - Compare any two scans by ID
- **Database integration in main.py**
  - Scans now automatically save to `fim.db`
  - `--label` flag to tag scans (e.g., `--label baseline`)

### Changed
- `main.py` now saves to database instead of just printing JSON
- Output is now a summary instead of raw JSON dump

---

## [0.3.0]

### Added
- Comprehensive documentation suite
  - Enhanced README with feature table and architecture diagram
  - ARCHITECTURE.md with technical design details
  - USER_GUIDE.md with step-by-step instructions
- Docstrings for all modules and functions
- Comparison SQL queries in documentation

### Changed
- Improved code organization with type hints
- Better inline comments explaining design decisions

---

## [0.2.0]

### Added
- SQLite database integration (`database.py`)
- `scan_runs` table for tracking scan operations
- `file_snapshots` table for storing file metadata per scan
- Foreign key relationship with CASCADE delete
- Indexes on `path` and `sha256` columns for query performance
- `get_connection()` function with foreign key pragma
- `init_db()` function for schema creation
- `create_scan_run()` function to record new scans
- `insert_file_snapshots()` function for bulk data insertion

### Changed
- Database schema designed for efficient scan comparisons

---

## [0.1.0]

### Added
- Initial project setup
- Recursive directory scanning (`scanner.py`)
  - Uses `os.walk()` for traversal
  - Skips symbolic links (deliberate design choice)
  - Graceful handling of permission errors
- SHA-256 file hashing (`hashing.py`)
  - Chunked reading for memory safety
  - 1MB default chunk size
- File metadata collection
  - Path, size, mtime, permissions
  - Owner UID/GID, inode, hard links
- Basic CLI entry point (`main.py`)
  - Accepts directory path as argument
- Project documentation
  - README.md with overview
  - .gitignore for Python projects

---

## Version History Summary

| Version | Focus Area |
|---------|------------|
| 0.1.0 | Core scanning and hashing |
| 0.2.0 | Database persistence layer |
| 0.3.0 | Documentation and code quality |
| 0.4.0 | Comparison feature and CLI improvements |
| 0.5.0 | Report exports (planned) |
| 1.0.0 | Production-ready release (planned) |
