# Next Steps — Configuration

Status as of 2026-09-08. Scope is **configuration and scaffolding only** — the ingest,
transform, index, and retrieve logic is yours to write per the project brief.

The project moved off GitHub Codespaces and now lives here, in this local clone, run
via Docker Desktop + the VS Code Dev Containers extension. This replaces the earlier
Codespaces-specific version of this file.

---

## Already done

- `.devcontainer/docker-compose.yml`: fixed a `network_mode` typo and a misplaced
  `volumes:` block that made the file invalid, added `DATABASE_URL`, and wired the
  root `.env` in via `env_file` (`required: false`, so a fresh clone without `.env`
  yet still starts).
- `.devcontainer/devcontainer.json`: fixed `postCreateCommand`'s path to
  `.devcontainer/requirements.txt`, added the `postgresql-client` feature so `psql`
  is available for milestone 4's hand-inspection.
- `.gitignore` added (`.env`, `__pycache__/`, etc. — `ingest/cache/` deliberately
  excluded from it, since raw API JSON is committed by design).
- Repo scaffolded: `ingest/cache/`, `transform/`, `index/`, `retrieve/`, `eval/`, `api/`.
- `index/schema.sql` written: `CREATE EXTENSION IF NOT EXISTS vector` plus the
  `achievements` / `guides` / `chunks` / `achievement_chunks` DDL from the brief.
- `.env` (local, gitignored) and `.env.example` (committed template) created for
  `STEAM_API_KEY`.

---

## 1. Start Docker Desktop

Checked from this shell — Docker CLI is installed (29.7.2) but the daemon isn't
running. Start Docker Desktop before anything below will work.

---

## 2. Fill in `.env`

Open `.env` at the repo root and set:

```
STEAM_API_KEY=<your key>
```

Never paste the actual value into a chat transcript — if you want to sanity-check it's
set later, print the length (`echo ${#STEAM_API_KEY}`), not the value.

`.env` is gitignored; `.env.example` (committed, no secret) documents the shape for
anyone else who clones this.

---

## 3. Open the devcontainer

With Docker Desktop running: VS Code Command Palette → **Dev Containers: Reopen in
Container**. First build runs `postCreateCommand`
(`pip install -r .devcontainer/requirements.txt`) and pulls the `pgvector/pgvector:pg17`
image for the `db` service.

Verify once it's up, inside the container:

- `echo ${#STEAM_API_KEY}` — non-zero length means `env_file` picked it up from `.env`.
- `psql $DATABASE_URL -c 'select 1'` — confirms `network_mode: service:db` is resolving
  `localhost` to the db container correctly.

---

## 4. Milestone 1 — apply the schema

```
psql $DATABASE_URL -f index/schema.sql
```

Should succeed on the empty `achievements` database created by `db`'s environment
vars. This installs pgvector and creates all four tables in one committed, rebuildable
step — no hand-run `CREATE EXTENSION` to lose if the container is ever rebuilt.

---

## After this

You're at milestone 3 (fetch schema + global percentages, commit raw JSON to
`ingest/cache/`), which is where you start writing code and I go back to reviewing
rather than scaffolding.

Remember the constraint that shapes the ingest scripts: **they capture and do not parse.**
Write raw JSON to `ingest/cache/`, nothing else. That's what lets you rewrite the parser
in milestone 5 without re-hitting the Steam API — and what makes milestone 4's
hand-inspection possible at all.
