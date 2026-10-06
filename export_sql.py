"""Generate the SQL deliverables: schema DDL (PostgreSQL + MySQL) and all analysis queries.

    python export_sql.py

Outputs
-------
    sql/schema_postgresql.sql   sql/schema_mysql.sql   sql/queries.sql
"""
from pathlib import Path

from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from src import database as db
from src.queries import QUERIES, SECTIONS

OUT = Path(__file__).parent / "sql"


def ddl(dialect) -> str:
    """CREATE TABLE / INDEX statements for one dialect plus the latest-rankings view."""
    parts = []
    for table in db.metadata.sorted_tables:
        parts.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        for index in sorted(table.indexes, key=lambda i: i.name):
            parts.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
        parts.append("")
    view = db.latest_view_sql(type("E", (), {"dialect": dialect})()).strip()  # reuse the app's view DDL
    parts.append(view + ";")
    return "\n".join(parts).replace("\t", "    ")


def literal_query(query) -> str:
    """Render a catalogue query with its default parameter values inlined."""
    sql = query.sql.replace("{rank}", '"rank"')
    for param in query.params:
        value = f"%{param.default}%" if param.like else param.default
        sql = sql.replace(f":{param.name}", "'" + value.replace("'", "''") + "'")
    return sql + ";"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    header = "-- Game Analytics: Unlocking Tennis Data with the Sportradar API\n"
    (OUT / "schema_postgresql.sql").write_text(
        header + "-- PostgreSQL schema\n\n" + ddl(postgresql.dialect()) + "\n", encoding="utf-8")
    (OUT / "schema_mysql.sql").write_text(
        header + "-- MySQL 8 schema\n\n" + ddl(mysql.dialect()) + "\n", encoding="utf-8")

    lines = [header + "-- All analysis queries (PostgreSQL syntax; parameters shown with their default values)",
             "-- 'rank' is quoted because it is a reserved word in MySQL 8: use `rank` there.\n"]
    for section in SECTIONS:
        lines.append(f"\n-- {'=' * 70}\n-- {section.upper()}\n-- {'=' * 70}\n")
        for q in (q for q in QUERIES if q.section == section):
            lines.append(f"-- {q.qid}. {q.title}\n-- {q.description}\n{literal_query(q)}\n")
    (OUT / "queries.sql").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", *(p.name for p in sorted(OUT.glob("*.sql"))))


if __name__ == "__main__":
    main()
