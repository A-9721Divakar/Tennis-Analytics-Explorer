"""SQL Lab: every required query, a read-only playground and the schema."""
import streamlit as st

from src import data_access as da
from src import database as db
from src import ui
from src.queries import QUERIES, QUERY_INDEX, SECTIONS

ER_DIAGRAM = """
digraph ER {
  rankdir=LR; bgcolor="transparent";
  node [shape=record, style="rounded,filled", fillcolor="#F6FAF7", color="#0B6E4F", fontname="Helvetica", fontsize=11];
  edge [color="#0B6E4F", fontname="Helvetica", fontsize=9];
  categories [label="{categories|+ category_id (PK)\\l  category_name\\l}"];
  competitions [label="{competitions|+ competition_id (PK)\\l  competition_name\\l  parent_id\\l  type\\l  gender\\l# category_id (FK)\\l}"];
  complexes [label="{complexes|+ complex_id (PK)\\l  complex_name\\l}"];
  venues [label="{venues|+ venue_id (PK)\\l  venue_name\\l  city_name\\l  country_name\\l  country_code\\l  timezone\\l# complex_id (FK)\\l}"];
  competitors [label="{competitors|+ competitor_id (PK)\\l  name\\l  country\\l  country_code\\l  abbreviation\\l}"];
  competitor_rankings [label="{competitor_rankings|+ rank_id (PK)\\l  rank\\l  movement\\l  points\\l  competitions_played\\l  ranking_year / week / gender\\l# competitor_id (FK)\\l}"];
  categories -> competitions [label="1 : N"];
  complexes -> venues [label="1 : N"];
  competitors -> competitor_rankings [label="1 : N"];
  competitions -> competitions [label="parent_id (self)"];
}
"""


def _param_widgets(query, key: str) -> dict:
    values = {}
    for param in query.params:
        options = da.param_options(param.options_sql) if param.options_sql else ()
        if options and not param.like:
            index = options.index(param.default) if param.default in options else 0
            values[param.name] = st.selectbox(param.label, options, index=index, key=f"{key}_{param.name}")
        elif options and param.like:
            values[param.name] = st.text_input(
                param.label, value=param.default, key=f"{key}_{param.name}",
                help=f"Known complexes: {', '.join(options[:8])}{'...' if len(options) > 8 else ''}",
            )
        else:
            values[param.name] = st.text_input(param.label, value=param.default, key=f"{key}_{param.name}")
    return values


def _catalogue_tab() -> None:
    section = st.radio("Section", SECTIONS, horizontal=True)
    options = [q.qid for q in QUERIES if q.section == section]
    qid = st.selectbox("Query", options, format_func=lambda i: f"{i} - {QUERY_INDEX[i].title}")
    query = QUERY_INDEX[qid]
    st.caption(query.description)

    values = _param_widgets(query, key=f"q_{qid}")
    st.markdown("**SQL** (shown for your active database)")
    st.code(db.render_sql(query.sql, da.get_engine()), language="sql")

    try:
        df, elapsed = da.run_named_query(qid, tuple(sorted(values.items())))
    except Exception as exc:  # noqa: BLE001 - show DB errors to the user, never crash
        st.error(f"Query failed: {exc}")
        return
    st.success(f"{len(df):,} rows · {elapsed:.1f} ms")
    ui.paginated_table(df, key=f"res_{qid}")
    if not df.empty:
        ui.download_csv(df, f"{qid}_result.csv", key=f"dl_{qid}")


def _playground_tab() -> None:
    st.caption("Read-only playground. Only a single SELECT/WITH statement is accepted; results are capped at 1,000 rows.")
    default = "SELECT c.country, COUNT(*) AS competitors\nFROM competitors c\nGROUP BY c.country\nORDER BY competitors DESC"
    sql = st.text_area("SQL", value=default, height=170, key="custom_sql")
    if st.button("▶ Run query", type="primary"):
        try:
            df, elapsed = da.run_custom(sql)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception as exc:  # noqa: BLE001
            st.error(f"Query failed: {exc}")
        else:
            st.success(f"{len(df):,} rows · {elapsed:.1f} ms")
            ui.table(df)
    st.info("Tip: the view `vw_latest_rankings` always holds the current week's rankings per gender.")


def _schema_tab() -> None:
    st.graphviz_chart(ER_DIAGRAM)
    st.markdown(
        "**Design notes**\n\n"
        "- 3NF: categories, complexes and competitors are separate entities referenced by foreign keys.\n"
        "- `competitions.parent_id` models the competition hierarchy (self-reference, NULL for top level).\n"
        "- Ranking rows are stored as weekly **snapshots** (`ranking_year`, `ranking_week`, `gender`), "
        "so re-running the ETL builds rank history instead of overwriting it.\n"
        "- Indexes cover every foreign key and the common filter columns (type/gender, snapshot, rank)."
    )
    counts = da.table_counts()
    st.markdown("**Row counts**")
    st.table({"table": list(counts), "rows": [f"{v:,}" for v in counts.values()]})


def render() -> None:
    ui.page_header("🧮 SQL Lab", "All required analysis queries, executed live against the database.")
    ui.demo_banner()
    tab1, tab2, tab3 = st.tabs(["📚 Query catalogue", "🧪 Playground", "🗺️ Schema"])
    with tab1:
        _catalogue_tab()
    with tab2:
        _playground_tab()
    with tab3:
        _schema_tab()
    ui.footer()
