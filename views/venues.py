"""Venues & complexes explorer."""
import plotly.express as px
import streamlit as st

from src import data_access as da
from src import ui


def render() -> None:
    ui.page_header("🏟️ Venues & Complexes", "Where the tennis happens: complexes, venues, countries and timezones.")
    ui.demo_banner()
    venues = da.venues_df()

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        countries = c1.multiselect("Country", sorted(venues["country_name"].unique()))
        timezones = c2.multiselect("Timezone", sorted(venues["timezone"].unique()))
        search = c3.text_input("Search venue / city / complex")

    df = venues
    if countries:
        df = df[df["country_name"].isin(countries)]
    if timezones:
        df = df[df["timezone"].isin(timezones)]
    if search:
        mask = (
            df["venue_name"].str.contains(search, case=False, na=False)
            | df["city_name"].str.contains(search, case=False, na=False)
            | df["complex_name"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    m = st.columns(4)
    m[0].metric("Venues", f"{len(df):,}")
    m[1].metric("Complexes", df["complex_id"].nunique())
    m[2].metric("Countries", df["country_name"].nunique())
    m[3].metric("Timezones", df["timezone"].nunique())

    tab_table, tab_charts, tab_multi = st.tabs(["📋 Venues", "📊 Charts", "🏢 Multi-venue complexes"])
    with tab_table:
        cols = ["venue_id", "venue_name", "complex_name", "city_name", "country_name", "country_code", "timezone"]
        ui.paginated_table(df[cols], key="venue_table")
        ui.download_csv(df[cols], "venues_filtered.csv", key="venue_dl")

    with tab_charts:
        if df.empty:
            st.info("No venues match the current filters.")
        else:
            left, right = st.columns(2)
            with left:
                by_country = df.groupby("country_name").size().reset_index(name="venues").nlargest(15, "venues")
                fig = px.bar(by_country.sort_values("venues"), x="venues", y="country_name", orientation="h",
                             title="Venues per country (top 15)", labels={"country_name": ""})
                ui.plot(fig, key="venue_country")
            with right:
                by_complex = df.groupby("complex_name").size().reset_index(name="venues").nlargest(15, "venues")
                fig = px.bar(by_complex.sort_values("venues"), x="venues", y="complex_name", orientation="h",
                             title="Venues per complex (top 15)", labels={"complex_name": ""})
                ui.plot(fig, key="venue_complex")
            tz = df.groupby("timezone").size().reset_index(name="venues")
            fig = px.pie(tz, names="timezone", values="venues", hole=0.45, title="Venues by timezone")
            ui.plot(fig, key="venue_tz")

    with tab_multi:
        counts = df.groupby(["complex_id", "complex_name"]).size().reset_index(name="venues")
        multi = counts[counts["venues"] > 1].sort_values("venues", ascending=False)
        st.caption(f"{len(multi)} complexes host more than one venue.")
        ui.table(multi[["complex_name", "venues"]])
    ui.footer()
