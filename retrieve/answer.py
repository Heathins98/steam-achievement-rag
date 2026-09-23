"""
The actual milestone 10 pipeline: try the resolver first, and only fall
through to hybrid search if the resolver comes back empty. This is what
"resolve, don't retrieve" means in practice - search is the fallback
path, not the default one.

This file itself doesn't generate anything - it still just returns
whichever chunks it found, not a written-out answer. retrieve/generate.py
is the layer on top of this that actually writes an answer from them.

Run with:
    python retrieve/answer.py
for an interactive prompt, same idea as resolve.py and search.py.
"""

import os
import psycopg
from sentence_transformers import SentenceTransformer

from resolve import resolve_question
from search import hybrid_search, MODEL_NAME


def find_chunks(question, model, cur):
    """
    Tries the resolver first. If it finds a matching achievement,
    returns its linked chunks. If not, falls through to hybrid search
    over every chunk instead.

    Returns (method, display_name, chunks) - method is "resolved" or
    "searched", display_name is the matched achievement's name (only
    set for the resolved path), and chunks is always a list of
    (chunk_id, guide_title, section_title, text) tuples regardless of
    which path found them, so callers don't need to care which one ran.
    """
    api_name, display_name, resolve_method = resolve_question(question, cur)

    if api_name is not None:
        cur.execute(
            """
            select c.id, g.title, c.section_title, c.text
            from achievement_chunks ac
            join chunks c on c.id = ac.chunk_id
            join guides g on g.published_file_id = c.guide_id
            where ac.achievement_id = %s
            """,
            (api_name,),
        )
        return ("resolved", display_name, cur.fetchall())

    rows = hybrid_search(question, model, cur)
    chunks = [(chunk_id, guide_title, section_title, text)
              for chunk_id, guide_title, section_title, text, _, _, _ in rows]
    return ("searched", None, chunks)


def main():
    database_url = os.environ["DATABASE_URL"]

    print(f"loading {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    print("Ask a question (or type 'quit'):")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            while True:
                question = input("\n> ").strip()
                if not question or question.lower() in ("quit", "exit"):
                    break

                method, display_name, chunks = find_chunks(question, model, cur)

                if method == "resolved":
                    print(f"  resolved -> {display_name}")
                else:
                    print("  unresolved by name - falling back to hybrid search")

                if not chunks:
                    print("  no chunks found")
                    continue

                for chunk_id, guide_title, section_title, text in chunks:
                    print(f"\n  --- \"{guide_title}\", section \"{section_title}\" ---")
                    print(f"  {text[:300]}{'...' if len(text) > 300 else ''}")


if __name__ == "__main__":
    main()
