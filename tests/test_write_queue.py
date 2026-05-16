"""Tests for WriteQueue service."""

import time
import threading
import pytest
from services.write_queue import WriteQueue


class TestWriteQueue:
    def test_submit_executes_operation(self):
        queue = WriteQueue()
        result_holder = {"value": None}

        def op():
            result_holder["value"] = 42

        queue.submit(op)
        assert result_holder["value"] == 42
        queue.stop()

    def test_submit_returns_value(self):
        queue = WriteQueue()

        def op():
            return "success"

        result = queue.submit(op)
        assert result == "success"
        queue.stop()

    def test_submit_raises_exception(self):
        queue = WriteQueue()

        def op():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            queue.submit(op)
        queue.stop()

    def test_retries_on_lock_error(self):
        queue = WriteQueue(max_retries=3, base_delay_ms=10, max_delay_ms=50)
        call_count = {"count": 0}

        def flaky_op():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise Exception("database is locked")
            return "ok"

        result = queue.submit(flaky_op)
        assert result == "ok"
        assert call_count["count"] == 3
        queue.stop()

    def test_fails_after_max_retries(self):
        queue = WriteQueue(max_retries=2, base_delay_ms=10, max_delay_ms=50)
        call_count = {"count": 0}

        def always_fail():
            call_count["count"] += 1
            raise Exception("database is locked")

        with pytest.raises(Exception, match="database is locked"):
            queue.submit(always_fail)
        assert call_count["count"] == 2
        queue.stop()

    def test_non_lock_error_not_retried(self):
        queue = WriteQueue(max_retries=5, base_delay_ms=10, max_delay_ms=50)
        call_count = {"count": 0}

        def syntax_error_op():
            call_count["count"] += 1
            raise SyntaxError("invalid syntax")

        with pytest.raises(SyntaxError):
            queue.submit(syntax_error_op)
        assert call_count["count"] == 1
        queue.stop()

    def test_serializes_concurrent_submissions(self):
        queue = WriteQueue()
        execution_log = []
        lock = threading.Lock()
        concurrent_count = {"current": 0, "max": 0}

        def slow_op(n):
            with lock:
                concurrent_count["current"] += 1
                concurrent_count["max"] = max(concurrent_count["max"], concurrent_count["current"])
                execution_log.append(n)
            time.sleep(0.02)
            with lock:
                concurrent_count["current"] -= 1

        threads = []
        for i in range(5):
            t = threading.Thread(target=queue.submit, args=(slow_op, i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(execution_log) == 5
        assert concurrent_count["max"] == 1  # Never more than 1 concurrent
        queue.stop()

    def test_start_stop_lifecycle(self):
        queue = WriteQueue()
        assert not queue.is_running
        queue.start()
        assert queue.is_running
        queue.stop()
        assert not queue.is_running

    def test_double_start_is_safe(self):
        queue = WriteQueue()
        queue.start()
        queue.start()
        queue.start()
        assert queue.is_running
        queue.stop()

    def test_pending_count(self):
        queue = WriteQueue()
        assert queue.pending_count == 0

        queue._queue.put(lambda: None)
        assert queue.pending_count == 1
        queue._queue.get()
        queue.stop()

    def test_exponential_backoff_timing(self):
        queue = WriteQueue(max_retries=3, base_delay_ms=20, max_delay_ms=100)
        timestamps = []

        def track_and_fail():
            timestamps.append(time.time())
            raise Exception("database is locked")

        with pytest.raises(Exception):
            queue.submit(track_and_fail)

        assert len(timestamps) == 3
        if len(timestamps) >= 2:
            first_gap = timestamps[1] - timestamps[0]
            assert first_gap >= 0.015
        queue.stop()
