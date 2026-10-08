"""Cached data-access functions used by the Streamlit views.

All heavy lifting is done in SQL; results are cached briefly so widget
interactions stay snappy while the data stays "live" (5-minute TTL).
"""
from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

import pandas as pd
import streamlit as st

from src import database as db
from src.queries import QUERY_INDEX, bind_params

TTL_SECONDS = 300


@st.cache_resource(show_spinner=False)
def get_engine():
    """One shared engine per Streamlit server process."""
    engine = db.get_engine()
    db.ensure_schema(engine)
    return engine


def _query(sql: str, params: Optional[dict] = None) -> pd.DataFrame:
    return db.query_df(sql, params, engine=get_engine())


def clear_caches() -> None:
    """Invalidate cached query results (call after an ETL run)."""
    st.cache_data.clear()


# ------------------------------------------------------------------- overview
@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def table_counts() -> Dict[str, int]:
    return db.table_counts(get_engine())


def has_data() -> bool:
    counts = table_counts()
    return any(counts.get(t, 0) > 0 for t in ("competitions", "venues", "competitor_rankings"))


@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def has_demo() -> bool:
    return db.has_demo_data(get_engine())


@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def etl_runs_df(limit: int = 30) -> pd.DataFrame:
    df = _query(
        "SELECT run_id, run_at, dataset, source, status, rows_loaded, message "
        "FROM etl_runs ORDER BY run_id DESC"
    )
    return df.head(limit)


# --------------------------------------------------------------- competitions
@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def competitions_df() -> pd.DataFrame:
    df = _query(
        """
        SELECT c.competition_id, c.competition_name, c.parent_id, c.type, c.gender,
               c.category_id, cat.category_name
        FROM competitions c
        LEFT JOIN categories cat ON cat.category_id = c.category_id
        ORDER BY cat.category_name, c.competition_name
        """
    )
    df["category_name"] = df["category_name"].fillna("Uncategorised")
    df["level"] = df["parent_id"].apply(lambda v: "Sub-competition" if pd.notna(v) else "Top-level")
    return df


# --------------------------------------------------------------------- venues
@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def venues_df() -> pd.DataFrame:
    df = _query(
        """
        SELECT v.venue_id, v.venue_name, v.city_name, v.country_name, v.country_code,
               v.timezone, v.complex_id, cx.complex_name
        FROM venues v
        LEFT JOIN complexes cx ON cx.complex_id = v.complex_id
        ORDER BY v.country_name, v.city_name, v.venue_name
        """
    )
    df["complex_name"] = df["complex_name"].fillna("(no complex)")
    return df


# ------------------------------------------------------------------- rankings
_RANK_SELECT = """
    SELECT cr.rank_id, cr.{rank} AS rank_pos, cr.movement, cr.points, cr.competitions_played,
           cr.ranking_name, cr.ranking_year, cr.ranking_week, cr.gender,
           c.competitor_id, c.name, c.country, c.country_code, c.abbreviation
"""


@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def snapshots_df() -> pd.DataFrame:
    return _query(
        """
        SELECT ranking_year, ranking_week, gender, COUNT(*) AS competitors
        FROM competitor_rankings
        GROUP BY ranking_year, ranking_week, gender
        ORDER BY ranking_year DESC, ranking_week DESC, gender
        """
    )


@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def latest_rankings_df() -> pd.DataFrame:
    return _query(
        _RANK_SELECT
        + """
        FROM vw_latest_rankings cr
        JOIN competitors c ON c.competitor_id = cr.competitor_id
        ORDER BY cr.gender, cr.{rank}
        """
    )


@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def rankings_df(year: int, week: int, gender: str) -> pd.DataFrame:
    return _query(
        _RANK_SELECT
        + """
        FROM competitor_rankings cr
        JOIN competitors c ON c.competitor_id = cr.competitor_id
        WHERE cr.ranking_year = :year AND cr.ranking_week = :week
          AND (:gender = 'all' OR cr.gender = :gender)
        ORDER BY cr.gender, cr.{rank}
        """,
        {"year": year, "week": week, "gender": gender},
    )


@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def competitors_df() -> pd.DataFrame:
    return _query(
        "SELECT competitor_id, name, country, country_code, abbreviation "
        "FROM competitors ORDER BY name"
    )


@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def competitor_history(competitor_ids: Tuple[str, ...]) -> pd.DataFrame:
    """Ranking history (one row per snapshot) for the given competitors."""
    if not competitor_ids:
        return pd.DataFrame()
    placeholders = ", ".join(f":id{i}" for i in range(len(competitor_ids)))
    params = {f"id{i}": cid for i, cid in enumerate(competitor_ids)}
    df = _query(
        _RANK_SELECT
        + f"""
        FROM competitor_rankings cr
        JOIN competitors c ON c.competitor_id = cr.competitor_id
        WHERE cr.competitor_id IN ({placeholders})
        ORDER BY cr.ranking_year, cr.ranking_week
        """,
        params,
    )
    if not df.empty:
        df["snapshot"] = df["ranking_year"].astype(str) + "-W" + df["ranking_week"].astype(str).str.zfill(2)
    return df


# ------------------------------------------------------------------- SQL lab
@st.cache_data(ttl=60, show_spinner=False)
def run_named_query(qid: str, values: Tuple[Tuple[str, str], ...]) -> Tuple[pd.DataFrame, float]:
    """Execute a catalogue query. Returns (result, elapsed_ms)."""
    query = QUERY_INDEX[qid]
    started = time.perf_counter()
    df = _query(query.sql, bind_params(query, dict(values)))
    return df, (time.perf_counter() - started) * 1000


@st.cache_data(ttl=TTL_SECONDS, show_spinner=False)
def param_options(options_sql: str) -> Tuple[str, ...]:
    df = _query(options_sql)
    return tuple(str(v) for v in df.iloc[:, 0].dropna().tolist())


def run_custom(sql: str, max_rows: int = 1000) -> Tuple[pd.DataFrame, float]:
    started = time.perf_counter()
    df = db.run_custom_query(sql, max_rows=max_rows, engine=get_engine())
    return df, (time.perf_counter() - started) * 1000
