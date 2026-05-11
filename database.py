"""
database.py — SQLite Persistence Layer

Manages all database operations for the FIM system including connection
management, schema initialization, and data insertion.

Author: Marco Buritica
Course: CISC 4900
"""

import sqlite3
import time
from typing import Optional, Dict, Any, Sequence

from logger import get_logger

logger = get_logger(__name__)


def get_connection(db_path: str = "fim.db") -> sqlite3.Connection:
    """
    Open a SQLite database connection with foreign key enforcement enabled.

    Args:
        db_path: Path to the SQLite database file. Default is "fim.db".

    Returns:
        A sqlite3.Connection object.

    Raises:
        sqlite3.OperationalError: If the database file cannot be opened.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        logger.debug(f"Database connection opened: {db_path}")
        return conn
    except sqlite3.OperationalError as e:
        logger.error(f"Failed to open database at {db_path}: {e}")
        raise


def init_db(conn: sqlite3.Connection) -> None:
    """
    Create the database schema if it doesn't already exist.

    Creates scan_runs and file_snapshots tables along with indexes.
    Safe to call multiple times.

    Args:
        conn: An open SQLite connection.

    Raises:
        sqlite3.Error: If table creation fails.
    """
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_runs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_time REAL    NOT NULL,
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
        logger.debug("Database schema initialized")
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise


def create_scan_run(
    conn: sqlite3.Connection,
    root_path: str,
    label: Optional[str] = None
) -> int:
    """
    Create a new scan run record and return its ID.

    Args:
        conn: An open SQLite connection.
        root_path: The directory path that was scanned.
        label: Optional descriptive label (e.g., "baseline").

    Returns:
        The integer ID of the newly created scan_runs row.

    Raises:
        sqlite3.Error: If the insert fails.
    """
    try:
        scan_time = time.time()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO scan_runs (scan_time, root_path, label) VALUES (?, ?, ?)",
            (scan_time, root_path, label),
        )
        scan_id = int(cur.lastrowid)
        logger.info(f"Scan run created: id={scan_id}, path={root_path}, label={label}")
        return scan_id
    except sqlite3.Error as e:
        logger.error(f"Failed to create scan run: {e}")
        raise


def insert_file_snapshots(
    conn: sqlite3.Connection,
    scan_run_id: int,
    files: Sequence[Dict[str, Any]],
) -> None:
    """
    Bulk insert file metadata into the file_snapshots table.

    Args:
        conn: An open SQLite connection.
        scan_run_id: The ID of the scan run to associate files with.
        files: A sequence of file metadata dictionaries.

    Raises:
        sqlite3.Error: If the insert fails.
    """
    try:
        rows = [
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
            for f in files
        ]

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
        logger.info(f"Inserted {len(rows)} file snapshots for scan_id={scan_run_id}")
    except sqlite3.Error as e:
        logger.error(f"Failed to insert file snapshots for scan_id={scan_run_id}: {e}")
        raise
