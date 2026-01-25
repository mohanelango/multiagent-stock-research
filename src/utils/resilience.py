from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Sequence, Type, TypeVar

import concurrent.futures as cf

T = TypeVar("T")


class RetryableError(RuntimeError):
    """Raise this to trigger a retry with backoff."""
    pass


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int = 3
    base_delay_sec: float = 0.5
    backoff_factor: float = 2.0
    max_delay_sec: float = 8.0
    jitter_ratio: float = 0.15  # 15% jitter
    retry_statuses: Sequence[int] = (408, 429, 500, 502, 503, 504)
    timeout_sec: Optional[float] = None  # per-attempt timeout


def _sleep_with_jitter(seconds: float, jitter_ratio: float) -> None:
    jitter = seconds * jitter_ratio * random.random()
    time.sleep(seconds + jitter)


def _call_with_timeout(fn: Callable[[], T], timeout_sec: float) -> T:
    # Thread-based timeout is sufficient for preventing stalls in production runs.
    with cf.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn)
        try:
            return fut.result(timeout=timeout_sec)
        except cf.TimeoutError as e:
            # Convert to RetryableError so retry_call always retries timeouts reliably,
            # regardless of what retry_exceptions the caller passes.
            raise RetryableError(f"Operation timed out after {timeout_sec}s") from e


def retry_call(
        fn: Callable[[], T],
        *,
        cfg: RetryConfig,
        op_name: str,
        logger,
        retry_exceptions: Iterable[Type[BaseException]] = (),
) -> T:
    """
    Retry wrapper with exponential backoff + jitter + optional per-attempt timeout.
    Retries when:
      - fn raises RetryableError
      - fn raises any exception in retry_exceptions
    """
    retry_exceptions = tuple(retry_exceptions)

    last_exc: Optional[BaseException] = None

    for attempt in range(cfg.max_retries + 1):
        try:
            if cfg.timeout_sec:
                return _call_with_timeout(fn, cfg.timeout_sec)
            return fn()

        except RetryableError as e:
            last_exc = e

        except retry_exceptions as e:
            last_exc = e

        # no more retries
        if attempt >= cfg.max_retries:
            break

        delay = min(cfg.max_delay_sec, cfg.base_delay_sec * (cfg.backoff_factor ** attempt))
        logger.warning(
            "Retrying op=%s attempt=%d/%d in %.2fs due to: %s",
            op_name,
            attempt + 1,
            cfg.max_retries + 1,
            delay,
            str(last_exc),
        )
        _sleep_with_jitter(delay, cfg.jitter_ratio)

    # exhausted
    logger.error("Retries exhausted op=%s after %d attempts. Last error: %s", op_name, cfg.max_retries + 1,
                 str(last_exc))

    raise last_exc if last_exc else RuntimeError(f"retry_call failed for op={op_name}")
