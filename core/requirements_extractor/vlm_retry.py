import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_TRANSIENT_CODES = {429, 500, 502, 503, 504}


class VlmRetryWrapper:
    """Wraps a Docling DocumentConverter with retry logic for transient errors."""

    def __init__(self, converter, max_retries: int = 3, base_delay: float = 2.0):
        self._converter = converter
        self._max_retries = max_retries
        self._base_delay = base_delay

    def convert(self, pdf_path: Path):
        last_error = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return self._converter.convert(pdf_path)
            except Exception as error:
                last_error = error
                if not self._is_transient(error):
                    raise
                delay = self._base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "VLM service unavailable (attempt %d/%d). Retrying in %.1fs...",
                    attempt, self._max_retries, delay,
                )
                time.sleep(delay)
        raise last_error

    def _is_transient(self, error: Exception) -> bool:
        msg = str(error).lower()
        if any(f'"code": {code}' in str(error) or f'"code":{code}' in str(error)
               for code in _TRANSIENT_CODES):
            return True
        if any(kw in msg for kw in ("503", "429", "unavailable", "high demand",
                                     "timeout", "timed out", "connection")):
            return True
        return False
