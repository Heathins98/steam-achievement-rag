# Implementation Steps

A chronological record of the infrastructure work done on this project — what was
built, why, and the commit each change landed in. Written so this is legible on
review later, not just at the time it happened.

Scope note: everything here is config, scaffolding, and DDL. Per the project brief
(`.claude/Project_Description.md`), application logic — `ingest/`, `transform/`,
`index/embed.py`, `retrieve/`, `eval/` — is written by hand, not documented here as
"implementation" in that sense. This file covers the environment the application
code runs in.

---

## 1. Starting state and a sync problem

The project began in a GitHub Codespace. A prior session there diagnosed several
config bugs and wrote `NEXT_STEPS.md` describing the fixes — but only `NEXT_STEPS.md`
itself was ever committed (`4c03ab5`, "Container updates"). The actual
`docker-compose.yml`/`devcontainer.json` fixes and a planned `.gitignore` existed only
as uncommitted changes inside that disposable Codespace and were never pushed.

This local Windows clone is a separate checkout of `origin/main`, so it had none of
that work — `docker-compose.yml` still had the bugs `NEXT_STEPS.md` described as
already-diagnosed. First step was redoing that work here so it actually lands in git.

---

## 2. Fixed `.devcontainer/docker-compose.yml` (commit `d207626`)

Two structural bugs in the committed file:

- **`rebuinetwork_mode: service:db`** under the `app` service — not a valid Compose
  key, a typo for `network_mode: service:db`. Without it, the `app` container doesn't
  share the `db` container's network namespace, so `localhost:5432` (the connection
  string the whole project assumes) wouldn't reach Postgres from inside `app`.
- **A misplaced `volumes:` block** — the named-volume declaration for `postgres-data`
  was indented as a sibling of `app:`/`db:` under `services:`, so Compose parsed it as
  an invalid third service instead of the top-level `volumes:` key it needed to be.
  Dedented it to sit alongside `services:`.

Also added `DATABASE_URL` to the `app` service's `environment:` block:
```
postgresql://postgres:postgres@localhost:5432/achievements
```
`localhost` here (not the hostname `db`) is correct specifically *because* of
`network_mode: service:db` — documented inline as a comment since it's non-obvious.

## 3. Fixed `.devcontainer/devcontainer.json` (commit `d207626`)

- `postCreateCommand` read `pip install -r requirements.txt`, resolved against
  `workspaceFolder`, but the file actually lives at `.devcontainer/requirements.txt`.
  It had been failing silently on every rebuild — no dependencies were ever installed.
  Fixed to `pip install -r .devcontainer/requirements.txt`.
- Added a `postgresql-client` devcontainer feature so `psql` is available inside the
  container for hand-inspecting rows (this file's own milestone 4). This reference was
  wrong at first — see §7.

## 4. Added `.gitignore` (commit `d207626`)

Covers `.env`, `__pycache__/`, `*.pyc`, `.venv/`/`venv/`. Explicit comment that
`ingest/cache/` is deliberately **not** ignored — raw Steam API JSON is committed on
purpose (the disposable-container constraint means the DB must be rebuildable from
committed files, not re-fetched).

## 5. Scaffolded the repo layout (commit `d207626`)

Created the directories the brief's layout names, each holding only a `.gitkeep`
(git doesn't track empty directories) so the ingest → transform → index → retrieve
separation is structural from day one, before any code exists in them:
```
ingest/cache/.gitkeep
transform/.gitkeep
retrieve/.gitkeep
eval/.gitkeep
api/.gitkeep
```

## 6. Wrote `index/schema.sql` (commit `d207626`)

Pure DDL translating the data model from `Project_Description.md` directly:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE achievements ( ... );        -- api_name PK
CREATE TABLE guides ( ... );              -- published_file_id PK
CREATE TABLE chunks ( ... );              -- FK -> guides, embedding vector(384), tsv tsvector
CREATE TABLE achievement_chunks ( ... );  -- FK -> achievements + chunks, composite PK
```

Table order is dependency order, not arbitrary: `guides` and `achievements` first
(no foreign keys out), then `chunks` (references `guides`), then
`achievement_chunks` last (references both `achievements` and `chunks`) — Postgres
won't let a foreign key point at a table that doesn't exist yet.

`CREATE EXTENSION IF NOT EXISTS vector` is the line that activates pgvector *for this
specific database* — the `pgvector/pgvector:pg17` base image ships the extension's
shared library on disk, but extensions are enabled per-database in Postgres, not
per-server, so this line is what makes the `vector(384)` column type and later
`\dx` listing actually work.

No indexes (ivfflat/HNSW on `embedding`, GIN on `tsv`) were added beyond the columns
themselves — that's a tuning decision tied to query patterns that don't exist yet,
deferred rather than guessed at.

**How this actually gets applied — important, not automatic:** nothing in
`postCreateCommand` or the compose file runs `schema.sql`. It's applied by hand:
```
psql "$DATABASE_URL" -f index/schema.sql
```
This was deliberate — the brief frames "applying `schema.sql` to an empty database
succeeds" as milestone 1's actual checkpoint, meant to be run and watched, not
invisible. Consequence: the `CREATE TABLE` statements have no `IF NOT EXISTS`, so
re-running the file against a database that already has these tables will error. A
clean slate means `docker compose down -v` (drops the `postgres-data` volume) and
re-running `schema.sql` against the fresh empty database — not hand-editing tables in
a `psql` session, for the same "state lives in committed files" reason.

---

## 7. Pivoted from Codespaces to local Docker Desktop (commit `c287d17`)

The project stopped living in a Codespace and moved entirely to this local clone, run
via Docker Desktop + the VS Code Dev Containers extension. Devcontainers are portable
between the two by design, so this didn't require changing the container definition —
only how secrets arrive:

- **`.env`** (repo root, gitignored) and **`.env.example`** (committed template)
  created for `STEAM_API_KEY`, replacing the Codespaces-secrets mechanism.
- **`docker-compose.yml`**: added `env_file` on the `app` service pointing at the
  root `.env`, with `required: false` so a fresh clone without `.env` yet still
  starts:
  ```yaml
  env_file:
    - path: ../.env
      required: false
  ```
  This makes `STEAM_API_KEY` arrive as a real container environment variable
  automatically on container start, the same way Codespaces secrets used to — no
  `python-dotenv`/`load_dotenv()` call needed inside the container.
- **`NEXT_STEPS.md`** rewritten end to end for local Docker Desktop, replacing the
  Codespaces-secrets/rebuild instructions it previously described.

## 8. First devcontainer launch attempts — three real bugs found in sequence

Each fix was verified with `docker compose ... config` / JSON validation before
committing, but only an actual "Reopen in Container" run surfaces some of these —
config that parses is not the same as config that works.

**a. Wrong feature reference (commit `fd48e72`)**
`ghcr.io/devcontainers/features/postgresql-client:1` (added in §3) doesn't exist —
there is no official `postgresql-client` feature under the `devcontainers` org.
GHCR returns `403 DENIED` for an anonymous pull of a nonexistent package rather than
a clean 404, which made the failure look like an auth problem. Corrected to the real
community feature: `ghcr.io/robbert229/devcontainer-features/postgresql-client:1`.

**b. Workspace mount too broad, and misnamed (commit `fd48e72`)**
`docker-compose.yml`'s volume mount was `../..:/workspaces:cached` — two directories
up from `.devcontainer/`, which bound the *entire parent `Projects/` folder*
(every sibling project on disk, not just this repo) into the container as
`/workspaces`. `devcontainer.json`'s `workspaceFolder` pointed at
`/workspaces/agentic-rag-app` (the GitHub repo's name), which doesn't exist inside
the container because this local folder is actually named `steam-achievement-rag`.
Narrowed the mount to just this repo and aligned the workspace folder name:
```yaml
volumes:
    - ..:/workspaces/steam-achievement-rag:cached
```
```json
"workspaceFolder": "/workspaces/steam-achievement-rag",
```

**c. WSLg mount — a wrong diagnosis, kept anyway (commit `28cf9c5`)**
Next failure: `Error response from daemon: accessing specified distro mount service:
stat /run/guest-services/distro-services/ubuntu.sock: no such file or directory`.
Initial diagnosis (via a GitHub issue on the same error signature) was that Dev
Containers' automatic WSLg/Wayland-socket bind mount was the cause, and the fix
added was a committed workspace setting:
```json
// .vscode/settings.json
{ "remote.containers.enableWSLg": false }
```
This didn't actually resolve it — the wayland mount kept appearing in the generated
Compose override regardless. Left in place anyway since it's a reasonable setting
for a headless Python/Postgres project with no GUI needs, but it wasn't the real fix.
Also committed `.devcontainer/devcontainer-lock.json`, auto-generated by the failed
build attempt, which pins the resolved `postgresql-client` feature to an exact digest
— kept intentionally, the same role as a package-lock file.

**d. The actual root cause: Docker Desktop's WSL Integration toggle**
Same error persisted after (c). Further research (a second, more specific GitHub
issue on the identical error string) identified the real cause: Docker Desktop's
**Settings → Resources → WSL Integration** toggle for the `Ubuntu` distro was off,
so Docker Desktop never started the guest-services helper inside that distro that
mount operations depend on — unrelated to anything in this repo's config. Fixed by
enabling that toggle and restarting Docker Desktop. No repo change was needed or made
for this one; it's a host-machine setting, noted here so future-me doesn't re-diagnose
it from scratch.

---

## 9. Milestone 1 and 2 verified working

With the container finally up, ran the verification checklist end to end inside the
container's integrated terminal:

```
$ echo ${#STEAM_API_KEY}
32
$ psql "$DATABASE_URL" -c "select 1;"
 ?column?
----------
        1
(1 row)
$ psql "$DATABASE_URL" -f index/schema.sql
CREATE EXTENSION
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
$ psql "$DATABASE_URL" -c "\dt"
 achievement_chunks, achievements, chunks, guides   -- all four present
$ psql "$DATABASE_URL" -c "\dx"
 vector 0.8.6 installed
```

Confirms, in order: `.env` → `env_file` wiring works: `network_mode: service:db`
correctly resolves `localhost` to the `db` container; `schema.sql` applies cleanly to
an empty database; pgvector 0.8.6 is active with ivfflat/HNSW methods available.

**Milestones 1 and 2, per the brief, are done.**

---

## 10. Security note

During troubleshooting, a `docker compose ... config` log pasted into chat printed
the resolved `STEAM_API_KEY` value in plaintext (Compose's `config` command resolves
and displays `environment:` values). Treated as exposed; the key was rotated at
steamcommunity.com/dev/apikey afterward. Noted here as a reminder: redact the
`environment:` block from any future `docker compose config` output before sharing
it anywhere, same as the `.env` file itself.

---

## Where this leaves things

Infrastructure is done and verified. Everything from here is application logic,
written by hand per the brief — milestone 3 onward (fetch schema + global
percentages, commit raw JSON to `ingest/cache/`, and so on through the rest of
`Project_Description.md`'s milestone list).
