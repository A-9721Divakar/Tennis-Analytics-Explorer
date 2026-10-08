"""Search and filter competitors by name, rank range, country and points."""
import plotly.express as px
import streamlit as st

from src import data_access as da
from src import ui


def render() -> None:
    ui.page_header("🔎 Search & Filter Competitors", "Doubles rankings - pick a snapshot, then slice it.")
    ui.demo_banner()

    with st.container(border=True):
        snap = ui.snapshot_selector("search", allow_all_genders=True)
    if snap is None:
        return
    df = da.rankings_df(snap["year"], snap["week"], snap["gender"])
    if df.empty:
        st.info("This snapshot has no rows.")
        return

    with st.container(border=True):
        c1, c2 = st.columns([2, 2])
        query = c1.text_input("Search by competitor name", placeholder="e.g. Novak")
        countries = c2.multiselect("Country", sorted(df["country"].unique()))
        c3, c4 = st.columns(2)
        max_rank = int(df["rank_pos"].max())
        rank_range = c3.slider("Rank range", 1, max_rank, (1, max_rank))
        max_points = int(df["points"].max())
        min_points = c4.slider("Minimum points", 0, max_points, 0)

    out = df[(df["rank_pos"].between(*rank_range)) & (df["points"] >= min_points)]
    if query:
        out = out[out["name"].str.contains(query, case=False, na=False)]
    if countries:
        out = out[out["country"].isin(countries)]

    m = st.columns(4)
    m[0].metric("Competitors", f"{len(out):,}")
    m[1].metric("Countries", out["country"].nunique())
    m[2].metric("Avg points", f"{out['points'].mean():,.0f}" if len(out) else "-")
    m[3].metric("Best rank", int(out["rank_pos"].min()) if len(out) else "-")

    cols = ["rank_pos", "name", "country", "points", "movement", "competitions_played", "gender"]
    ui.paginated_table(out[cols], key="search_table")
    ui.download_csv(out[cols], "competitors_filtered.csv", key="search_dl")

    if len(out) > 1:
        fig = px.scatter(out, x="rank_pos", y="points", color="movement",
                         color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                         hover_data=["name", "country"], title="Rank vs points (colour = weekly movement)",
                         labels={"rank_pos": "Rank", "points": "Points"})
        ui.plot(fig, key="search_scatter")
    ui.footer()
