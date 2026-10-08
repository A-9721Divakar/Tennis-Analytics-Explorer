import pytest
from sqlalchemy import create_engine

from src import database as db


@pytest.fixture()
def engine(tmp_path):
    """A throw-away SQLite database with the full schema."""
    eng = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    db.ensure_schema(eng)
    return eng
