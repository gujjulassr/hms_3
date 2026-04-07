"""
Advanced Python — Decorators for logging, timing, and access control.
Section 2 requirement: decorators for logging.
"""
import functools
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("hms")


def log_action(func):
    """
    Decorator — logs function entry, arguments, exit, and return value.
    Works with both sync and async functions.
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.info(f"[CALL] {func_name} | args={args[:3]}... kwargs={list(kwargs.keys())}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"[OK] {func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"[ERROR] {func_name} failed: {e}")
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.info(f"[CALL] {func_name} | args={args[:3]}... kwargs={list(kwargs.keys())}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"[OK] {func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"[ERROR] {func_name} failed: {e}")
            raise

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def timer(func):
    """
    Decorator — measures execution time of a function.
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"[TIMER] {func.__name__} took {elapsed:.4f}s")
        return result

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"[TIMER] {func.__name__} took {elapsed:.4f}s")
        return result

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def require_role(*allowed_roles):
    """
    Decorator factory — restricts function access to specific roles.
    Usage: @require_role("doctor", "admin")
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Look for 'user' in kwargs
            user = kwargs.get("user", {})
            role = user.get("role", "")
            if role not in allowed_roles:
                raise PermissionError(f"Role '{role}' not allowed. Required: {allowed_roles}")
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            user = kwargs.get("user", {})
            role = user.get("role", "")
            if role not in allowed_roles:
                raise PermissionError(f"Role '{role}' not allowed. Required: {allowed_roles}")
            return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator factory — retries a function on failure.
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(f"[RETRY] {func.__name__} attempt {attempt}/{max_attempts} failed: {e}")
                    if attempt < max_attempts:
                        import asyncio
                        await asyncio.sleep(delay)
            raise last_error

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(f"[RETRY] {func.__name__} attempt {attempt}/{max_attempts} failed: {e}")
                    if attempt < max_attempts:
                        time.sleep(delay)
            raise last_error

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
