"""Write queue service for serializing database writes with retry logic.

Prevents 'database is locked' errors by queuing write operations and
retrying with exponential backoff when contention occurs.
"""

import queue
import threading
import time
from typing import Any, Callable, Optional
from utils import get_class_logger


class WriteQueue:
    """Serializes write operations with exponential backoff retry."""

    def __init__(
        self,
        max_retries: int = 5,
        base_delay_ms: int = 100,
        max_delay_ms: int = 1600,
    ):
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self.logger = get_class_logger(self)

    def start(self):
        """Start the write queue worker thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._process_queue, daemon=True, name="WriteQueueWorker"
            )
            self._worker_thread.start()
            self.logger.info("Write queue started")

    def stop(self):
        """Stop the write queue and wait for pending operations."""
        with self._lock:
            if not self._running:
                return
            self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._queue.put(None)
            self._worker_thread.join(timeout=10)
            self.logger.info("Write queue stopped")

    def submit(self, operation: Callable, *args, **kwargs) -> Any:
        """Submit a write operation to the queue. Returns result or raises exception."""
        if not self._running:
            self.start()

        result_holder = {"result": None, "exception": None, "done": threading.Event()}

        def wrapped():
            try:
                delay_ms = self.base_delay_ms
                last_exception = None
                for attempt in range(1, self.max_retries + 1):
                    try:
                        result_holder["result"] = operation(*args, **kwargs)
                        return
                    except Exception as e:
                        last_exception = e
                        error_msg = str(e).lower()
                        is_lock_error = any(
                            keyword in error_msg
                            for keyword in ["locked", "busy", "cannot acquire lock"]
                        )
                        if is_lock_error and attempt < self.max_retries:
                            self.logger.warning(
                                f"Write lock contention (attempt {attempt}/{self.max_retries}), "
                                f"retrying in {delay_ms}ms: {e}"
                            )
                            time.sleep(delay_ms / 1000.0)
                            delay_ms = min(delay_ms * 2, self.max_delay_ms)
                        else:
                            break
                result_holder["exception"] = last_exception
            finally:
                result_holder["done"].set()

        self._queue.put(wrapped)
        result_holder["done"].wait()

        if result_holder["exception"]:
            raise result_holder["exception"]
        return result_holder["result"]

    def _process_queue(self):
        """Worker thread that processes queued write operations."""
        while self._running:
            try:
                task = self._queue.get(timeout=1.0)
                if task is None:
                    break
                task()
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Write queue worker error: {e}", exc_info=True)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()
