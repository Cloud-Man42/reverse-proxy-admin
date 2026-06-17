import sys
from contextlib import contextmanager

if sys.platform == "win32":
    @contextmanager
    def file_lock(_path):
        yield
else:
    import fcntl

    @contextmanager
    def file_lock(path):
        lock_path = path.with_suffix(path.suffix + ".lock")
        with open(lock_path, "w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_path.unlink(missing_ok=True)
