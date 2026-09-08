# Next Steps — Configuration

Status as of 2026-09-08. Scope is **configuration and scaffolding only** — the ingest,
transform, index, and retrieve logic is yours to write per the project brief.

Environment already verified working: Codespace (2 cores, 7.8 GB RAM, 27 GB free),
Python 3.12.14, Postgres 17.11 reachable on `localhost:5432`, pgvector 0.8.6 available,
`requests` / `psycopg` / `python-dotenv` installed.

---

## 1. Commit the pending environment fixes

Three uncommitted changes are sitting in the working tree. Get them in before anything
else, so a rebuild can't lose them.

```
M .devcontainer/devcontainer.json    # postCreateCommand path was wrong
M .devcontainer/docker-compose.yml   # your earlier edits
?? .gitignore                        # .env, __pycache__ now covered
```

Check `git diff .devcontainer/docker-compose.yml` first — those edits predate this
session and I haven't reviewed what you changed.

The `devcontainer.json` fix matters: `postCreateCommand` pointed at `requirements.txt`
relative to `workspaceFolder`, but the file is at `.devcontainer/requirements.txt`. It
had been failing silently on every rebuild, which is why no dependencies were installed.

---

## 2. `STEAM_API_KEY` — blocks milestone 2, and milestone 3 behind it

Not set in this container. Nothing else on this list is blocked by it, so do it early
and let the rebuild happen while you work on the rest.

1. github.com/settings/codespaces → **Codespaces secrets** → New secret
2. Name it exactly `STEAM_API_KEY`, scope it to this repository
3. **Rebuild the container** — Command Palette → *Codespaces: Rebuild Container*.
   A restart will not inject a new secret; it is only read at container create.
4. Verify: `echo ${#STEAM_API_KEY}` should print a non-zero length.

Print the length, never the value — it ends up in your terminal scrollback and in any
transcript you share.

The secret arrives as a real environment variable, so `os.environ["STEAM_API_KEY"]` is
all you need. `python-dotenv` is in requirements for local `.env` use; you do not need
a `.env` for the key itself, and shouldn't create one for it.

---

## 3. `CREATE EXTENSION vector` — milestone 1

I confirmed this succeeds (ran it in a transaction, rolled back), but left it uninstalled
because it's your checkpoint and because of where it belongs:

**Put it in `index/schema.sql`, not a one-off command.** Your constraint is that the
codespace is disposable and the database must be fully rebuildable from committed files.
A hand-run `CREATE EXTENSION` in a psql session is exactly the kind of state that
silently doesn't survive. First line of the file:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Milestone 1 is then "applying `schema.sql` to an empty database succeeds", which is a
stronger and more useful checkpoint than the extension alone.

---

## 4. Scaffold the repo layout

None of these exist yet. Creating the directories now — even empty — makes the
ingest/transform/index separation (principle 3) structural rather than aspirational:

```
ingest/      achievements.py, guides.py, cache/
transform/   parse_subgame.py, chunk.py, link.py
index/       embed.py, schema.sql
retrieve/    resolve.py, search.py, generate.py
eval/        goldset.py, metrics.py
api/
```

`ingest/cache/` holds raw JSON and **is committed** — the `.gitignore` I wrote carries
a comment saying so, since it looks exactly like something a future cleanup would ignore.
Git won't track an empty directory, so add a `.gitkeep` if you want the structure
committed before there's data in it.

Note the brief's layout names the root `steam-achievement-rag/` but the repo is
`agentic-rag-app`. Cosmetic — just don't let it turn into a package-name mismatch later.

---

## 5. Decide the DB connection contract

You'll need this in the first ingest script, and it's worth settling once rather than
hardcoding a connection string in five files.

Current credentials, from `docker-compose.yml`:

```
host=localhost dbname=achievements user=postgres password=postgres
```

`network_mode: service:db` means the app container shares the db container's network
namespace, so `localhost` is correct here — not `db`. That's unusual enough to be worth
a comment wherever you write it down.

The decision: a `DATABASE_URL` env var (set in `docker-compose.yml` under the `app`
service, so it survives rebuilds) versus a `.env` file. The compose route keeps it
in a committed file and matches how `STEAM_API_KEY` already arrives; the `.env` route
generalises better if you ever point at a non-local database. Either is defensible —
pick one and keep it out of the application modules.

---

## 6. Optional: `psql` client

Not installed, and not required — `psycopg` covers every programmatic need. But
**milestone 4 is hand-inspection**, and a REPL is genuinely better than a Python
one-liner for poking at 700 rows. If you want it, add to `devcontainer.json`:

```json
"features": {
    "ghcr.io/devcontainers/features/postgresql-client:1": {}
}
```

Takes effect on the next rebuild — so decide before you rebuild for `STEAM_API_KEY`
and get both in one pass.

---

## Ordering

Steps 1 and 4 are free and unblock nothing else — do them now.
Step 6 must be decided *before* the step 2 rebuild if you want it.
Step 2's rebuild is the long pole. Kick it off, then do step 3 and step 5 while it runs.

After that you're at milestone 3 (fetch schema + global percentages, commit raw JSON),
which is where you start writing code and I go back to reviewing rather than scaffolding.

Remember the constraint that shapes the ingest scripts: **they capture and do not parse.**
Write raw JSON to `ingest/cache/`, nothing else. That's what lets you rewrite the parser
in milestone 5 without re-hitting the Steam API — and what makes milestone 4's
hand-inspection possible at all.
