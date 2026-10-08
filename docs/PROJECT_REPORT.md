# Project report - Game Analytics: Unlocking Tennis Data with the Sportradar API

## 1. Objective
Collect competition, venue and doubles-ranking data from the Sportradar Tennis API, store it in a normalised SQL database, answer 20 required analytical questions in SQL, and expose everything through an interactive Streamlit application.

## 2. Workflow
1. **Extract** - `SportradarClient` calls `competitions`, `complexes` and `double_competitors_rankings` (Tennis API v3). It throttles to ~1 req/s, retries 429/5xx with back-off, hides the key in errors, and saves raw JSON to `data/raw/`.
2. **Transform** - pure functions flatten nested JSON: `competitions[].category` → categories + competitions; `complexes[].venues[]` → complexes + venues; `rankings[].competitor_rankings[].competitor` → competitors + rankings. Values are clipped to column size, typed, and defaulted where NOT NULL columns would otherwise fail.
3. **Load** - one transaction per dataset; upserts by primary key; ranking snapshots replaced per (name, year, week, gender). Every step is recorded in `etl_runs`.
4. **Analyse** - `src/queries.py` holds all queries; `export_sql.py` writes them to `sql/queries.sql`.
5. **Present** - Streamlit app reading the database live (5-minute cache).

## 3. Schema design
Six tables per the brief (`categories`, `competitions`, `complexes`, `venues`, `competitors`, `competitor_rankings`) plus `etl_runs`.
- Third normal form: repeated attributes (category name, complex name, competitor details) live in their own tables.
- `competitions.parent_id` is a nullable self-reference (top-level = NULL); it is deliberately not a hard FK because a parent may be absent from a partial download.
- Extension: `competitor_rankings` also stores `ranking_year`, `ranking_week`, `gender`, `ranking_name`, giving weekly history and the Year/Week/Gender filters shown in the brief's sample UI.
- Indexes on all foreign keys, `parent_id`, `(type, gender)`, the snapshot columns and `rank`.
- View `vw_latest_rankings` = newest snapshot per gender, used by all "current week" queries.

## 4. Challenges and solutions
| Challenge | Solution |
|---|---|
| API rate limits | Throttle + exponential back-off + `Retry-After` support |
| Nested JSON | Dedicated transform layer with unit tests |
| Missing / over-long fields vs NOT NULL and VARCHAR limits | Defaults and clipping in one place |
| `rank` reserved in MySQL 8 | `{rank}` placeholder quoted per dialect |
| Cross-database upsert | Dialect-specific `ON CONFLICT` / `ON DUPLICATE KEY` |
| Re-runs creating duplicates | Idempotent loads; snapshot replacement |
| Ephemeral cloud disk | Hosted PostgreSQL via `DATABASE_URL` |
| Public app safety | Parameterised SQL, SELECT-only playground, optional admin password |

## 5. Testing
18 automated tests cover the transforms, API client (retries, auth errors, key redaction, caching), idempotency, snapshot history, the latest-rankings view, the read-only guard, and execution of every catalogue query. The Streamlit pages were also exercised programmatically with Streamlit's `AppTest`.

## 6. Insights
*Complete this section after loading live data - the numbers below must come from your own run.*
- Which categories contain the most competitions, and what share are doubles? (Home page, SQL C2/C6)
- How deep is the hierarchy - which parents have the most sub-competitions? (B1)
- Which countries have the most ranked doubles players and the highest average points? (Country Analysis, R5, B2)
- How many players held a stable rank this week (R3), and who climbed most (B3)?
- Which countries host the most venues, and does that match where the top players come from?

## 7. Future work
Scheduled weekly ETL (GitHub Actions / cron), singles rankings and match results endpoints, player head-to-head, and caching layer with Redis.
