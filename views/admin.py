"""Data Admin: pipeline status, ETL trigger and demo-data loader."""
import hmac

import streamlit as st

from config import get_api_settings, get_setting
from src import data_access as da
from src import etl
from src import ui


def _authorised() -> bool:
    """Optional password gate (set ADMIN_PASSWORD in secrets / env)."""
    password = get_setting("ADMIN_PASSWORD")
    if not password:
        return True
    if st.session_state.get("admin_ok"):
        return True
    entered = st.text_input("Admin password", type="password")
    if entered and hmac.compare_digest(entered, password):
        st.session_state["admin_ok"] = True
        st.rerun()
    elif entered:
        st.error("Incorrect password.")
    return False


def _run(demo: bool, use_cache: bool) -> None:
    with st.status("Running ETL pipeline...", expanded=True) as status:
        try:
            results = etl.run_etl(demo=demo, use_cache=use_cache, progress=st.write, engine=da.get_engine())
        except Exception as exc:  # noqa: BLE001 - surface any setup problem to the user
            status.update(label="ETL could not start", state="error")
            st.error(str(exc))
            return
        failed = [r for r in results if r["status"] != "success"]
        status.update(
            label="ETL finished with errors" if failed else "ETL finished successfully",
            state="error" if failed else "complete",
        )
    da.clear_caches()
    for r in results:
        (st.success if r["status"] == "success" else st.error)(f"**{r['dataset']}** - {r['message']}")


def render_empty_state() -> None:
    ui.hero("Welcome to Tennis Analytics Explorer", "The database is empty - load some data to get started.")
    st.markdown(
        "1. **Live data**: add `SPORTRADAR_API_KEY` (see README) and open **Data Admin → Run ETL**.\n"
        "2. **Just exploring?** Load the built-in *demo* data set (fictional players) with one click."
    )
    if st.button("🧪 Load demo data", type="primary"):
        _run(demo=True, use_cache=False)
        st.rerun()


def render() -> None:
    ui.page_header("⚙️ Data Admin", "Pipeline status and data refresh.")
    if not _authorised():
        return

    counts = da.table_counts()
    cols = st.columns(len(counts) - 1)
    for col, (name, value) in zip(cols, [(k, v) for k, v in counts.items() if k != "etl_runs"]):
        col.metric(name.replace("_", " ").title(), f"{value:,}")

    if da.has_demo():
        st.warning("Currently showing **demo** data.", icon="🧪")

    api = get_api_settings()
    st.markdown("#### Refresh data")
    st.caption("API key: " + ("✅ configured" if api["api_key"] else "❌ not set") +
               f" · access level: `{api['access_level']}`")
    c1, c2 = st.columns(2)
    with c1:
        use_cache = st.checkbox("Reuse cached raw JSON if available (no API calls)", value=False)
        if st.button("🔄 Run ETL with live Sportradar data", type="primary", disabled=not api["api_key"]):
            _run(demo=False, use_cache=use_cache)
    with c2:
        confirm = st.checkbox("Replace ALL current data with fictional demo data")
        if st.button("🧪 Load demo data", disabled=not confirm):
            _run(demo=True, use_cache=False)

    st.markdown("#### ETL run history")
    runs = da.etl_runs_df()
    if runs.empty:
        st.caption("No ETL runs recorded yet.")
    else:
        ui.table(runs)
    ui.footer()
