"""Game Analytics: Unlocking Tennis Data with the Sportradar API - Streamlit entry point.

Run locally:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="Tennis Analytics Explorer",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src import data_access as da  # noqa: E402
from src import ui  # noqa: E402
from views import (  # noqa: E402
    admin,
    competitions,
    competitor_profile,
    competitor_search,
    country_analysis,
    home,
    leaderboards,
    sql_lab,
    venues,
)

PAGES = {
    "🏠 Home": home.render,
    "🏆 Competitions": competitions.render,
    "🏟️ Venues & Complexes": venues.render,
    "🔎 Search Competitors": competitor_search.render,
    "👤 Competitor Profile": competitor_profile.render,
    "🌍 Country Analysis": country_analysis.render,
    "🥇 Leaderboards": leaderboards.render,
    "🧮 SQL Lab": sql_lab.render,
    "⚙️ Data Admin": admin.render,
}


def main() -> None:
    ui.inject_css()
    with st.sidebar:
        st.markdown("## 🎾 Tennis Analytics")
        st.caption("Sportradar Event Explorer")
        page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
        st.divider()
        try:
            counts = da.table_counts()
            st.caption(
                f"**{counts['competitions']:,}** competitions · **{counts['venues']:,}** venues · "
                f"**{counts['competitors']:,}** competitors"
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Database unavailable: {exc}")
            st.stop()
        if st.button("↻ Refresh data cache", width="stretch"):
            da.clear_caches()
            st.rerun()

    if not da.has_data() and page != "⚙️ Data Admin":
        admin.render_empty_state()
        return
    PAGES[page]()


main()
