"""
test_fim.py — Unit Tests for the File Integrity Monitoring System

Tests all core modules: hashing, scanner, database, and comparator.
Uses only Python standard library (unittest, tempfile, sqlite3).

Usage:
    python3 test_fim.py
    python3 test_fim.py -v        # verbose output

Author: Marco Buritica
Course: CISC 4900
"""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from hashing import sha256_file
from scanner import collect_file_metadata
from database import get_connection, init_db, create_scan_run, insert_file_snapshots
from comparator import compare_scans, format_comparison_report, get_scan_summary


# ─────────────────────────────────────────────
#  Hashing Tests
# ─────────────────────────────────────────────

class TestHashing(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory with test files before each test."""
        self.tmp_dir = tempfile.mkdtemp()

    def _make_file(self, name, content="hello"):
        """Helper: write a file and return its path."""
        path = Path(self.tmp_dir) / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def test_returns_string(self):
        """sha256_file should return a string."""
        f = self._make_file("test.txt")
        result = sha256_file(f)
        self.assertIsInstance(result, str)

    def test_correct_length(self):
        """SHA-256 hex digest should always be 64 characters."""
        f = self._make_file("test.txt")
        result = sha256_file(f)
        self.assertEqual(len(result), 64)

    def test_known_hash(self):
        """Empty file should always produce the same known SHA-256 hash."""
        f = self._make_file("empty.txt", content="")
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.assertEqual(sha256_file(f), expected)

    def test_same_content_same_hash(self):
        """Two files with identical content should produce the same hash."""
        f1 = self._make_file("a.txt", content="hello world")
        f2 = self._make_file("b.txt", content="hello world")
        self.assertEqual(sha256_file(f1), sha256_file(f2))

    def test_different_content_different_hash(self):
        """Two files with different content should produce different hashes."""
        f1 = self._make_file("a.txt", content="hello")
        f2 = self._make_file("b.txt", content="world")
        self.assertNotEqual(sha256_file(f1), sha256_file(f2))

    def test_file_not_found(self):
        """sha256_file should raise FileNotFoundError for missing files."""
        with self.assertRaises(FileNotFoundError):
            sha256_file("/nonexistent/path/file.txt")


# ─────────────────────────────────────────────
#  Scanner Tests
# ─────────────────────────────────────────────

class TestScanner(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory with test files before each test."""
        self.tmp_dir = tempfile.mkdtemp()

    def _make_file(self, name, content="test content"):
        """Helper: write a file and return its path."""
        path = Path(self.tmp_dir) / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_returns_list(self):
        """collect_file_metadata should return a list."""
        result = collect_file_metadata(self.tmp_dir)
        self.assertIsInstance(result, list)

    def test_finds_files(self):
        """Scanner should find files in the target directory."""
        self._make_file("file1.txt")
        self._make_file("file2.txt")
        result = collect_file_metadata(self.tmp_dir)
        self.assertEqual(len(result), 2)

    def test_metadata_fields(self):
        """Each file entry should contain all required metadata fields."""
        self._make_file("file.txt")
        result = collect_file_metadata(self.tmp_dir)
        expected_fields = {
            "path", "size_bytes", "mtime", "permissions",
            "owner_uid", "owner_gid", "inode", "hard_links", "sha256"
        }
        self.assertEqual(set(result[0].keys()), expected_fields)

    def test_results_sorted(self):
        """Results should be sorted by file path."""
        self._make_file("c.txt")
        self._make_file("a.txt")
        self._make_file("b.txt")
        result = collect_file_metadata(self.tmp_dir)
        paths = [f["path"] for f in result]
        self.assertEqual(paths, sorted(paths))

    def test_empty_directory(self):
        """Scanning an empty directory should return an empty list."""
        result = collect_file_metadata(self.tmp_dir)
        self.assertEqual(result, [])

    def test_skips_symlinks(self):
        """Symlinks should not appear in scan results."""
        real_file = self._make_file("real.txt")
        link_path = Path(self.tmp_dir) / "link.txt"
        link_path.symlink_to(real_file)
        result = collect_file_metadata(self.tmp_dir)
        paths = [f["path"] for f in result]
        self.assertNotIn(str(link_path), paths)

    def test_invalid_directory(self):
        """Scanner should raise an error for a non-existent directory."""
        with self.assertRaises((FileNotFoundError, NotADirectoryError)):
            collect_file_metadata("/nonexistent/directory")

    def test_sha256_in_results(self):
        """Each file entry should have a valid 64-character SHA-256 hash."""
        self._make_file("file.txt", content="some content")
        result = collect_file_metadata(self.tmp_dir)
        self.assertEqual(len(result[0]["sha256"]), 64)


# ─────────────────────────────────────────────
#  Database Tests
# ─────────────────────────────────────────────

class TestDatabase(unittest.TestCase):

    def setUp(self):
        """Create an in-memory SQLite database before each test."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON;")
        init_db(self.conn)

    def tearDown(self):
        """Close the database connection after each test."""
        self.conn.close()

    def test_tables_created(self):
        """init_db should create scan_runs and file_snapshots tables."""
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        self.assertIn("scan_runs", table_names)
        self.assertIn("file_snapshots", table_names)

    def test_create_scan_run_returns_id(self):
        """create_scan_run should return an integer ID."""
        scan_id = create_scan_run(self.conn, "/test/path", label="baseline")
        self.assertIsInstance(scan_id, int)
        self.assertGreater(scan_id, 0)

    def test_create_scan_run_with_label(self):
        """Scan run label should be stored and retrievable."""
        create_scan_run(self.conn, "/test/path", label="baseline")
        row = self.conn.execute(
            "SELECT label FROM scan_runs WHERE label = 'baseline'"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "baseline")

    def test_create_scan_run_without_label(self):
        """Scan run should be created with NULL label if none provided."""
        scan_id = create_scan_run(self.conn, "/test/path")
        row = self.conn.execute(
            "SELECT label FROM scan_runs WHERE id = ?", (scan_id,)
        ).fetchone()
        self.assertIsNone(row[0])

    def test_insert_file_snapshots(self):
        """insert_file_snapshots should store all file records."""
        scan_id = create_scan_run(self.conn, "/test/path")
        files = [
            {"path": "/test/a.txt", "size_bytes": 100, "mtime": 1000.0,
             "permissions": "0o644", "owner_uid": 1000, "owner_gid": 1000,
             "inode": 1, "hard_links": 1, "sha256": "a" * 64},
            {"path": "/test/b.txt", "size_bytes": 200, "mtime": 2000.0,
             "permissions": "0o644", "owner_uid": 1000, "owner_gid": 1000,
             "inode": 2, "hard_links": 1, "sha256": "b" * 64},
        ]
        insert_file_snapshots(self.conn, scan_id, files)
        self.conn.commit()

        count = self.conn.execute(
            "SELECT COUNT(*) FROM file_snapshots WHERE scan_run_id = ?", (scan_id,)
        ).fetchone()[0]
        self.assertEqual(count, 2)

    def test_multiple_scan_runs(self):
        """Each call to create_scan_run should return a unique ID."""
        id1 = create_scan_run(self.conn, "/test/path")
        id2 = create_scan_run(self.conn, "/test/path")
        self.assertNotEqual(id1, id2)


# ─────────────────────────────────────────────
#  Comparator Tests
# ─────────────────────────────────────────────

class TestComparator(unittest.TestCase):

    def setUp(self):
        """Set up an in-memory database with two scans for comparison."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON;")
        init_db(self.conn)

        # Scan 1 (baseline): file_a and file_b
        self.scan1 = create_scan_run(self.conn, "/test", label="baseline")
        insert_file_snapshots(self.conn, self.scan1, [
            {"path": "/test/file_a.txt", "size_bytes": 100, "mtime": 1000.0,
             "permissions": "0o644", "owner_uid": 1000, "owner_gid": 1000,
             "inode": 1, "hard_links": 1, "sha256": "a" * 64},
            {"path": "/test/file_b.txt", "size_bytes": 200, "mtime": 2000.0,
             "permissions": "0o644", "owner_uid": 1000, "owner_gid": 1000,
             "inode": 2, "hard_links": 1, "sha256": "b" * 64},
        ])

        # Scan 2: file_a (modified), file_c (new), file_b (deleted)
        self.scan2 = create_scan_run(self.conn, "/test", label="scan2")
        insert_file_snapshots(self.conn, self.scan2, [
            {"path": "/test/file_a.txt", "size_bytes": 150, "mtime": 3000.0,
             "permissions": "0o644", "owner_uid": 1000, "owner_gid": 1000,
             "inode": 1, "hard_links": 1, "sha256": "x" * 64},  # modified
            {"path": "/test/file_c.txt", "size_bytes": 300, "mtime": 4000.0,
             "permissions": "0o644", "owner_uid": 1000, "owner_gid": 1000,
             "inode": 3, "hard_links": 1, "sha256": "c" * 64},  # added
        ])
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_detects_added_files(self):
        """compare_scans should detect files added in the new scan."""
        diff = compare_scans(self.conn, self.scan1, self.scan2)
        self.assertIn("/test/file_c.txt", diff["added"])

    def test_detects_deleted_files(self):
        """compare_scans should detect files removed since the baseline."""
        diff = compare_scans(self.conn, self.scan1, self.scan2)
        self.assertIn("/test/file_b.txt", diff["deleted"])

    def test_detects_modified_files(self):
        """compare_scans should detect files whose hash changed."""
        diff = compare_scans(self.conn, self.scan1, self.scan2)
        modified_paths = [m[0] for m in diff["modified"]]
        self.assertIn("/test/file_a.txt", modified_paths)

    def test_no_false_positives(self):
        """Unmodified files should not appear in any change category."""
        # Scan 3 is identical to scan 1
        scan3 = create_scan_run(self.conn, "/test", label="scan3")
        insert_file_snapshots(self.conn, scan3, [
            {"path": "/test/file_a.txt", "size_bytes": 100, "mtime": 1000.0,
             "permissions": "0o644", "owner_uid": 1000, "owner_gid": 1000,
             "inode": 1, "hard_links": 1, "sha256": "a" * 64},
        ])
        self.conn.commit()

        diff = compare_scans(self.conn, self.scan1, scan3)
        # file_a unchanged — should not appear in modified
        modified_paths = [m[0] for m in diff["modified"]]
        self.assertNotIn("/test/file_a.txt", modified_paths)

    def test_invalid_scan_id_raises(self):
        """compare_scans should raise ValueError for a nonexistent scan ID."""
        with self.assertRaises(ValueError):
            compare_scans(self.conn, self.scan1, 9999)

    def test_returns_correct_keys(self):
        """compare_scans result should have added, deleted, and modified keys."""
        diff = compare_scans(self.conn, self.scan1, self.scan2)
        self.assertIn("added", diff)
        self.assertIn("deleted", diff)
        self.assertIn("modified", diff)

    def test_get_scan_summary(self):
        """get_scan_summary should return correct file count."""
        summary = get_scan_summary(self.conn, self.scan1)
        self.assertEqual(summary["file_count"], 2)
        self.assertEqual(summary["label"], "baseline")

    def test_get_scan_summary_invalid_id(self):
        """get_scan_summary should raise ValueError for missing scan ID."""
        with self.assertRaises(ValueError):
            get_scan_summary(self.conn, 9999)

    def test_format_report_contains_summary(self):
        """format_comparison_report output should contain SUMMARY line."""
        diff = compare_scans(self.conn, self.scan1, self.scan2)
        report = format_comparison_report(diff)
        self.assertIn("SUMMARY", report)
        self.assertIn("added", report)
        self.assertIn("deleted", report)
        self.assertIn("modified", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
