# Deployment guide (Streamlit Community Cloud + free PostgreSQL)

Streamlit Cloud's disk is ephemeral, so use a hosted database. **Neon** or **Supabase** both have free PostgreSQL tiers.

## 1. Create the database
1. Create a project on https://neon.tech (or Supabase) and copy the connection string, e.g.
   `postgresql://user:pass@host/dbname?sslmode=require`.
2. Optional: run `sql/schema_postgresql.sql` in its SQL editor (the app also creates the schema itself).

## 2. Load the data (from your laptop)
Put the connection string in `.env` as `DATABASE_URL`, then:
```bash
python run_etl.py
```
Check row counts in the output.

## 3. Push to GitHub
```bash
git init && git add . && git commit -m "Tennis analytics project"
git branch -M main
git remote add origin https://github.com/<you>/tennis-analytics.git
git push -u origin main
```
`.env` and `secrets.toml` are git-ignored - never commit keys. Also commit `sql/queries.sql` (required deliverable).

## 4. Deploy
1. https://share.streamlit.io → **New app** → select the repo, branch `main`, main file `app.py`.
2. **Advanced settings → Secrets**, paste (see `.streamlit/secrets.toml.example`):
   ```toml
   DATABASE_URL = "postgresql://..."
   SPORTRADAR_API_KEY = "..."
   ADMIN_PASSWORD = "choose-one"
   ```
3. Deploy. Add the public URL to your README.

## Alternative: no external database
Remove `data/*.db` from `.gitignore`, run `python run_etl.py`, commit `data/tennis.db`, and deploy without `DATABASE_URL`. The app is then read-only demo-style (changes are lost on restart).

## Troubleshooting
| Symptom | Fix |
|---|---|
| `HTTP 403` from Sportradar | Key not enabled for the Tennis API, or wrong `SPORTRADAR_ACCESS_LEVEL` |
| `HTTP 429` | Trial keys allow ~1 call/sec; the client retries automatically |
| `ModuleNotFoundError` | Activate the venv, `pip install -r requirements.txt` |
| Empty dashboard | Run `python run_etl.py` (or `--demo`) |
| SSL error on cloud DB | Ensure `?sslmode=require` is in `DATABASE_URL` |
