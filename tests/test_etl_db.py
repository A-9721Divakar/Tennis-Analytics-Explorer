import pytest
from sqlalchemy import text

from src import database as db
from src import etl
from src.api_client import SportradarError
from src.queries import QUERIES, bind_params
from tests.test_transform import COMPETITIONS, COMPLEXES, RANKINGS


def test_demo_pipeline_loads_all_tables(engine):
    results = etl.run_etl(engine, demo=True)
    assert all(r["status"] == "success" for r in results)
    counts = db.table_counts(engine)
    assert counts["competitions"] > 0 and counts["venues"] > 0 and counts["competitor_rankings"] > 0
    assert db.has_demo_data(engine)


def test_every_catalogue_query_runs(engine):
    etl.run_etl(engine, demo=True)
    for query in QUERIES:
        df = db.query_df(query.sql, bind_params(query, {}), engine)
        assert list(df.columns), query.qid


def test_default_parameters_return_rows(engine):
    etl.run_etl(engine, demo=True)
    for qid in ("C3", "C4", "V3", "V7", "R4"):
        query = next(q for q in QUERIES if q.qid == qid)
        assert len(db.query_df(query.sql, bind_params(query, {}), engine)) > 0, qid


def test_loads_are_idempotent(engine):
    etl.load_competitions(engine, COMPETITIONS)
    etl.load_competitions(engine, COMPETITIONS)
    etl.load_complexes(engine, COMPLEXES)
    etl.load_complexes(engine, COMPLEXES)
    counts = db.table_counts(engine)
    assert counts["competitions"] == 3 and counts["venues"] == 2


def test_rankings_reload_replaces_snapshot_but_keeps_history(engine):
    etl.load_rankings(engine, RANKINGS)
    etl.load_rankings(engine, RANKINGS)  # same week again -> no duplicates
    assert db.table_counts(engine)["competitor_rankings"] == 2
    next_week = {"rankings": [dict(RANKINGS["rankings"][0], week=39)]}
    etl.load_rankings(engine, next_week)
    assert db.table_counts(engine)["competitor_rankings"] == 4


def test_latest_view_returns_only_newest_snapshot(engine):
    etl.load_rankings(engine, RANKINGS)
    etl.load_rankings(engine, {"rankings": [dict(RANKINGS["rankings"][0], week=39)]})
    with engine.connect() as conn:
        weeks = {r[0] for r in conn.execute(text("SELECT ranking_week FROM vw_latest_rankings"))}
    assert weeks == {39}


def test_live_mode_without_key_fails_before_touching_data(engine, monkeypatch):
    etl.run_etl(engine, demo=True)
    before = db.table_counts(engine)
    monkeypatch.delenv("SPORTRADAR_API_KEY", raising=False)
    monkeypatch.setattr(etl, "get_api_settings", lambda: {"api_key": None})
    with pytest.raises(SportradarError):
        etl.run_etl(engine, demo=False)
    assert db.table_counts(engine) == before


def test_read_only_guard():
    assert db.validate_read_only("SELECT 1;") == "SELECT 1"
    for bad in ("DROP TABLE competitors", "SELECT 1; SELECT 2", "DELETE FROM venues",
                "UPDATE venues SET city_name='x'", "SELECT * INTO x FROM venues"):
        with pytest.raises(ValueError):
            db.validate_read_only(bad)
