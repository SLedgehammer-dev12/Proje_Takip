"""Tests for SQLite connection pool optimization."""

import os
import sqlite3
import time
import threading
import pytest
from database import ProjeTakipDB


DB_PATH = "test_conn_pool.db"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for ext in ["", "-wal", "-shm"]:
        path = DB_PATH + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


class TestConnectionPool:
    def test_pool_initialized_with_connections(self):
        db = ProjeTakipDB(DB_PATH)
        assert len(db._read_pool) == 3
        for conn in db._read_pool:
            assert isinstance(conn, sqlite3.Connection)
        db.close()

    def test_acquire_returns_connection(self):
        db = ProjeTakipDB(DB_PATH)
        conn = db.acquire_read_connection()
        assert isinstance(conn, sqlite3.Connection)
        assert len(db._read_pool) == 2
        db.release_read_connection(conn)
        assert len(db._read_pool) == 3
        db.close()

    def test_release_back_to_pool(self):
        db = ProjeTakipDB(DB_PATH)
        conn1 = db.acquire_read_connection()
        conn2 = db.acquire_read_connection()
        assert len(db._read_pool) == 1

        db.release_read_connection(conn1)
        assert len(db._read_pool) == 2

        db.release_read_connection(conn2)
        assert len(db._read_pool) == 3
        db.close()

    def test_pool_max_size_respected(self):
        db = ProjeTakipDB(DB_PATH)
        conn1 = db.acquire_read_connection()
        conn2 = db.acquire_read_connection()
        conn3 = db.acquire_read_connection()
        conn4 = db.acquire_read_connection()

        assert len(db._read_pool) == 0

        db.release_read_connection(conn1)
        db.release_read_connection(conn2)
        db.release_read_connection(conn3)
        db.release_read_connection(conn4)

        assert len(db._read_pool) == 4  # 3 initial + 1 new, all returned
        db.close()

    def test_acquire_when_empty_creates_new(self):
        db = ProjeTakipDB(DB_PATH)
        connections = []
        for _ in range(5):
            connections.append(db.acquire_read_connection())

        assert len(db._read_pool) == 0
        for conn in connections:
            assert isinstance(conn, sqlite3.Connection)

        for conn in connections:
            db.release_read_connection(conn)

        assert len(db._read_pool) == 5  # All returned, capped at max 5
        db.close()

    def test_read_connection_can_query(self):
        db = ProjeTakipDB(DB_PATH)
        with db.transaction():
            db.cursor.execute("INSERT INTO kategoriler (isim) VALUES ('Test')")

        conn = db.acquire_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM kategoriler")
        count = cursor.fetchone()[0]
        assert count >= 1

        db.release_read_connection(conn)
        db.close()

    def test_close_cleans_pool(self):
        db = ProjeTakipDB(DB_PATH)
        conn = db.acquire_read_connection()
        db.release_read_connection(conn)
        assert len(db._read_pool) == 3

        db.close()
        assert len(db._read_pool) == 0

    def test_pool_thread_safe(self):
        db = ProjeTakipDB(DB_PATH)
        acquired = []
        lock = threading.Lock()

        def worker():
            conn = db.acquire_read_connection()
            with lock:
                acquired.append(conn)
            time.sleep(0.01)
            db.release_read_connection(conn)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(acquired) == 5
        assert len(db._read_pool) == 5
        db.close()
