"""Extract -> Transform -> Load pipeline.

* **Extract**: :class:`src.api_client.SportradarClient` (or demo payloads)
* **Transform**: pure functions that flatten nested JSON into relational rows
  (unit-tested, no I/O)
* **Load**: idempotent upserts, one transaction per dataset, audit log in ``etl_runs``
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import and_, delete
from sqlalchemy.engine import Engine

from config import get_api_settings
from src import database as db
from src.api_client import SportradarClient, SportradarError
from src.demo_data import build_demo_payloads

logger = logging.getLogger(__name__)

DATASETS = ("competitions", "complexes", "rankings")
ProgressFn = Callable[[str], None]


# ------------------------------------------------------------------ utilities
def _text(value: Any, max_len: int, default: Optional[str]) -> Optional[str]:
    """Trim/clip a value to fit its column, falling back to ``default``."""
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip()[:max_len]


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _abbreviation(name: str) -> str:
    letters = "".join(ch for ch in name if ch.isalpha())
    return (letters[:3] or "UNK").upper()


# ------------------------------------------------------------------ transform
def transform_competitions(payload: Dict[str, Any]) -> Tuple[List[dict], List[dict], int]:
    """Flatten the competitions payload into (categories, competitions, skipped)."""
    category_rows: Dict[str, dict] = {}
    competition_rows: Dict[str, dict] = {}
    skipped = 0

    for item in payload.get("competitions") or []:
        comp_id = _text(item.get("id"), 50, None)
        name = _text(item.get("name"), 100, None)
        if not comp_id or not name:
            skipped += 1
            continue

        category = item.get("category") or {}
        category_id = _text(category.get("id"), 50, None)
        if category_id:
            category_rows[category_id] = {
                "category_id": category_id,
                "category_name": _text(category.get("name"), 100, "Unknown"),
            }

        competition_rows[comp_id] = {
            "competition_id": comp_id,
            "competition_name": name,
            "parent_id": _text(item.get("parent_id"), 50, None),
            "type": (_text(item.get("type"), 20, "unknown") or "unknown").lower(),
            "gender": (_text(item.get("gender"), 10, "unknown") or "unknown").lower(),
            "category_id": category_id,
        }
    return list(category_rows.values()), list(competition_rows.values()), skipped


def transform_complexes(payload: Dict[str, Any]) -> Tuple[List[dict], List[dict], int]:
    """Flatten the complexes payload into (complexes, venues, skipped)."""
    complex_rows: Dict[str, dict] = {}
    venue_rows: Dict[str, dict] = {}
    skipped = 0

    for item in payload.get("complexes") or []:
        complex_id = _text(item.get("id"), 50, None)
        complex_name = _text(item.get("name"), 100, None)
        if not complex_id or not complex_name:
            skipped += 1
            continue
        complex_rows[complex_id] = {"complex_id": complex_id, "complex_name": complex_name}

        for venue in item.get("venues") or []:
            venue_id = _text(venue.get("id"), 50, None)
            venue_name = _text(venue.get("name"), 100, None)
            if not venue_id or not venue_name:
                skipped += 1
                continue
            venue_rows[venue_id] = {
                "venue_id": venue_id,
                "venue_name": venue_name,
                "city_name": _text(venue.get("city_name"), 100, "Unknown"),
                "country_name": _text(venue.get("country_name"), 100, "Unknown"),
                "country_code": _text(venue.get("country_code"), 3, "UNK"),
                "timezone": _text(venue.get("timezone"), 100, "Unknown"),
                "complex_id": complex_id,
            }
    return list(complex_rows.values()), list(venue_rows.values()), skipped


def transform_rankings(
    payload: Dict[str, Any],
) -> Tuple[List[dict], List[dict], List[Tuple[str, int, int, str]], int]:
    """Flatten doubles rankings into (competitors, rankings, snapshots, skipped)."""
    competitor_rows: Dict[str, dict] = {}
    ranking_rows: List[dict] = []
    snapshots: List[Tuple[str, int, int, str]] = []
    skipped = 0
    today = date.today().isocalendar()

    for ranking in payload.get("rankings") or []:
        name = _text(ranking.get("name"), 50, "doubles")
        year = _int(ranking.get("year"), today[0])
        week = _int(ranking.get("week"), today[1])
        gender = (_text(ranking.get("gender"), 10, "unknown") or "unknown").lower()
        snapshots.append((name, year, week, gender))

        for entry in ranking.get("competitor_rankings") or []:
            competitor = entry.get("competitor") or {}
            competitor_id = _text(competitor.get("id"), 50, None)
            if not competitor_id or entry.get("rank") is None:
                skipped += 1
                continue
            competitor_name = _text(competitor.get("name"), 100, "Unknown")
            competitor_rows[competitor_id] = {
                "competitor_id": competitor_id,
                "name": competitor_name,
                "country": _text(competitor.get("country"), 100, "Unknown"),
                "country_code": _text(competitor.get("country_code"), 3, "UNK"),
                "abbreviation": _text(competitor.get("abbreviation"), 10, None)
                or _abbreviation(competitor_name or ""),
            }
            ranking_rows.append(
                {
                    "rank": _int(entry.get("rank")),
                    "movement": _int(entry.get("movement")),
                    "points": _int(entry.get("points")),
                    "competitions_played": _int(entry.get("competitions_played")),
                    "competitor_id": competitor_id,
                    "ranking_name": name,
                    "ranking_year": year,
                    "ranking_week": week,
                    "gender": gender,
                }
            )
    return list(competitor_rows.values()), ranking_rows, snapshots, skipped


# ----------------------------------------------------------------------- load
def load_competitions(engine: Engine, payload: Dict[str, Any]) -> Tuple[int, str]:
    cats, comps, skipped = transform_competitions(payload)
    if not comps:
        raise ValueError("No competitions found in the API response.")
    with engine.begin() as conn:
        db.upsert_rows(conn, db.categories, cats)
        db.upsert_rows(conn, db.competitions, comps)
    return len(comps), f"{len(cats)} categories, {len(comps)} competitions, {skipped} skipped"


def load_complexes(engine: Engine, payload: Dict[str, Any]) -> Tuple[int, str]:
    cxs, vens, skipped = transform_complexes(payload)
    if not cxs:
        raise ValueError("No complexes found in the API response.")
    with engine.begin() as conn:
        db.upsert_rows(conn, db.complexes, cxs)
        db.upsert_rows(conn, db.venues, vens)
    return len(vens), f"{len(cxs)} complexes, {len(vens)} venues, {skipped} skipped"


def load_rankings(engine: Engine, payload: Dict[str, Any]) -> Tuple[int, str]:
    comps, rows, snapshots, skipped = transform_rankings(payload)
    if not rows:
        raise ValueError("No doubles rankings found in the API response.")
    table = db.competitor_rankings
    with engine.begin() as conn:
        db.upsert_rows(conn, db.competitors, comps)
        # Replace only the snapshots present in this payload -> history is preserved
        for name, year, week, gender in set(snapshots):
            conn.execute(
                delete(table).where(
                    and_(
                        table.c.ranking_name == name,
                        table.c.ranking_year == year,
                        table.c.ranking_week == week,
                        table.c.gender == gender,
                    )
                )
            )
        chunk = 200
        for start in range(0, len(rows), chunk):
            conn.execute(table.insert(), rows[start:start + chunk])
    return len(rows), f"{len(comps)} competitors, {len(rows)} ranking rows, {skipped} skipped"


LOADERS: Dict[str, Callable[[Engine, Dict[str, Any]], Tuple[int, str]]] = {
    "competitions": load_competitions,
    "complexes": load_complexes,
    "rankings": load_rankings,
}


# ------------------------------------------------------------------ orchestration
def run_etl(
    engine: Optional[Engine] = None,
    datasets: Iterable[str] = DATASETS,
    use_cache: bool = False,
    demo: bool = False,
    client: Optional[SportradarClient] = None,
    progress: Optional[ProgressFn] = None,
) -> List[Dict[str, Any]]:
    """Run the pipeline and return one result dict per dataset.

    Raises :class:`SportradarError` up-front when live mode has no API key,
    so nothing is modified before the problem is reported.
    """
    engine = engine or db.get_engine()
    db.ensure_schema(engine)
    say = progress or (lambda message: logger.info(message))
    source = "demo" if demo else "sportradar"

    datasets = list(datasets)
    if not demo and client is None:
        client = SportradarClient(**get_api_settings())

    # 1) EXTRACT everything first, so a failed download never wipes existing data.
    payloads: Dict[str, Dict[str, Any]] = {}
    errors: Dict[str, str] = {}
    demo_payloads = build_demo_payloads() if demo else {}
    for dataset in datasets:
        say(f"Extracting {dataset} ({source})...")
        try:
            payloads[dataset] = (
                demo_payloads[dataset] if demo else client.fetch(dataset, use_cache=use_cache)
            )
        except SportradarError as exc:
            errors[dataset] = str(exc)
            logger.error("%s extraction failed: %s", dataset, exc)

    # 2) Demo data and live data must never be mixed in one database.
    if payloads and (demo or db.has_demo_data(engine)):
        say("Clearing existing data before loading a fresh data set...")
        db.purge_data(engine)

    # 3) TRANSFORM + LOAD, one transaction per dataset.
    results: List[Dict[str, Any]] = []
    for dataset in datasets:
        if dataset in errors:
            rows, message, status = 0, errors[dataset], "failed"
        else:
            say(f"Loading {dataset}...")
            try:
                rows, message = LOADERS[dataset](engine, payloads[dataset])
                status = "success"
            except ValueError as exc:
                rows, message, status = 0, str(exc), "failed"
                logger.error("%s failed: %s", dataset, exc)
            except Exception as exc:  # noqa: BLE001 - never let one dataset kill the run
                rows, message, status = 0, f"{type(exc).__name__}: {exc}", "failed"
                logger.exception("Unexpected error while loading %s", dataset)

        with engine.begin() as conn:
            db.log_run(conn, dataset, source, status, rows, message)
        results.append({"dataset": dataset, "status": status, "rows": rows, "message": message})
        say(f"  {dataset}: {status} - {message}")
    return results
