"""Competition explorer: filters, hierarchy navigation and distribution charts."""
import plotly.express as px
import streamlit as st

from src import data_access as da
from src import ui


def render() -> None:
    ui.page_header(
        "🏆 Competition Explorer",
        "Navigate competition hierarchies (e.g. ATP Vienna → Singles / Doubles) and analyse their distribution.",
    )
    ui.demo_banner()
    comps = da.competitions_df()

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        categories = c1.multiselect("Category", sorted(comps["category_name"].unique()))
        types = c2.multiselect("Type", sorted(comps["type"].unique()))
        genders = c3.multiselect("Gender", sorted(comps["gender"].unique()))
        level = c4.selectbox("Level", ["All", "Top-level", "Sub-competition"])
        search = st.text_input("Search competition name", placeholder="e.g. Vienna")

    df = comps
    if categories:
        df = df[df["category_name"].isin(categories)]
    if types:
        df = df[df["type"].isin(types)]
    if genders:
        df = df[df["gender"].isin(genders)]
    if level != "All":
        df = df[df["level"] == level]
    if search:
        df = df[df["competition_name"].str.contains(search, case=False, na=False)]

    m = st.columns(4)
    m[0].metric("Matching competitions", f"{len(df):,}")
    m[1].metric("Categories", df["category_name"].nunique())
    m[2].metric("Top-level", int((df["level"] == "Top-level").sum()))
    m[3].metric("Sub-competitions", int((df["level"] == "Sub-competition").sum()))

    tab_table, tab_hier, tab_charts = st.tabs(["📋 Table", "🌳 Hierarchy explorer", "📊 Distribution"])

    with tab_table:
        show = df[["competition_id", "competition_name", "category_name", "type", "gender", "level", "parent_id"]]
        ui.paginated_table(show, key="comp_table")
        ui.download_csv(show, "competitions_filtered.csv", key="comp_dl")

    with tab_hier:
        parent_ids = set(comps["parent_id"].dropna())
        parents = comps[comps["competition_id"].isin(parent_ids)].sort_values("competition_name")
        if parents.empty:
            st.info("No parent/child relationships found in the loaded data.")
        else:
            labels = dict(zip(parents["competition_id"], parents["competition_name"]))
            chosen = st.selectbox("Parent competition", list(labels), format_func=lambda i: labels[i])
            children = comps[comps["parent_id"] == chosen]
            st.markdown(f"**{labels[chosen]}** has **{len(children)}** sub-competitions")
            ui.table(children[["competition_id", "competition_name", "type", "gender", "category_name"]])
            st.caption("Sub-competitions per parent, top 15")
            counts = (
                comps.dropna(subset=["parent_id"]).groupby("parent_id").size().reset_index(name="sub_competitions")
            )
            counts["parent"] = counts["parent_id"].map(dict(zip(comps["competition_id"], comps["competition_name"])))
            counts = counts.dropna(subset=["parent"]).nlargest(15, "sub_competitions").sort_values("sub_competitions")
            fig = px.bar(counts, x="sub_competitions", y="parent", orientation="h",
                         labels={"sub_competitions": "Sub-competitions", "parent": ""})
            ui.plot(fig, key="comp_hier_bar")

    with tab_charts:
        if df.empty:
            st.info("No data to chart for the current filters.")
        else:
            left, right = st.columns(2)
            with left:
                dist = df.groupby(["category_name", "type"]).size().reset_index(name="competitions")
                fig = px.bar(dist, x="category_name", y="competitions", color="type", barmode="stack",
                             title="Competition types by category", labels={"category_name": ""})
                ui.plot(fig, key="comp_dist")
            with right:
                tree = df.groupby(["category_name", "type", "gender"]).size().reset_index(name="competitions")
                fig = px.treemap(tree, path=[px.Constant("All"), "category_name", "type", "gender"],
                                 values="competitions", title="Category → type → gender")
                ui.plot(fig, key="comp_tree")
    ui.footer()
