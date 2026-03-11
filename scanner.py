import os
import stat
from pathlib import Path
from hashing import sha256_file

def collect_file_metadata(root_dir):
    results = []
    root_dir = Path(root_dir).expanduser().resolve()

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            filepath = Path(dirpath) / filename
            try:
                # Skip if not a regular file
                if not filepath.is_file():
                    continue

                # Skip symlinks. Remove this if you want them.
                if filepath.is_symlink():
                    continue

                s = filepath.stat()
                metadata = {
                    "path":        str(filepath.resolve()),
                    "size_bytes":  int(s.st_size),
                    "mtime":       float(s.st_mtime),
                    "permissions": oct(stat.S_IMODE(s.st_mode)),
                    "owner_uid":   int(s.st_uid),
                    "owner_gid":   int(s.st_gid),
                    "inode":       int(s.st_ino),
                    "hard_links":  int(s.st_nlink),
                    "sha256": sha256_file(filepath),
                }
                results.append(metadata)

            except (PermissionError, FileNotFoundError, OSError):
                # file may disappear during scan or be inaccessible
                continue

    results.sort(key=lambda x: x["path"])
    return results