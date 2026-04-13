"""
database.py — SQLite Persistence Layer

This module manages all database operations for the File Integrity Monitoring
system, including connection management, schema initialization, and data
insertion.

Schema Design:
    The database uses two tables to separate scan metadata from file snapshots:
    
    - scan_runs: Records each scan operation with timestamp, path, and label
    - file_snapshots: Stores file metadata for each scan (linked via foreign key)
    
    This design allows efficient comparison between any two scans and maintains
    a complete audit history of all monitoring activity.

Example:
    >>> from database import get_connection, init_db, create_scan_run
    >>> conn = get_connection("fim.db")
    >>> init_db(conn)
    >>> scan_id = create_scan_run(conn, "/home/user", label="baseline")
    >>> print(f"Created scan with ID: {scan_id}")
    Created scan with ID: 1

Author: Marco Buritica
Course: CISC 4900
"""

import sqlite3
import time
from typing import Optional, Dict, Any, Sequence


def get_connection(db_path: str = "fim.db") -> sqlite3.Connection:
    """
    Open a SQLite database connection with foreign key enforcement enabled.

    This function creates a connection to the specified SQLite database file.
    If the file doesn't exist, SQLite will create it automatically. Foreign
    key constraints are enabled to maintain referential integrity between
    scan_runs and file_snapshots tables.

    Args:
        db_path: Path to the SQLite database file. Default is "fim.db" in
                 the current working directory.

    Returns:
        A sqlite3.Connection object ready for use.

    Example:
        >>> conn = get_connection("fim.db")
        >>> conn.execute("SELECT 1").fetchone()
        (1,)
        >>> conn.close()

        >>> # Using a custom path
        >>> conn = get_connection("/var/lib/fim/integrity.db")

    Note:
        Always close the connection when done, or use a context manager.
        Foreign keys are enabled via PRAGMA to ensure CASCADE deletes work.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """
    Create the database schema if it doesn't already exist.

    This function creates the scan_runs and file_snapshots tables along with
    indexes for efficient querying. It is safe to call multiple times — tables
    are only created if they don't exist (CREATE TABLE IF NOT EXISTS).

    Tables created:
        scan_runs:
            - id: Auto-incrementing primary key
            - scan_time: Unix timestamp of when the scan was performed
            - root_path: The directory that was scanned
            - label: Optional human-readable label (e.g., "baseline", "weekly")

        file_snapshots:
            - scan_run_id: Foreign key to scan_runs.id
            - path: Absolute file path (part of composite primary key)
            - size_bytes: File size
            - mtime: Last modification timestamp
            - permissions: Octal permission string
            - owner_uid/owner_gid: Owner user and group IDs
            - inode: Filesystem inode number
            - hard_links: Number of hard links
            - sha256: SHA-256 hash of file contents

    Indexes created:
        - idx_snapshots_path: For fast lookups by file path
        - idx_snapshots_sha: For finding files with matching hashes

    Args:
        conn: An open SQLite connection (from get_connection).

    Returns:
        None. The function commits the transaction.

    Example:
        >>> conn = get_connection("fim.db")
        >>> init_db(conn)  # Creates tables if needed
        >>> init_db(conn)  # Safe to call again — no-op if tables exist
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_runs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time REAL    NOT NULL,   -- Unix timestamp (time.time())
            root_path TEXT    NOT NULL,
            label     TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS file_snapshots (
            scan_run_id INTEGER NOT NULL,
            path        TEXT    NOT NULL,
            size_bytes  INTEGER,
            mtime       REAL,
            permissions TEXT,
            owner_uid   INTEGER,
            owner_gid   INTEGER,
            inode       INTEGER,
            hard_links  INTEGER,
            sha256      TEXT,

            PRIMARY KEY (scan_run_id, path),
            FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id) ON DELETE CASCADE
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_path ON file_snapshots(path);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_sha  ON file_snapshots(sha256);")
    conn.commit()


def create_scan_run(
    conn: sqlite3.Connection, 
    root_path: str, 
    label: Optional[str] = None
) -> int:
    """
    Create a new scan run record and return its ID.

    This function inserts a new row into the scan_runs table with the current
    timestamp and the specified root path. The returned ID is used to associate
    file snapshots with this scan via insert_file_snapshots().

    Args:
        conn: An open SQLite connection.
        root_path: The directory path that will be scanned.
        label: Optional descriptive label for this scan (e.g., "baseline",
               "daily-2024-04-08", "pre-update"). Useful for identifying
               scans later.

    Returns:
        The integer ID of the newly created scan_runs row.

    Example:
        >>> conn = get_connection("fim.db")
        >>> init_db(conn)
        >>> scan_id = create_scan_run(conn, "/etc", label="baseline")
        >>> print(f"Scan ID: {scan_id}")
        Scan ID: 1

        >>> # Without a label
        >>> scan_id = create_scan_run(conn, "/home/user/documents")
        >>> print(f"Scan ID: {scan_id}")
        Scan ID: 2

    Note:
        This function does NOT commit the transaction. Call conn.commit()
        after inserting file snapshots to ensure atomicity.
    """
    scan_time = time.time()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO scan_runs (scan_time, root_path, label) VALUES (?, ?, ?)",
        (scan_time, root_path, label),
    )
    return int(cur.lastrowid)


def insert_file_snapshots(
    conn: sqlite3.Connection,
    scan_run_id: int,
    files: Sequence[Dict[str, Any]],
) -> None:
    """
    Bulk insert file metadata into the file_snapshots table.

    This function efficiently inserts multiple file records in a single
    database operation using executemany(). Each file dictionary should
    contain the metadata fields collected by scanner.collect_file_metadata().

    Args:
        conn: An open SQLite connection.
        scan_run_id: The ID of the scan run (from create_scan_run) to
                     associate these files with.
        files: A sequence of dictionaries containing file metadata. Each
               dictionary should have these keys:
               - path (str): Absolute file path
               - size_bytes (int): File size
               - mtime (float): Last modification timestamp
               - permissions (str): Octal permission string
               - owner_uid (int): Owner user ID
               - owner_gid (int): Owner group ID
               - inode (int): Filesystem inode
               - hard_links (int): Hard link count
               - sha256 (str): SHA-256 hash digest

    Returns:
        None. Records are inserted but transaction is NOT committed.

    Example:
        >>> from scanner import collect_file_metadata
        >>> conn = get_connection("fim.db")
        >>> init_db(conn)
        >>> 
        >>> files = collect_file_metadata("/etc")
        >>> scan_id = create_scan_run(conn, "/etc", label="baseline")
        >>> insert_file_snapshots(conn, scan_id, files)
        >>> conn.commit()  # Don't forget to commit!
        >>> 
        >>> print(f"Inserted {len(files)} file records")

    Note:
        Call conn.commit() after this function to persist the data.
        Missing keys in file dictionaries will be inserted as NULL.
    """
    rows = []
    for f in files:
        rows.append(
            (
                scan_run_id,
                f.get("path"),
                f.get("size_bytes"),
                f.get("mtime"),
                f.get("permissions"),
                f.get("owner_uid"),
                f.get("owner_gid"),
                f.get("inode"),
                f.get("hard_links"),
                f.get("sha256"),
            )
        )

    conn.executemany(
        """
        INSERT INTO file_snapshots (
            scan_run_id, path, size_bytes, mtime, permissions,
            owner_uid, owner_gid, inode, hard_links, sha256
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
