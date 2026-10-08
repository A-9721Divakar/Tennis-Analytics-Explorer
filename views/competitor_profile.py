"""Competitor details viewer with rank / points history and comparison."""
import plotly.express as px
import streamlit as st

from src import data_access as da
from src import ui


def render() -> None:
    ui.page_header("👤 Competitor Profile", "Rank, movement, competitions played and history for a single competitor.")
    ui.demo_banner()

    people = da.competitors_df()
    if people.empty:
        st.info("No competitors loaded yet.")
        return
    labels = {
        row.competitor_id: f"{row.name} ({row.country_code})" for row in people.itertuples(index=False)
    }
    ids = list(labels)
    chosen = st.selectbox("Choose a competitor (type to search)", ids, format_func=lambda i: labels[i])

    history = da.competitor_history((chosen,))
    if history.empty:
        st.warning("This competitor has no ranking rows.")
        return
    current = history.iloc[-1]
    previous = history.iloc[-2] if len(history) > 1 else None

    st.markdown(f"### {current['name']} · {current['country']}")
    m = st.columns(5)
    m[0].metric("Current rank", f"#{int(current['rank_pos'])}", delta=f"{int(current['movement']):+d} vs last week")
    m[1].metric("Points", f"{int(current['points']):,}",
                delta=None if previous is None else f"{int(current['points'] - previous['points']):+,}")
    m[2].metric("Competitions played", int(current["competitions_played"]))
    m[3].metric("Country code", current["country_code"])
    m[4].metric("Snapshot", f"{int(current['ranking_year'])}-W{int(current['ranking_week']):02d}")

    latest = da.rankings_df(int(current["ranking_year"]), int(current["ranking_week"]), str(current["gender"]))
    if not latest.empty:
        percentile = (latest["points"] < current["points"]).mean() * 100
        st.progress(min(max(percentile / 100, 0.0), 1.0),
                    text=f"Scores more points than {percentile:.0f}% of the {current['gender']} field")
        peers = latest[(latest["country"] == current["country"]) & (latest["competitor_id"] != chosen)]
        if not peers.empty:
            with st.expander(f"Other ranked competitors from {current['country']} ({len(peers)})"):
                ui.table(peers[["rank_pos", "name", "points", "movement"]])

    st.markdown("#### History & comparison")
    compare = st.multiselect(
        "Compare with (optional, max 3)", [i for i in ids if i != chosen],
        format_func=lambda i: labels[i], max_selections=3,
    )
    hist = da.competitor_history(tuple([chosen] + compare))
    if hist["snapshot"].nunique() < 2:
        st.info("Only one weekly snapshot is stored so far. Re-run the ETL each week and the history charts fill in.")
        ui.table(hist[["snapshot", "name", "rank_pos", "points", "movement", "competitions_played"]])
    else:
        left, right = st.columns(2)
        with left:
            fig = px.line(hist, x="snapshot", y="rank_pos", color="name", markers=True, title="Rank over time",
                          labels={"rank_pos": "Rank", "snapshot": ""})
            fig.update_yaxes(autorange="reversed")
            ui.plot(fig, key="prof_rank")
        with right:
            fig = px.line(hist, x="snapshot", y="points", color="name", markers=True, title="Points over time",
                          labels={"points": "Points", "snapshot": ""})
            ui.plot(fig, key="prof_points")
    ui.footer()
