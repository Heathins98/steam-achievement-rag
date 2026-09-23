"""
The resolver - milestone 9, "resolve, don't retrieve." Given a question,
tries to match it against the 700 known achievement names first, two
ways, in order:
  1. exact  - does an achievement's display name show up as a whole
              word/phrase inside the question? Same word-boundary
              technique transform/link.py already uses.
  2. fuzzy  - if no exact match, is the question close enough to some
              achievement's display name (typos, slightly different
              wording of the name itself) using Python's built-in
              difflib?

If a question matches, its linked chunks (from achievement_chunks) get
printed as the answer - this module only resolves and surfaces raw
guide text, it doesn't write anything. retrieve/generate.py is the
piece that turns this into an actual written answer.

Be honest about what this can and can't catch: fuzzy matching here
compares the whole question against each display name, so it mostly
helps with near-misses of the name itself ("cheet death" instead of
"Cheat Death"), not questions that describe an achievement without
naming it ("where's the hidden binary code in Reach"). Catching those is
what milestone 10's embeddings are for - an unresolved question here
isn't a bug, it's the actual baseline gap the brief wants measured.

Two ways to use this file:
  - Run it directly for an interactive prompt: type a question, see
    what it resolves to.
  - Import resolve_question() - retrieve/answer.py does exactly this,
    falling through to retrieve/search.py's hybrid search when nothing
    resolves, instead of just giving up.

Run with:
    python retrieve/resolve.py
"""

import os
import re
import difflib
import psycopg

FUZZY_MATCH_CUTOFF = 0.75

# Achievement names too generic to trust as a resolver match on their
# own, found by hand during milestone 7 (transform/link.py): these are
# real achievement names that are ALSO common words that show up
# constantly in unrelated guide text and questions - "Halo" (a real
# achievement, but also just the franchise's own name) and "Flood" (a
# real achievement, but also a faction name mentioned everywhere) being
# the two confirmed cases so far. A question merely containing one of
# these words isn't good evidence someone is asking about that specific
# achievement. This is a short, evidence-based list, not a general rule
# like "skip short names" - that would also wrongly exclude perfectly
# fine single-word achievements like "Headhunter" or "Warrior".
TOO_GENERIC_TO_MATCH_ALONE = {"Halo", "Flood"}


def fetch_achievements(cur):
    """Returns a list of (api_name, display_name) for all 700 achievements."""
    cur.execute("select api_name, display_name from achievements")
    return cur.fetchall()


def exact_match(question, achievements):
    """
    Checks whether any achievement's display name appears as a whole
    word/phrase inside the question, case-insensitive. Returns
    (api_name, display_name) or None.

    If more than one achievement matches, the longest (most specific)
    display name wins - a short generic word matching alongside a more
    specific one shouldn't be allowed to win just because it happened to
    be checked first.
    """
    candidates = []
    for api_name, display_name in achievements:
        if display_name in TOO_GENERIC_TO_MATCH_ALONE:
            continue
        pattern = re.compile(r"\b" + re.escape(display_name) + r"\b", re.IGNORECASE)
        if pattern.search(question):
            candidates.append((api_name, display_name))

    if not candidates:
        return None

    # longest display_name = most specific match
    return max(candidates, key=lambda pair: len(pair[1]))


def fuzzy_match(question, achievements):
    """
    Falls back to a similarity check between the whole question and
    each display name, for when the question is a near-miss of the
    achievement name itself rather than an exact substring. Returns
    (api_name, display_name) or None if nothing clears the cutoff.
    """
    display_names = [display_name for _, display_name in achievements]
    close = difflib.get_close_matches(question, display_names, n=1, cutoff=FUZZY_MATCH_CUTOFF)
    if not close:
        return None

    matched_name = close[0]
    for api_name, display_name in achievements:
        if display_name == matched_name:
            return (api_name, display_name)
    return None


def resolve_question(question, cur):
    """
    Tries to resolve a question to a single achievement. Returns
    (api_name, display_name, method) where method is "exact", "fuzzy",
    or None if nothing matched at all.
    """
    achievements = fetch_achievements(cur)

    found = exact_match(question, achievements)
    if found:
        api_name, display_name = found
        return (api_name, display_name, "exact")

    found = fuzzy_match(question, achievements)
    if found:
        api_name, display_name = found
        return (api_name, display_name, "fuzzy")

    return (None, None, None)


def fetch_linked_chunks(cur, api_name):
    """Returns the guide text chunks already linked to this achievement."""
    cur.execute(
        """
        select g.title, c.section_title, c.text
        from achievement_chunks ac
        join chunks c on c.id = ac.chunk_id
        join guides g on g.published_file_id = c.guide_id
        where ac.achievement_id = %s
        """,
        (api_name,),
    )
    return cur.fetchall()


EXCERPT_WINDOW = 250


def excerpt_near(text, display_name):
    """
    Returns a snippet of text centered on wherever the achievement's
    display name actually shows up, instead of always just the start of
    the chunk. Needed because some guides pack many achievements into
    one section (a compilation-style guide, not one section per
    achievement) - for those, the first few hundred characters can
    easily belong to a completely different achievement than the one
    that was actually asked about, even though the chunk as a whole is
    a correct link.
    """
    match = re.search(re.escape(display_name), text, re.IGNORECASE)
    if not match:
        # display name isn't literally in this chunk's text (the link
        # might be through the achievement's description instead) -
        # fall back to just the start of the chunk
        start = 0
    else:
        start = max(0, match.start() - EXCERPT_WINDOW)

    end = start + (EXCERPT_WINDOW * 2)
    snippet = text[start:end].strip()

    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


def main():
    database_url = os.environ["DATABASE_URL"]

    print("Ask a question about a Halo MCC achievement (or type 'quit'):")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            while True:
                question = input("\n> ").strip()
                if not question or question.lower() in ("quit", "exit"):
                    break

                api_name, display_name, method = resolve_question(question, cur)

                if api_name is None:
                    print("  unresolved - no matching achievement found "
                          "(this is exactly the gap milestone 10 fills)")
                    continue

                print(f"  resolved via {method} match -> {display_name} ({api_name})")

                chunks = fetch_linked_chunks(cur, api_name)
                if not chunks:
                    print("  (no guide chunks are linked to this achievement yet)")
                    continue

                for guide_title, section_title, text in chunks:
                    print(f"\n  --- from \"{guide_title}\", section \"{section_title}\" ---")
                    print(f"  {excerpt_near(text, display_name)}")


if __name__ == "__main__":
    main()
