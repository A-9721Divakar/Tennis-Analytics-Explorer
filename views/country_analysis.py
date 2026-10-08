"""Country-wise analysis of ranked competitors and venues."""
import plotly.express as px
import streamlit as st

from src import data_access as da
from src import ui


def render() -> None:
    ui.page_header("🌍 Country-wise Analysis", "Which nations dominate doubles - and where do they play?")
    ui.demo_banner()

    with st.container(border=True):
        snap = ui.snapshot_selector("country", allow_all_genders=True)
    if snap is None:
        return
    df = da.rankings_df(snap["year"], snap["week"], snap["gender"])
    if df.empty:
        st.info("This snapshot has no rows.")
        return

    summary = (
        df.groupby(["country", "country_code"])
        .agg(
            competitors=("competitor_id", "nunique"),
            average_points=("points", "mean"),
            total_points=("points", "sum"),
            best_rank=("rank_pos", "min"),
        )
        .reset_index()
        .sort_values(["competitors", "total_points"], ascending=False)
    )
    summary["average_points"] = summary["average_points"].round(1)

    venue_counts = da.venues_df().groupby("country_code").size().rename("venues").reset_index()
    summary = summary.merge(venue_counts, on="country_code", how="left").fillna({"venues": 0})
    summary["venues"] = summary["venues"].astype(int)

    metric = st.radio(
        "Map / chart metric", ["competitors", "total_points", "average_points"],
        horizontal=True, format_func=lambda s: s.replace("_", " ").title(),
    )
    fig = px.choropleth(summary, locations="country_code", color=metric, hover_name="country",
                        hover_data={"competitors": True, "average_points": True, "country_code": False},
                        color_continuous_scale="YlGn", title=f"{metric.replace('_', ' ').title()} by country")
    fig.update_layout(geo=dict(showframe=False, showcoastlines=False, projection_type="natural earth"))
    ui.plot(fig, key="country_map")

    left, right = st.columns(2)
    with left:
        top = summary.nlargest(15, metric).sort_values(metric)
        fig = px.bar(top, x=metric, y="country", orientation="h", title=f"Top 15 countries - {metric.replace('_', ' ')}",
                     labels={"country": "", metric: metric.replace("_", " ").title()})
        ui.plot(fig, key="country_bar")
    with right:
        fig = px.scatter(summary, x="competitors", y="average_points", size="total_points", hover_name="country",
                         color="best_rank", color_continuous_scale="Greens_r",
                         title="Depth vs quality (bubble = total points)",
                         labels={"competitors": "Ranked competitors", "average_points": "Average points"})
        ui.plot(fig, key="country_scatter")

    st.markdown("#### Country table")
    ui.paginated_table(summary, key="country_table", default_size=25)
    ui.download_csv(summary, "country_summary.csv", key="country_dl")
    ui.footer()
