"""Sportradar Tennis API client.

Features
--------
* Throttling (the trial key allows ~1 request/second)
* Retries with exponential back-off for 429 / 5xx and network errors
* Clear errors for authentication problems, with the API key redacted
* Raw JSON caching in ``data/raw`` so the ETL can be re-run offline
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from config import API_BASE_URL, ENDPOINTS, RAW_DIR

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class SportradarError(RuntimeError):
    """Raised for any unrecoverable Sportradar API problem."""


class SportradarClient:
    """Thin, resilient wrapper around the Sportradar Tennis v3 API."""

    def __init__(
        self,
        api_key: Optional[str],
        access_level: str = "trial",
        language: str = "en",
        request_delay: float = 1.2,
        max_retries: int = 5,
        timeout: int = 30,
        raw_dir: Path = RAW_DIR,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not api_key:
            raise SportradarError(
                "SPORTRADAR_API_KEY is not set. Add it to your .env file "
                "(see .env.example) or run the ETL with --demo."
            )
        self.api_key = api_key
        self.access_level = access_level
        self.language = language
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.raw_dir = Path(raw_dir)
        self.session = session or requests.Session()
        self._last_request_at = 0.0

    # ------------------------------------------------------------------ helpers
    def _url(self, dataset: str) -> str:
        endpoint = ENDPOINTS[dataset]
        return f"{API_BASE_URL}/{self.access_level}/v3/{self.language}/{endpoint}"

    def _redact(self, text: str) -> str:
        return text.replace(self.api_key, "***")

    def _throttle(self) -> None:
        wait = self.request_delay - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _backoff_seconds(attempt: int, response: Optional[requests.Response] = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after and str(retry_after).isdigit():
                return float(retry_after)
        return min(2.0 ** attempt, 30.0)

    # -------------------------------------------------------------------- cache
    def _cache_path(self, dataset: str) -> Path:
        return self.raw_dir / f"{dataset}_latest.json"

    def _save_cache(self, dataset: str, payload: Dict[str, Any]) -> None:
        try:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
            text = json.dumps(payload, ensure_ascii=False)
            self._cache_path(dataset).write_text(text, encoding="utf-8")
            dated = self.raw_dir / f"{dataset}_{date.today().isoformat()}.json"
            dated.write_text(text, encoding="utf-8")
        except OSError as exc:  # cache is best-effort
            logger.warning("Could not write raw cache for %s: %s", dataset, exc)

    def _load_cache(self, dataset: str) -> Optional[Dict[str, Any]]:
        path = self._cache_path(dataset)
        if path.exists():
            logger.info("Using cached raw JSON for %s (%s)", dataset, path)
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    # ------------------------------------------------------------------- public
    def fetch(self, dataset: str, use_cache: bool = False) -> Dict[str, Any]:
        """Fetch one dataset (``competitions``, ``complexes`` or ``rankings``)."""
        if dataset not in ENDPOINTS:
            raise SportradarError(f"Unknown dataset '{dataset}'. Choose from {list(ENDPOINTS)}")
        if use_cache:
            cached = self._load_cache(dataset)
            if cached is not None:
                return cached

        url = self._url(dataset)
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            try:
                response = self.session.get(
                    url, params={"api_key": self.api_key}, timeout=self.timeout
                )
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise SportradarError(
                        f"Network error while fetching {dataset}: {self._redact(str(exc))}"
                    ) from None
                delay = self._backoff_seconds(attempt)
                logger.warning("Network error (%s). Retry %d in %.0fs", dataset, attempt, delay)
                time.sleep(delay)
                continue

            status = response.status_code
            if status == 200:
                try:
                    payload = response.json()
                except ValueError:
                    raise SportradarError(f"{dataset}: response was not valid JSON") from None
                logger.info("Fetched %s (attempt %d)", dataset, attempt)
                self._save_cache(dataset, payload)
                return payload
            if status in RETRYABLE_STATUS and attempt < self.max_retries:
                delay = self._backoff_seconds(attempt, response)
                logger.warning("HTTP %s for %s. Retry %d in %.0fs", status, dataset, attempt, delay)
                time.sleep(delay)
                continue
            if status in (401, 403):
                raise SportradarError(
                    f"HTTP {status} for {dataset}: check that the API key is valid, that it is "
                    f"enabled for the Tennis API and that SPORTRADAR_ACCESS_LEVEL "
                    f"('{self.access_level}') matches your plan."
                )
            body = self._redact(response.text[:200])
            raise SportradarError(f"HTTP {status} for {dataset}: {body}")
        raise SportradarError(f"{dataset}: retries exhausted")  # pragma: no cover
