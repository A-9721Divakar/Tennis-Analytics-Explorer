"""Homepage dashboard: headline KPIs and overview charts."""
import plotly.express as px
import streamlit as st

from src import data_access as da
from src import ui


def render() -> None:
    ui.hero(
        "Tennis Analytics Explorer",
        "Competition hierarchies, venues and doubles rankings - powered by the Sportradar Tennis API",
    )
    ui.demo_banner()

    comps = da.competitions_df()
    venues = da.venues_df()
    ranks = da.latest_rankings_df()

    # ---- KPI row -----------------------------------------------------------
    k = st.columns(6)
    k[0].metric("Ranked competitors", f"{ranks['competitor_id'].nunique():,}")
    k[1].metric("Countries represented", f"{ranks['country'].nunique():,}")
    if ranks.empty:
        k[2].metric("Highest points", "-")
    else:
        top = ranks.loc[ranks["points"].idxmax()]
        k[2].metric("Highest points", f"{int(top['points']):,}", help=f"Held by {top['name']} ({top['country']})")
    k[3].metric("Competitions", f"{len(comps):,}")
    k[4].metric("Categories", f"{comps['category_name'].nunique():,}")
    k[5].metric("Venues / complexes", f"{len(venues):,} / {venues['complex_id'].nunique():,}")

    if not ranks.empty:
        st.caption(
            f"Rankings snapshot: week {int(ranks['ranking_week'].max())}, "
            f"{int(ranks['ranking_year'].max())} (latest per gender)."
        )

    # ---- Charts ------------------------------------------------------------
    left, right = st.columns(2)
    with left:
        by_cat = (
            comps.groupby("category_name").size().reset_index(name="competitions")
            .sort_values("competitions", ascending=False).head(12)
        )
        fig = px.bar(by_cat, x="competitions", y="category_name", orientation="h",
                     title="Competitions by category", labels={"competitions": "Competitions", "category_name": ""})
        fig.update_layout(yaxis=dict(autorange="reversed"))
        ui.plot(fig, key="home_cat")
    with right:
        mix = comps.groupby(["type", "gender"]).size().reset_index(name="competitions")
        fig = px.sunburst(mix, path=["type", "gender"], values="competitions",
                          title="Competition mix: type → gender")
        ui.plot(fig, key="home_mix")

    left, right = st.columns(2)
    with left:
        top10 = ranks.nlargest(10, "points").sort_values("points")
        fig = px.bar(top10, x="points", y="name", color="gender", orientation="h",
                     title="Top 10 competitors by points", labels={"points": "Points", "name": ""})
        ui.plot(fig, key="home_top10")
    with right:
        fig = px.histogram(ranks, x="movement", color="gender", nbins=21, barmode="overlay",
                           opacity=0.75, title="Weekly rank movement distribution",
                           labels={"movement": "Rank movement (+ = moved up)"})
        ui.plot(fig, key="home_move")

    by_country = ranks.groupby(["country", "country_code"]).size().reset_index(name="competitors")
    fig = px.choropleth(by_country, locations="country_code", color="competitors", hover_name="country",
                        color_continuous_scale="Greens", title="Where the ranked competitors come from")
    fig.update_layout(geo=dict(showframe=False, showcoastlines=False, projection_type="natural earth"))
    ui.plot(fig, key="home_map")
    ui.footer()
