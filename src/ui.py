"""Reusable Streamlit UI helpers: styling, charts, tables, filters."""
from __future__ import annotations

import math
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from src import data_access as da

PALETTE = ["#0B6E4F", "#F2A900", "#C8553D", "#2E86AB", "#7A9E7E", "#6C4F77", "#A3B18A", "#D98E04"]
px.defaults.color_discrete_sequence = PALETTE
px.defaults.template = "plotly_white"

COLUMN_LABELS = {
    "rank_pos": "Rank",
    "competitions_played": "Comps played",
    "competitor_id": "Competitor ID",
    "competition_id": "Competition ID",
    "competition_name": "Competition",
    "category_name": "Category",
    "ranking_year": "Year",
    "ranking_week": "Week",
    "venue_name": "Venue",
    "city_name": "City",
    "country_name": "Country",
    "country_code": "Code",
    "complex_name": "Complex",
    "parent_id": "Parent ID",
    "total_competitions": "Competitions",
    "total_venues": "Venues",
    "total_competitors": "Competitors",
}

CSS = """
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
.hero {
    background: linear-gradient(120deg, #0B6E4F 0%, #14956B 55%, #F2A900 140%);
    border-radius: 18px; padding: 1.6rem 2rem; margin-bottom: 1.2rem; color: #fff;
}
.hero h1 {margin: 0; font-size: 2.1rem; color: #fff; letter-spacing: -0.5px;}
.hero p {margin: .35rem 0 0 0; font-size: 1.02rem; opacity: .93; color: #fff;}
[data-testid="stMetric"] {
    background: #F6FAF7; border: 1px solid #DDEBE2; border-radius: 14px; padding: .8rem 1rem;
}
[data-testid="stMetricLabel"] p {font-weight: 600; color: #3B5648;}
section[data-testid="stSidebar"] {border-right: 1px solid #DDEBE2;}
.footer {color: #7A8F84; font-size: .8rem; text-align: center; margin-top: 2.5rem;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>🎾 {title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def page_header(title: str, caption: str = "") -> None:
    st.subheader(title)
    if caption:
        st.caption(caption)


def demo_banner() -> None:
    if da.has_demo():
        st.warning(
            "**Demo mode** - you are looking at fictional sample data. Add a Sportradar API key and "
            "run the ETL (Data Admin page) to replace it with real data.",
            icon="🧪",
        )


def plot(fig, key: Optional[str] = None) -> None:
    """Render a Plotly figure with consistent styling."""
    fig.update_layout(
        margin=dict(l=10, r=10, t=55, b=10),
        title_font_size=16,
        legend_title_text="",
    )
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except TypeError:  # older Streamlit versions
        st.plotly_chart(fig, use_container_width=True, key=key)


def prettify(df: pd.DataFrame) -> pd.DataFrame:
    """Friendly column names for display."""
    return df.rename(columns=lambda c: COLUMN_LABELS.get(c, c.replace("_", " ").title()))


def table(df: pd.DataFrame, height: Optional[int] = None) -> None:
    """Interactive, sortable table with friendly headers."""
    kwargs = {"hide_index": True}
    if height is not None:
        kwargs["height"] = height
    try:
        st.dataframe(prettify(df), width="stretch", **kwargs)
    except TypeError:  # older Streamlit versions
        st.dataframe(prettify(df), use_container_width=True, **kwargs)


def paginated_table(df: pd.DataFrame, key: str, default_size: int = 25) -> None:
    """Show a DataFrame in pages so large results never flood the browser."""
    total = len(df)
    if total == 0:
        st.info("No rows match the current filters.")
        return
    sizes = [10, 25, 50, 100]
    c1, c2, c3 = st.columns([1, 1, 3])
    size = c1.selectbox("Rows per page", sizes, index=sizes.index(default_size), key=f"{key}_size")
    pages = max(1, math.ceil(total / size))
    page = c2.number_input("Page", min_value=1, max_value=pages, value=1, step=1, key=f"{key}_page")
    start = (int(page) - 1) * size
    end = min(start + size, total)
    c3.markdown(f"<br>Showing **{start + 1:,}-{end:,}** of **{total:,}** rows", unsafe_allow_html=True)
    table(df.iloc[start:end])


def download_csv(df: pd.DataFrame, filename: str, key: str) -> None:
    st.download_button(
        "⬇️ Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )


def snapshot_selector(key: str, allow_all_genders: bool = False) -> Optional[dict]:
    """Year / week / gender pickers. Defaults to the most recent snapshot."""
    snaps = da.snapshots_df()
    if snaps.empty:
        st.info("No ranking snapshots loaded yet.")
        return None
    cols = st.columns(3)
    years = sorted(snaps["ranking_year"].unique().tolist(), reverse=True)
    year = cols[0].selectbox("Year", years, key=f"{key}_year")
    weeks = sorted(snaps[snaps["ranking_year"] == year]["ranking_week"].unique().tolist(), reverse=True)
    week = cols[1].selectbox("Week", weeks, key=f"{key}_week")
    genders = sorted(
        snaps[(snaps["ranking_year"] == year) & (snaps["ranking_week"] == week)]["gender"].unique().tolist()
    )
    options = (["all"] if allow_all_genders and len(genders) > 1 else []) + genders
    gender = cols[2].selectbox("Gender", options, key=f"{key}_gender")
    return {"year": int(year), "week": int(week), "gender": str(gender)}


def footer() -> None:
    st.markdown(
        '<div class="footer">Game Analytics: Unlocking Tennis Data with the Sportradar API · '
        "Python · SQL · Streamlit</div>",
        unsafe_allow_html=True,
    )
