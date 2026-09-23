"""
Links achievements to the guide chunks that explain them. A match gets
written to achievement_chunks, tagged with how it was found.

Two passes, in order:
  1. exact_display_name - does the achievement's display name show up as
     plain text inside a chunk? This is the original bootstrap - guides
     tend to quote achievement names close to verbatim, so a simple
     case-insensitive substring check gets high-precision links without
     needing embeddings or anything fancy first.
  2. exact_description  - for achievements pass 1 found NOTHING for,
     does the achievement's own description (with the sub-game prefix
     stripped) show up instead? Confirmed by hand: many achievements
     have joke/flavor-text display names ("Bip! Bap! BAM!") that a
     guide author never writes verbatim, even while describing exactly
     how to get it in plain language close to Steam's own description
     ("earn a Triple Kill medal with the pistol"). Checked all 52
     achievements pass 1 missed after two rounds of guide ingestion -
     every single one had its description text sitting in the corpus
     already. This isn't a guess, it's the confirmed fix for that gap.

These same links double as eval ground truth later.

Only matches against chunks.text (the section body), not
chunks.section_title - a look at real data showed section titles here
are mission-based ("Mission 08 // Cortana"), not achievement-named, so
an achievement name shows up in the body text, not as a heading.

Known limitation, worth remembering rather than pre-emptively "fixing":
a short or generic display name could in theory match text that isn't
really about that achievement (pass 1 already excludes a couple of
confirmed offenders - see TOO_GENERIC_TO_MATCH_ALONE-equivalent handling
below). Pass 2's full-sentence descriptions don't have this problem in
practice - a whole sentence coincidentally appearing elsewhere is not
realistic - so it doesn't need the same guard.

Run with:
    python transform/link.py
"""

import os
import re
import psycopg

# same generic-name exclusions confirmed during earlier hand-inspection
# (see git history) - real achievement names that are also common words
# showing up constantly in unrelated guide text
TOO_GENERIC_TO_MATCH_ALONE = {"Halo", "Flood"}


def fetch_achievements(cur):
    """Returns a list of (api_name, display_name, description) for all 700 achievements."""
    cur.execute("select api_name, display_name, description from achievements")
    return cur.fetchall()


def fetch_chunks(cur):
    """Returns a list of (id, text) for every chunk."""
    cur.execute("select id, text from chunks")
    return cur.fetchall()


def extract_description_core(description):
    """
    Strips the sub-game prefix (e.g. "Halo CE: ") off a description,
    leaving just the actual requirement text. Achievements without a
    prefix (collection-wide ones) come back unchanged, since split()
    with no match just returns the original string.
    """
    if not description:
        return None
    return description.split(": ", 1)[-1].rstrip(".")


def find_matches_by_display_name(achievements, chunks):
    """
    Checks every achievement's display name against every chunk for a
    case-insensitive, whole-word match. Returns {api_name: [chunk_id, ...]}
    for achievements with at least one match.

    A plain substring check ("Hero" in "Heroic difficulty") matches
    right through the middle of unrelated words - found this the hard
    way on real data: "Hero" was matching every "Heroic" difficulty
    mention, "Legend" every "Legendary", "Key" every "Keyes" (a level
    name), "War" every "Warzone". \b word boundaries fix that - they
    require a real word edge on both sides of the name, not just any
    substring position.
    """
    matches = {}
    for api_name, display_name, description in achievements:
        if display_name in TOO_GENERIC_TO_MATCH_ALONE:
            continue
        pattern = re.compile(r"\b" + re.escape(display_name) + r"\b", re.IGNORECASE)
        found_chunk_ids = [chunk_id for chunk_id, text in chunks if pattern.search(text)]
        if found_chunk_ids:
            matches[api_name] = found_chunk_ids
    return matches


def find_matches_by_description(achievements, chunks, already_matched):
    """
    Fallback pass, only for achievements not already in already_matched:
    checks whether the achievement's own description (prefix stripped)
    appears as a substring in a chunk. Returns {api_name: [chunk_id, ...]}.

    Full sentences don't need the word-boundary treatment display names
    needed - a whole sentence landing inside unrelated text by
    coincidence isn't a realistic risk the way a single generic word was.
    """
    matches = {}
    for api_name, display_name, description in achievements:
        if api_name in already_matched:
            continue
        core = extract_description_core(description)
        if not core:
            continue
        needle = core.lower()
        found_chunk_ids = [chunk_id for chunk_id, text in chunks if needle in text.lower()]
        if found_chunk_ids:
            matches[api_name] = found_chunk_ids
    return matches


def save_matches(cur, matches_by_method):
    """
    Replaces the entire achievement_chunks table with the matches just
    found. A full delete-then-insert, same idea as chunks got in
    chunk.py - there's no natural key here to upsert against that still
    makes sense if the matching logic itself changes between runs, so
    this just starts clean every time instead.

    matches_by_method is {method_name: {api_name: [chunk_id, ...]}}.
    """
    cur.execute("delete from achievement_chunks")
    for method, matches in matches_by_method.items():
        for api_name, chunk_ids in matches.items():
            for chunk_id in chunk_ids:
                cur.execute(
                    """
                    insert into achievement_chunks (achievement_id, chunk_id, confidence, method)
                    values (%s, %s, %s, %s)
                    """,
                    (api_name, chunk_id, 1.0, method),
                )


def main():
    database_url = os.environ["DATABASE_URL"]

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            achievements = fetch_achievements(cur)
            chunks = fetch_chunks(cur)

            print(f"checking {len(achievements)} achievements against {len(chunks)} chunks...")

            display_name_matches = find_matches_by_display_name(achievements, chunks)
            print(f"  pass 1 (display name): {len(display_name_matches)} achievements matched")

            description_matches = find_matches_by_description(achievements, chunks, display_name_matches)
            print(f"  pass 2 (description, fallback only): {len(description_matches)} more achievements matched")

            save_matches(cur, {
                "exact_display_name": display_name_matches,
                "exact_description": description_matches,
            })
        conn.commit()

    total_matched = len(display_name_matches) + len(description_matches)
    total_links = sum(len(v) for v in display_name_matches.values()) + sum(len(v) for v in description_matches.values())
    print(f"found {total_links} links")
    print(f"  {total_matched} of {len(achievements)} achievements have at least one matching chunk")


if __name__ == "__main__":
    main()
