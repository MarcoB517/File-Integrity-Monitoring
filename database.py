import sqlite3
import time
from typing import Optional, Dict, Any, Sequence


def get_connection(db_path: str = "fim.db") -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables/indexes for Workflow 1 (scan_runs + file_snapshots)."""
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


def create_scan_run(conn: sqlite3.Connection, root_path: str, label: Optional[str] = None) -> int:
    """Insert a scan_runs row and return its id."""
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
    """Bulk insert file metadata dictionaries into file_snapshots."""
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
