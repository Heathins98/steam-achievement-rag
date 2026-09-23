"""
Computes a sentence embedding for every chunk's text and stores it in
chunks.embedding, using all-MiniLM-L6-v2 (384 dimensions - matches the
vector(384) column already defined in index/schema.sql).

This is the first half of milestone 10: turning the guide text already
sitting in the database into something a similarity search can actually
compare against. retrieve/search.py (not written yet) is the code that
runs a query against these embeddings - this script just fills the
column in.

No extra pgvector client library here - the embedding gets converted to
pgvector's own text format ("[0.1,0.2,...]") and passed as a plain
string. Postgres parses that itself on the way in, since that's just
the vector type's normal text input format - one less dependency to
install and rebuild the container for.

Safe to re-run: it always recomputes and overwrites every chunk's
embedding from whatever text is currently in the table, so re-running
this after a re-chunk (transform/chunk.py) just picks up the latest text.

Run with:
    python index/embed.py
"""

import os
import psycopg
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


def fetch_chunks(cur):
    """Returns every chunk's (id, text) currently in the table."""
    cur.execute("select id, text from chunks")
    return cur.fetchall()


def to_pgvector_literal(embedding):
    """
    Turns a list/array of numbers into the text format pgvector expects
    for a vector column: "[0.123,0.456,...]".
    """
    return "[" + ",".join(str(x) for x in embedding) + "]"


def save_embedding(cur, chunk_id, embedding):
    """Writes one chunk's embedding back to its row."""
    cur.execute(
        "update chunks set embedding = %s where id = %s",
        (to_pgvector_literal(embedding), chunk_id),
    )


def populate_tsv(cur):
    """
    Fills in the tsv column used for keyword (BM25-family) search - the
    other half of milestone 10's hybrid search, alongside the dense
    embeddings above. One statement covers every row, so there's no
    need to loop chunk by chunk the way the embeddings do.
    """
    cur.execute("update chunks set tsv = to_tsvector('english', text)")


def main():
    database_url = os.environ["DATABASE_URL"]

    print(f"loading {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            chunks = fetch_chunks(cur)
            print(f"embedding {len(chunks)} chunks...")

            chunk_ids = [chunk_id for chunk_id, text in chunks]
            texts = [text for chunk_id, text in chunks]

            # encode() batches internally - much faster than calling it
            # once per chunk in a loop
            embeddings = model.encode(texts, show_progress_bar=True)

            for chunk_id, embedding in zip(chunk_ids, embeddings):
                save_embedding(cur, chunk_id, embedding)

            print("populating tsv for keyword search...")
            populate_tsv(cur)

        conn.commit()

    print(f"saved embeddings and tsv for {len(chunks)} chunks")


if __name__ == "__main__":
    main()
