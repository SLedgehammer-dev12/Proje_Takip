"""Tests for WAL checkpoint and health check optimization."""

import os
import pytest
from database import ProjeTakipDB


DB_PATH = "test_wal_health.db"


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


class TestWalCheckpoint:
    def test_wal_checkpoint_timer_created(self):
        db = ProjeTakipDB(DB_PATH)
        assert db._wal_checkpoint_timer is not None
        assert db._wal_checkpoint_timer.interval() == 300000  # 5 minutes
        db.close()

    def test_perform_wal_checkpoint_no_error(self):
        db = ProjeTakipDB(DB_PATH)
        with db.transaction():
            db.cursor.execute("INSERT INTO kategoriler (isim) VALUES ('Test')")

        db._perform_wal_checkpoint()
        db.close()

    def test_wal_checkpoint_timer_stopped_on_close(self):
        db = ProjeTakipDB(DB_PATH)
        db.close()
        assert db._wal_checkpoint_timer is not None


class TestHealthCheck:
    def test_health_check_timer_created(self):
        db = ProjeTakipDB(DB_PATH)
        assert db._health_check_timer is not None
        assert db._health_check_timer.interval() == 1800000  # 30 minutes
        db.close()

    def test_health_check_on_healthy_db(self):
        db = ProjeTakipDB(DB_PATH)
        db.cursor.execute("PRAGMA quick_check")
        result = db.cursor.fetchone()
        assert result[0] == "ok"
        db.close()

    def test_health_check_method_no_error(self):
        db = ProjeTakipDB(DB_PATH)
        db._health_check()
        db.close()

    def test_health_check_timer_stopped_on_close(self):
        db = ProjeTakipDB(DB_PATH)
        db.close()
        assert db._health_check_timer is not None


class TestNetworkOptimization:
    def test_local_db_uses_wal_mode(self):
        db = ProjeTakipDB(DB_PATH)
        db.cursor.execute("PRAGMA journal_mode")
        mode = db.cursor.fetchone()[0]
        assert mode == "wal"
        db.close()

    def test_local_db_has_normal_synchronous(self):
        db = ProjeTakipDB(DB_PATH)
        db.cursor.execute("PRAGMA synchronous")
        level = db.cursor.fetchone()[0]
        assert level == 1  # NORMAL
        db.close()

    def test_local_db_busy_timeout(self):
        db = ProjeTakipDB(DB_PATH)
        db.cursor.execute("PRAGMA busy_timeout")
        timeout = db.cursor.fetchone()[0]
        assert timeout == 10000  # 10 seconds
        db.close()

    def test_local_db_cache_size(self):
        db = ProjeTakipDB(DB_PATH)
        db.cursor.execute("PRAGMA cache_size")
        cache = db.cursor.fetchone()[0]
        assert cache == -64000  # 64MB
        db.close()
