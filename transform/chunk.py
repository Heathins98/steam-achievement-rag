"""
Loads guide metadata into the guides table, and guide section text into
the chunks table - cleaning Steam's BBCode-style guide markup out of the
text first.

Two things happen here, matching the two things milestone 6 needs:
  1. Read guides_details_976730.json and upsert one row per guide into
     the guides table. This has to happen first - chunks.guide_id is a
     foreign key into guides, so a guide row must exist before any of
     its chunks can be inserted.
  2. Read every cached guide_sections_<id>.json file and insert one row
     per section into the chunks table, with the section's text cleaned
     of BBCode markup first.

Field names below (for both guides.py's cached responses) were
confirmed by hand against real output, not guessed - see the
conversation history / commit message for how each one was checked.

Note: chunks.sub_game is left NULL here, and stays that way - it's not
populated anywhere in the current pipeline. Unlike achievements, a
single guide section doesn't come with anything telling us which
sub-game it belongs to. transform/link.py links chunks to achievements
(which do have a sub_game), so inheriting a value through that link is
possible in principle, but nothing does it today - a chunk's sub_game
column is unused, not silently wrong.

Some guide sections bundle several achievements together under one
heading instead of one section per achievement - confirmed by hand
against real output (see split_compilation_section() below): a section
with 3+ lines like "-Achievement Name:" gets split into one sub-chunk
per achievement instead of staying one oversized chunk. This mattered
in practice, not just in theory - a bundled chunk like that was diluting
both dense and keyword search enough that the right answer wasn't
showing up in the top results at all, not just showing up alongside
noise.

Run with:
    python transform/chunk.py
"""

import os
import re
import glob
import json
import psycopg

HERE = os.path.dirname(__file__)
CACHE_DIR = os.path.join(HERE, "..", "ingest", "cache")
DETAILS_FILE = os.path.join(CACHE_DIR, "guides_details_976730.json")


def clean_guide_text(raw_text):
    """
    Strips Steam's BBCode-style guide markup out of a section's text,
    keeping anything actually useful:
      - [previewimg=...][/previewimg] and [previewicon=...][/previewicon]
        blocks are dropped completely, tag and contents - these only
        reference an internal Steam image id, there's no usable link
        in them worth keeping.
      - [url=LINK]label[/url] tags are replaced with just LINK, so a
        real link (like a walkthrough video) survives as plain text.
      - Bare URLs already sitting in the text with no tag around them
        (like a plain youtube.com link) are left completely alone.
      - Every other bbcode tag ([b], [/b], [h1], [/h1], etc.) is
        stripped, but the text between the tags is kept - that's real
        prose content, not markup.
      - Leftover multi-blank-line gaps (usually where an image used to
        be) get collapsed down to a single blank line.
    """
    text = raw_text

    # drop image/icon blocks entirely - no usable link inside these,
    # just an internal Steam image id
    text = re.sub(r"\[previewimg=.*?\]\[/previewimg\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[previewicon=.*?\]\[/previewicon\]", "", text, flags=re.DOTALL)

    # [url=https://example.com]click here[/url] -> just the link itself
    text = re.sub(r"\[url=([^\]]+)\].*?\[/url\]", r"\1", text, flags=re.DOTALL)

    # bbcode list items are [*], not a normal named tag (the asterisk
    # doesn't match the generic tag stripper below), so they need their
    # own rule - turn each one into a plain text bullet on its own line
    # instead of leaving the literal "[*]" sitting in the text
    text = re.sub(r"\[\*\]", "\n- ", text)

    # every remaining bbcode tag, opening or closing, with or without an
    # "=value" attribute - replace with a space rather than nothing, so
    # two tags sitting right next to each other (no space between them
    # in the original text) don't glue the words on either side together
    text = re.sub(r"\[/?[a-zA-Z0-9]+(=[^\]]*)?\]", " ", text)

    # clean up the extra spacing that leaves behind, without eating the
    # newlines that separate paragraphs
    text = re.sub(r"[ \t]{2,}", " ", text)     # collapse repeated spaces
    text = re.sub(r"[ \t]+\n", "\n", text)     # trailing space before a line break
    text = re.sub(r"\n[ \t]+", "\n", text)     # leading space after a line break
    text = re.sub(r"\n{3,}", "\n\n", text)     # collapse 3+ line breaks to one blank line

    return text.strip()


# a line that starts with "-", has at least one non-space character,
# then a colon ending the line - the header format confirmed by hand
# across six different achievements in the one guide that uses this
# style ("-Destination Vacation:", "-Airborne:", etc.)
COMPILATION_HEADER_PATTERN = re.compile(r"^-(\S.*):\s*$", re.MULTILINE)

# fewer than this many headers in a section and it's treated as normal
# prose that just happens to contain a dash somewhere, not a bundled
# list of achievements worth splitting apart
MIN_HEADERS_TO_SPLIT = 3


def split_compilation_section(text):
    """
    Some sections bundle several achievements under one heading instead
    of one section per achievement. Returns a list of (sub_title, text)
    pairs - one pair per achievement if the section matches that bundled
    pattern, or a single (None, text) pair unchanged if it doesn't.
    """
    headers = list(COMPILATION_HEADER_PATTERN.finditer(text))
    if len(headers) < MIN_HEADERS_TO_SPLIT:
        return [(None, text)]

    pieces = []
    for i, header in enumerate(headers):
        start = header.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        sub_title = header.group(1).strip()
        pieces.append((sub_title, text[start:end].strip()))
    return pieces


def load_guides(database_url):
    """
    Reads the raw GetDetails response and upserts one row per ENGLISH
    guide into the guides table. Returns the list of guide ids loaded,
    so load_chunks() knows which cached section files to look for.

    None of the QueryFiles calls in ingest/guides.py filter by language -
    that parameter doesn't exist on the endpoint - so guides in other
    languages show up unasked-for, more of them than expected (13 of 74
    guides, several different languages, not just one). They're mostly
    harmless for retrieval (they rank last on English questions,
    confirmed by hand), but there's no reason to keep paying to embed
    and store guide content nobody asked for. GetDetails' own "language"
    field is Steam's ELanguage enum - 0 is English.
    """
    with open(DETAILS_FILE) as f:
        details_data = json.load(f)

    guide_list = details_data["response"]["publishedfiledetails"]
    ENGLISH = 0

    english_guide_ids = []
    skipped_count = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for guide in guide_list:
                guide_id = guide["publishedfileid"]

                if guide.get("language") != ENGLISH:
                    # clean up anything already loaded for this guide
                    # from before this filter existed - cascades down
                    # through chunks and achievement_chunks automatically
                    cur.execute("delete from guides where published_file_id = %s", (guide_id,))
                    skipped_count += 1
                    continue

                vote_data = guide.get("vote_data", {})
                cur.execute(
                    """
                    INSERT INTO guides
                        (published_file_id, title, author, time_updated, votes_up)
                    VALUES
                        (%(published_file_id)s, %(title)s, %(author)s, to_timestamp(%(time_updated)s), %(votes_up)s)
                    ON CONFLICT (published_file_id) DO UPDATE SET
                        title        = EXCLUDED.title,
                        author       = EXCLUDED.author,
                        time_updated = EXCLUDED.time_updated,
                        votes_up     = EXCLUDED.votes_up
                    """,
                    {
                        "published_file_id": guide_id,
                        "title": guide.get("title"),
                        # a raw SteamID64, not a display name - see the
                        # module docstring
                        "author": guide.get("creator"),
                        "time_updated": guide.get("time_updated"),
                        "votes_up": vote_data.get("votes_up"),
                    },
                )
                english_guide_ids.append(guide_id)
        conn.commit()

    print(f"loaded {len(english_guide_ids)} rows into guides ({skipped_count} non-English skipped)")
    return english_guide_ids


def load_chunks(database_url, guide_ids):
    """
    Reads every cached guide_sections_<id>.json file and loads one row
    per section into the chunks table, text cleaned first.

    Deletes any existing chunks for a guide before inserting its fresh
    ones, so running this script again (e.g. after re-fetching guides)
    replaces old rows instead of piling up duplicates - chunks.id is an
    auto-generated serial with no natural key of its own to upsert on,
    unlike achievements or guides, so delete-then-insert is how this
    stays re-runnable.
    """
    total_sections = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for guide_id in guide_ids:
                section_file = os.path.join(CACHE_DIR, f"guide_sections_{guide_id}.json")
                if not os.path.exists(section_file):
                    print(f"  skipping {guide_id} - no cached section file found")
                    continue

                with open(section_file) as f:
                    section_data = json.load(f)

                sections = section_data["response"]["sub_sections"]

                cur.execute("DELETE FROM chunks WHERE guide_id = %s", (guide_id,))

                for section in sections:
                    # section titles can carry the same BBCode markup as
                    # the body text (e.g. an image tag tacked onto the
                    # end of a title) - clean both the same way
                    cleaned_title = clean_guide_text(section.get("title", ""))
                    cleaned_text = clean_guide_text(section.get("description_text", ""))
                    ordinal = section.get("sort_order")

                    # normally this is a single (None, cleaned_text) pair
                    # and nothing changes - it only actually splits when
                    # the section bundles several achievements together
                    for sub_title, sub_text in split_compilation_section(cleaned_text):
                        if sub_title is None:
                            section_title = cleaned_title
                        else:
                            section_title = f"{cleaned_title}: {sub_title}" if cleaned_title else sub_title

                        cur.execute(
                            """
                            INSERT INTO chunks
                                (guide_id, section_title, ordinal, text)
                            VALUES
                                (%(guide_id)s, %(section_title)s, %(ordinal)s, %(text)s)
                            """,
                            {
                                "guide_id": guide_id,
                                "section_title": section_title,
                                "ordinal": ordinal,
                                "text": sub_text,
                            },
                        )
                        total_sections += 1
        conn.commit()

    print(f"loaded {total_sections} rows into chunks")


def main():
    database_url = os.environ["DATABASE_URL"]

    guide_ids = load_guides(database_url)
    load_chunks(database_url, guide_ids)


if __name__ == "__main__":
    main()
