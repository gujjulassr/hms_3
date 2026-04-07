"""
Advanced Python — Threading for concurrent booking validation.
Section 2 requirement: threading for concurrent bookings.
"""
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from utils.decorators import logger


# Thread-safe booking lock
_booking_lock = threading.Lock()
_slot_locks: dict[str, threading.Lock] = {}  # Per-slot locks


def get_slot_lock(session_id: str, slot_number: int) -> threading.Lock:
    """Get or create a thread-safe lock for a specific slot."""
    key = f"{session_id}:{slot_number}"
    if key not in _slot_locks:
        with _booking_lock:
            if key not in _slot_locks:
                _slot_locks[key] = threading.Lock()
    return _slot_locks[key]


def thread_safe_book(session_id: str, slot_number: int, book_func: Callable, *args) -> bool:
    """
    Thread-safe wrapper for booking operations.
    Uses per-slot locking to prevent double-booking race conditions.
    """
    lock = get_slot_lock(session_id, slot_number)
    acquired = lock.acquire(timeout=5)  # 5 second timeout
    if not acquired:
        logger.warning(f"[THREAD] Could not acquire lock for slot {session_id}:{slot_number}")
        return False
    try:
        result = book_func(*args)
        return result
    except Exception as e:
        logger.error(f"[THREAD] Booking failed: {e}")
        return False
    finally:
        lock.release()


class ConcurrentBookingProcessor:
    """
    Process multiple booking requests concurrently using threads.
    Demonstrates: ThreadPoolExecutor, threading.Lock, concurrent processing.
    """

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._results: list[dict] = []
        self._lock = threading.Lock()

    def submit_booking(self, booking_id: str, process_func: Callable, *args):
        """Submit a booking job to the thread pool."""
        future = self._executor.submit(self._process_with_lock, booking_id, process_func, *args)
        return future

    def _process_with_lock(self, booking_id: str, process_func: Callable, *args):
        """Execute a booking function with thread-safe result collection."""
        try:
            result = process_func(*args)
            with self._lock:
                self._results.append({"id": booking_id, "status": "success", "result": result})
            return result
        except Exception as e:
            with self._lock:
                self._results.append({"id": booking_id, "status": "error", "error": str(e)})
            return None

    def get_results(self) -> list[dict]:
        """Get all processed results."""
        with self._lock:
            return list(self._results)

    def clear_results(self):
        """Clear results."""
        with self._lock:
            self._results.clear()

    def shutdown(self):
        self._executor.shutdown(wait=True)


def run_async_in_thread(coro):
    """Run an async coroutine in a new thread with its own event loop."""
    result = [None]
    error = [None]

    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result[0] = loop.run_until_complete(coro)
        except Exception as e:
            error[0] = e
        finally:
            loop.close()

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join(timeout=30)

    if error[0]:
        raise error[0]
    return result[0]
