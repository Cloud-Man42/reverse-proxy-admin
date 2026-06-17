import os
import tempfile
from pathlib import Path

# Use temp sqlite for tests
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'nginx-admin-test.db'}")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")
