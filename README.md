# 🎾 Game Analytics: Unlocking Tennis Data with the Sportradar API

An end-to-end data project: **Sportradar Tennis API → Python ETL → SQL database → interactive Streamlit dashboard.**

| Layer | Technology |
|---|---|
| Extraction | Python, `requests` (throttling, retries, raw-JSON cache) |
| Storage | SQLAlchemy Core on **PostgreSQL / MySQL / SQLite** (normalised, indexed) |
| Analysis | 27 SQL queries (7 + 7 + 6 required, plus 4 bonus), a `vw_latest_rankings` view |
| App | Streamlit + Plotly, 9 pages, pagination, CSV export, read-only SQL playground |
| Quality | 18 pytest tests, PEP 8 / pyflakes clean, GitHub Actions CI |

## Project structure

```
app.py                  Streamlit entry point (navigation + routing)
run_etl.py              CLI: extract -> transform -> load
export_sql.py           Generates sql/*.sql deliverables
config.py               Settings (env / .env / Streamlit secrets)
src/api_client.py       Sportradar client (rate limit, retry, cache, key redaction)
src/etl.py              Pure transform functions + idempotent loaders + audit log
src/database.py         Schema, indexes, view, upsert, read-only SQL guard
src/queries.py          Catalogue of every required SQL query
src/demo_data.py        Fictional demo payloads (offline testing)
src/data_access.py      Cached queries for the UI
src/ui.py               Charts, tables, filters, styling
views/                  One module per dashboard page
sql/                    schema_postgresql.sql, schema_mysql.sql, queries.sql
tests/                  pytest suite
docs/                   PROJECT_REPORT.md, DEPLOYMENT.md
```

## Quick start (VS Code)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate            # Windows      (macOS/Linux: source .venv/bin/activate)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
copy .env.example .env            # macOS/Linux: cp .env.example .env
#    edit .env and set SPORTRADAR_API_KEY (get one at https://console.sportradar.com/signup)

# 4. Load data
python run_etl.py                 # live API data
#  or: python run_etl.py --demo   # fictional data, no key needed

# 5. Launch the dashboard
streamlit run app.py
```

In VS Code choose the `.venv` interpreter (`Ctrl+Shift+P` → *Python: Select Interpreter*) and run the commands above in the integrated terminal.

### Using PostgreSQL or MySQL
Set `DATABASE_URL` in `.env` (examples in `.env.example`). Tables and the view are created automatically; DDL is also in `sql/`.

### ETL options
| Command | Effect |
|---|---|
| `python run_etl.py` | Fetch all three endpoints and load them |
| `python run_etl.py --only rankings` | Refresh one dataset (run weekly to build rank history) |
| `python run_etl.py --use-cache` | Reload the raw JSON saved in `data/raw/` without calling the API |
| `python run_etl.py --demo` | Load fictional sample data |

## Dashboard pages
Home KPIs · Competition explorer (filters, hierarchy tree, treemap) · Venues & complexes · Competitor search (name / rank range / country / points) · Competitor profile (history + comparison) · Country analysis (choropleth) · Leaderboards · **SQL Lab** (all required queries with parameters, playground, ER diagram) · Data Admin (ETL trigger, run log).

## Design highlights
- **Idempotent loads** – upserts by primary key; re-running never duplicates rows.
- **Rank history** – ranking rows are weekly snapshots; the current week is exposed via `vw_latest_rankings`.
- **Safe by design** – API key redacted from errors, parameterised SQL only, SELECT-only playground, optional admin password.
- **Failure isolation** – extraction happens before any data is replaced; one failing dataset does not stop the others; every step is logged in `etl_runs`.
- **Portable SQL** – reserved word `rank` is quoted per dialect.

## Tests
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Deployment
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and the write-up in [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md).

> Demo data is entirely fictional; a banner is shown in the app whenever it is loaded.
