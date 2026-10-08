"""Leaderboards: top-ranked, highest points, biggest movers, most active."""
import plotly.express as px
import streamlit as st

from src import data_access as da
from src import ui


def _board(df, value_col: str, title: str, key: str, n: int, ascending: bool = False) -> None:
    board = df.sort_values([value_col, "rank_pos"], ascending=[ascending, True]).head(n)
    cols = ["rank_pos", "name", "country", "points", "movement", "competitions_played", "gender"]
    ui.table(board[cols])
    chart = board.sort_values(value_col, ascending=not ascending)
    fig = px.bar(chart, x=value_col, y="name", color="gender", orientation="h", title=title,
                 labels={value_col: value_col.replace("_", " ").title(), "name": ""})
    ui.plot(fig, key=key)


def render() -> None:
    ui.page_header("🥇 Leaderboards", "Top performers in the selected ranking snapshot.")
    ui.demo_banner()
    with st.container(border=True):
        snap = ui.snapshot_selector("board", allow_all_genders=True)
    if snap is None:
        return
    df = da.rankings_df(snap["year"], snap["week"], snap["gender"])
    if df.empty:
        st.info("This snapshot has no rows.")
        return
    n = st.slider("Entries to show", 5, 50, 10)

    t1, t2, t3, t4, t5 = st.tabs(
        ["🏅 Top ranked", "💯 Highest points", "🚀 Biggest climbers", "📉 Biggest fallers", "🎯 Most active"]
    )
    with t1:
        board = df.sort_values("rank_pos").head(n)
        ui.table(board[["rank_pos", "name", "country", "points", "movement", "gender"]])
    with t2:
        _board(df, "points", f"Top {n} by points", "lb_points", n)
    with t3:
        _board(df, "movement", f"Top {n} climbers", "lb_up", n)
    with t4:
        _board(df, "movement", f"Top {n} fallers", "lb_down", n, ascending=True)
    with t5:
        _board(df, "competitions_played", f"Top {n} by competitions played", "lb_active", n)
    ui.footer()
