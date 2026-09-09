# Steam Achievement RAG — Project Brief

A retrieval-augmented generation system that answers "how do I get this achievement?"
for **Halo: The Master Chief Collection** (Steam appid `976730`, 700 achievements).

---

## How to work with me on this

**I am building this myself. Do not write implementation code for me.**

I want to learn RAG properly, so the help I want is:

- Explaining concepts and tradeoffs
- Reviewing code I've written and pointing out what's wrong or naive
- Research: API behavior, library choices, current best practice
- Config/scaffolding snippets (devcontainer, docker-compose, DDL) are fine —
  application logic is not

If I ask a question that could be answered either by explaining or by writing
the code, explain. If I'm stuck, give me the concept and a pointer, not the solution.

---

## Why this project

RAG is fuzzy lookup over unstructured prose. It is *not* analytics — anything
countable, sortable, or filterable belongs in SQL.

Achievement help is a genuinely good fit: the answer lives in a specific paragraph
someone wrote, phrased a dozen different ways, with no database column that captures it.

The catch: **Steam does not contain the how-to content.** The achievement schema gives
names, terse one-line descriptions, and icons. Hidden achievements have no description
at all. The actual corpus is **Steam Community Guides** — user-written walkthroughs,
retrievable through the API as published files.

## Why MCC specifically

- 700 achievements — large enough for retrieval quality to actually matter
- Rich guide ecosystem, including several complete achievement walkthroughs
- Steam's own descriptions are prefixed by sub-game (`Halo: Reach: Complete Winter
  Contingency`, `Halo CE: Complete Halo`), while others are collection-wide
  (`Kill 100 Grunts`) — a machine-extractable facet for free
- One appid containing six games, which makes the structured-vs-semantic problem concrete

Achievement names are unique across sub-games, so achievement *identity* is unambiguous.
`sub_game` is a **useful filter facet, not a correctness guardrail** — it matters for
ambiguous queries ("how do I find all the skulls?") that describe six games' worth of
near-identical guide prose.

---

## Architecture

### Data model

```sql
achievements
  api_name      TEXT PRIMARY KEY   -- stable Steam identifier
  display_name  TEXT NOT NULL
  description   TEXT               -- empty for hidden achievements
  is_hidden     BOOLEAN NOT NULL
  sub_game      TEXT               -- parsed from description prefix
  global_pct    REAL

guides
  published_file_id  TEXT PRIMARY KEY
  title, author, time_updated, votes_up

chunks
  id, guide_id, section_title, ordinal, text
  sub_game
  embedding  vector(384)
  tsv        tsvector          -- for BM25 / keyword search

achievement_chunks
  achievement_id, chunk_id, confidence, method
```

`achievement_chunks` is the heart of the system. Bootstrap it by exact-matching the
700 display names against chunk text — guides usually quote achievement names verbatim
as section headers, so this yields high-precision links cheaply. **Those links double
as eval ground truth.**

### Chunking

Guides are already structured into sections via `GetSubSectionData`, often one section
per achievement. Chunk on those real boundaries rather than slicing at a fixed token
count. Structure-aware chunking vs fixed-size is one of the largest quality levers in
RAG, and this dataset provides the structure for free.

### Query path

1. **Resolve, don't retrieve.** Match the user's phrasing against 700 known achievement
   names — exact first, then fuzzy/trigram. This is a lookup, not vector search.
2. **Resolved** → pull linked chunks directly from `achievement_chunks`.
3. **Unresolved** ("the one where you kill the Elite with a plasma sword") → embed the
   query, filter on `sub_game` where inferable, hybrid search (dense + BM25).
4. Rerank.
5. Generate, citing the source guide.

Step 1 is the router. Measuring how many queries short-circuit there is itself a finding.

### Repo layout

```
steam-achievement-rag/
├── .devcontainer/
│   ├── devcontainer.json
│   └── docker-compose.yml
├── ingest/
│   ├── achievements.py    # GetSchemaForGame + global %
│   ├── guides.py          # QueryFiles → GetDetails → GetSubSectionData
│   └── cache/             # raw JSON, committed to git
├── transform/
│   ├── parse_subgame.py
│   ├── chunk.py
│   └── link.py
├── index/
│   ├── embed.py
│   └── schema.sql
├── retrieve/
│   ├── resolve.py
│   ├── search.py
│   └── generate.py
├── eval/
│   ├── goldset.py
│   └── metrics.py
└── api/
```

---

## Environment

GitHub Codespaces, Postgres + pgvector via docker-compose.

**Constraints:**
- 120 core-hours/month free (2-core minimum machine ≈ 60 real hours); 15 GB storage
- Storage accrues while a codespace *exists*, not just while it runs — delete unused ones
- Default 30-day retention: an inactive codespace is deleted, taking its volumes with it
- Default 30-min idle timeout; stop the codespace rather than closing the tab

**Consequence — treat the codespace as disposable.** Raw API responses are committed to
the repo. The database must be fully rebuildable from them via the loader script. The
only copy of anything must never live in a container.

Scale is small: one schema call, ~50 guide fetches, a few thousand chunks. Rate limits
and CPU are non-issues. MiniLM (`all-MiniLM-L6-v2`, 384 dims) runs fine on 2 cores.
`sentence-transformers` pulls PyTorch (~2 GB), so it is added only when embedding
actually begins.

Steam API key lives in Codespaces Secrets as `STEAM_API_KEY`, injected at container start.

### Endpoints

```
ISteamUserStats/GetSchemaForGame/v2/?key={KEY}&appid=976730
ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/?gameid=976730   (no key)
IPublishedFileService/QueryFiles/v1/     (filter by appid + guide filetype)
IPublishedFileService/GetDetails/v1/
IPublishedFileService/GetSubSectionData/v1/   (guide TOC + sections)
```

Achievements are at `game.availableGameStats.achievements`, each with `name`,
`displayName`, `description`, `hidden`.

---

## Milestones

Ingestion scripts only capture — they write raw JSON and do no parsing. That separation
means the parser can be rewritten without re-hitting the API.

- [ ] 1. Devcontainer up; `CREATE EXTENSION vector;` succeeds
- [ ] 2. `STEAM_API_KEY` in Codespaces Secrets, readable after rebuild
- [ ] 3. Fetch schema + global percentages, commit raw JSON
- [ ] 4. **Inspect the JSON by hand** (see below)
- [ ] 5. Parse `sub_game`, load `achievements` idempotently (`ON CONFLICT DO UPDATE`)
- [ ] 6. Ingest ~20 top MCC guides; inspect section structure before writing a chunker
- [ ] 7. Build `achievement_chunks` by exact name matching; measure coverage of 700
- [ ] 8. Gold set: 100 naturally-phrased questions keyed to correct `api_name`
- [ ] 9. **Resolver only, no embeddings.** Score it. This is the baseline.
- [ ] 10. Add dense + BM25 for the unresolved tail. Score again.
- [ ] 11. Generation last.

If step 9 already scores well, that's a real finding — it tells me how much of this
problem is actually retrieval.

### Step 4 questions to answer by hand

- Do I get exactly 700?
- How many have `hidden: 1`, and what's in `description` for those?
- What fraction of descriptions carry a sub-game prefix?
- Is the prefix format consistent enough to split on, or is a lookup table needed?
- Does the percentages response cover all 700?

Whatever the hidden achievements look like shapes the whole project — that gap is
exactly what the guides have to fill.

---

## Key principles

1. **Build the eval set before the retriever.** Skipping this is why most RAG projects plateau.
2. **Baseline without embeddings first.** Know what the simple thing scores before adding complexity.
3. **Ingest, transform, and index are separate re-runnable stages.** Never re-embed because ingestion changed.
4. **Inspect data by hand before writing a parser for it.**
5. **Filter on structure, embed on meaning.** Confusing the two is the central RAG failure mode.