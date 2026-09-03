import sqlite3

from app.db import apply_sqlite_pragmas


def test_apply_sqlite_pragmas_sets_expected_values():
    conn = sqlite3.connect(":memory:")
    try:
        apply_sqlite_pragmas(conn)
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA temp_store").fetchone()[0] == 2  # 2 == MEMORY
        # WAL isn't available for a pure in-memory database; it stays "memory".
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] in {"wal", "memory"}
    finally:
        conn.close()