"""Relational schema and database helpers (SQLAlchemy Core).

The same code runs on SQLite (zero-setup default), PostgreSQL and MySQL.
Tables follow the project brief; a few extra columns (ranking year/week/gender)
let us store weekly ranking *snapshots* so history builds up over time.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, Mapping, Optional, Sequence

import pandas as pd
from sqlalchemy import (
    CHAR,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Connection, Engine

from config import get_database_url

logger = logging.getLogger(__name__)

metadata = MetaData()
LATEST_VIEW = "vw_latest_rankings"
DEMO_PREFIX = "demo:"

# --------------------------------------------------------------------- schema
categories = Table(
    "categories",
    metadata,
    Column("category_id", String(50), primary_key=True),
    Column("category_name", String(100), nullable=False),
)

competitions = Table(
    "competitions",
    metadata,
    Column("competition_id", String(50), primary_key=True),
    Column("competition_name", String(100), nullable=False),
    Column("parent_id", String(50), nullable=True),
    Column("type", String(20), nullable=False),
    Column("gender", String(10), nullable=False),
    Column("category_id", String(50), ForeignKey("categories.category_id"), nullable=True),
)
Index("ix_competitions_category_id", competitions.c.category_id)
Index("ix_competitions_parent_id", competitions.c.parent_id)
Index("ix_competitions_type_gender", competitions.c.type, competitions.c.gender)

complexes = Table(
    "complexes",
    metadata,
    Column("complex_id", String(50), primary_key=True),
    Column("complex_name", String(100), nullable=False),
)

venues = Table(
    "venues",
    metadata,
    Column("venue_id", String(50), primary_key=True),
    Column("venue_name", String(100), nullable=False),
    Column("city_name", String(100), nullable=False),
    Column("country_name", String(100), nullable=False),
    Column("country_code", CHAR(3), nullable=False),
    Column("timezone", String(100), nullable=False),
    Column("complex_id", String(50), ForeignKey("complexes.complex_id"), nullable=True),
)
Index("ix_venues_complex_id", venues.c.complex_id)
Index("ix_venues_country_name", venues.c.country_name)

competitors = Table(
    "competitors",
    metadata,
    Column("competitor_id", String(50), primary_key=True),
    Column("name", String(100), nullable=False),
    Column("country", String(100), nullable=False),
    Column("country_code", CHAR(3), nullable=False),
    Column("abbreviation", String(10), nullable=False),
)
Index("ix_competitors_country", competitors.c.country)

competitor_rankings = Table(
    "competitor_rankings",
    metadata,
    Column("rank_id", Integer, primary_key=True, autoincrement=True),
    Column("rank", Integer, nullable=False),
    Column("movement", Integer, nullable=False),
    Column("points", Integer, nullable=False),
    Column("competitions_played", Integer, nullable=False),
    Column("competitor_id", String(50), ForeignKey("competitors.competitor_id"), nullable=False),
    # Snapshot columns (extension to the brief - enables week/year/gender filters)
    Column("ranking_name", String(50), nullable=False, server_default="doubles"),
    Column("ranking_year", Integer, nullable=False),
    Column("ranking_week", Integer, nullable=False),
    Column("gender", String(10), nullable=False),
)
Index("ix_rankings_competitor", competitor_rankings.c.competitor_id)
Index(
    "ix_rankings_snapshot",
    competitor_rankings.c.ranking_year,
    competitor_rankings.c.ranking_week,
    competitor_rankings.c.gender,
)
Index("ix_rankings_rank", competitor_rankings.c.rank)

etl_runs = Table(
    "etl_runs",
    metadata,
    Column("run_id", Integer, primary_key=True, autoincrement=True),
    Column("run_at", DateTime, nullable=False),
    Column("dataset", String(30), nullable=False),
    Column("source", String(20), nullable=False),
    Column("status", String(20), nullable=False),
    Column("rows_loaded", Integer, nullable=False, server_default="0"),
    Column("message", String(500), nullable=True),
)


# --------------------------------------------------------------------- engine
@lru_cache(maxsize=4)
def get_engine(url: Optional[str] = None) -> Engine:
    """Create (and cache) the SQLAlchemy engine."""
    url = url or get_database_url()
    kwargs: Dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_recycle"] = 1800
    return create_engine(url, **kwargs)


def latest_view_sql(engine: Engine) -> str:
    """DDL for the 'current week' view (per gender), quoting reserved words."""
    rank = engine.dialect.identifier_preparer.quote("rank")
    return f"""
    CREATE VIEW {LATEST_VIEW} AS
    SELECT cr.rank_id, cr.{rank} AS {rank}, cr.movement, cr.points,
           cr.competitions_played, cr.competitor_id, cr.ranking_name,
           cr.ranking_year, cr.ranking_week, cr.gender
    FROM competitor_rankings cr
    WHERE (cr.ranking_year * 100 + cr.ranking_week) = (
        SELECT MAX(x.ranking_year * 100 + x.ranking_week)
        FROM competitor_rankings x
        WHERE x.gender = cr.gender
    )
    """


def ensure_schema(engine: Engine) -> None:
    """Create tables and the latest-rankings view if they do not exist."""
    metadata.create_all(engine)
    if LATEST_VIEW not in inspect(engine).get_view_names():
        try:
            with engine.begin() as conn:
                conn.execute(text(latest_view_sql(engine)))
        except Exception as exc:  # noqa: BLE001 - another session may have created it
            logger.warning("Could not create view %s: %s", LATEST_VIEW, exc)


def render_sql(sql: str, engine: Engine) -> str:
    """Replace the ``{rank}`` placeholder with a dialect-safe quoted identifier."""
    quoted = engine.dialect.identifier_preparer.quote("rank")
    return sql.replace("{rank}", quoted)


def query_df(
    sql: str, params: Optional[Mapping[str, Any]] = None, engine: Optional[Engine] = None
) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame."""
    engine = engine or get_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text(render_sql(sql, engine)), conn, params=dict(params or {}))


# ---------------------------------------------------------------- read-only SQL
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|replace|attach|"
    r"detach|pragma|vacuum|call|exec|execute|copy|merge|into)\b",
    re.IGNORECASE,
)


def validate_read_only(sql: str) -> str:
    """Return a cleaned single SELECT statement or raise ValueError."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("Please enter a query.")
    if ";" in cleaned:
        raise ValueError("Only a single statement is allowed.")
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")
    if _FORBIDDEN.search(cleaned):
        raise ValueError("This query contains a keyword that is not allowed in read-only mode.")
    return cleaned


def run_custom_query(sql: str, max_rows: int = 1000, engine: Optional[Engine] = None) -> pd.DataFrame:
    """Execute a validated read-only query and return at most ``max_rows`` rows."""
    engine = engine or get_engine()
    cleaned = validate_read_only(sql)
    with engine.connect() as conn:
        result = conn.execute(text(render_sql(cleaned, engine)))
        rows = result.fetchmany(max_rows)
        return pd.DataFrame(rows, columns=list(result.keys()))


# ------------------------------------------------------------------- loading
def upsert_rows(conn: Connection, table: Table, rows: Sequence[Mapping[str, Any]]) -> int:
    """Insert rows, updating existing ones by primary key (idempotent loads)."""
    if not rows:
        return 0
    pk_cols = [c.name for c in table.primary_key.columns]
    update_cols = [c.name for c in table.columns if c.name not in pk_cols]
    chunk_size = max(1, 900 // len(table.columns))  # stays under SQLite's variable limit
    dialect = conn.dialect.name

    for start in range(0, len(rows), chunk_size):
        batch = list(rows[start:start + chunk_size])
        if dialect in ("postgresql", "sqlite"):
            if dialect == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as dialect_insert
            else:
                from sqlalchemy.dialects.sqlite import insert as dialect_insert
            stmt = dialect_insert(table).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=pk_cols, set_={c: stmt.excluded[c] for c in update_cols}
            )
            conn.execute(stmt)
        elif dialect in ("mysql", "mariadb"):
            from sqlalchemy.dialects.mysql import insert as mysql_insert

            stmt = mysql_insert(table).values(batch)
            stmt = stmt.on_duplicate_key_update({c: stmt.inserted[c] for c in update_cols})
            conn.execute(stmt)
        else:  # generic fallback
            for row in batch:
                conn.execute(delete(table).where(*[table.c[k] == row[k] for k in pk_cols]))
                conn.execute(table.insert().values(row))
    return len(rows)


def purge_data(engine: Engine) -> None:
    """Delete all rows (child tables first). Schema and view are kept."""
    with engine.begin() as conn:
        for table in reversed(metadata.sorted_tables):
            conn.execute(delete(table))


def log_run(
    conn: Connection, dataset: str, source: str, status: str, rows: int, message: str = ""
) -> None:
    """Record one ETL step in the etl_runs audit table."""
    conn.execute(
        etl_runs.insert().values(
            run_at=datetime.now(timezone.utc).replace(tzinfo=None),
            dataset=dataset,
            source=source,
            status=status,
            rows_loaded=rows,
            message=(message or "")[:500],
        )
    )


def table_counts(engine: Engine) -> Dict[str, int]:
    """Row count for each table."""
    counts: Dict[str, int] = {}
    with engine.connect() as conn:
        for table in metadata.sorted_tables:
            counts[table.name] = int(conn.execute(select(func.count()).select_from(table)).scalar_one())
    return counts


def has_demo_data(engine: Engine) -> bool:
    """True when the database currently holds the built-in demo data set."""
    with engine.connect() as conn:
        n = conn.execute(
            select(func.count())
            .select_from(categories)
            .where(categories.c.category_id.like(f"{DEMO_PREFIX}%"))
        ).scalar_one()
    return int(n) > 0
