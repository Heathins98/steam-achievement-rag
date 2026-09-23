"""
Hybrid search over chunks - milestone 10's second half, for whatever
the resolver (retrieve/resolve.py) can't find by name alone. Combines
two different signals:
  - dense - cosine similarity between the question's embedding and each
            chunk's embedding (pgvector's <=> operator). Catches
            questions that mean the same thing as a chunk without
            sharing many of the same words.
  - BM25  - Postgres's tsvector/tsquery keyword ranking (ts_rank).
            Catches exact terms embeddings can blur past - a specific
            level name, an item name, a number.

These two scores are NOT just added together. A cosine similarity is
always between 0 and 1; a ts_rank score has no such bound and depends on
term frequency in a completely different way - blending the raw numbers
would let whichever one happens to have bigger numbers quietly dominate
every search, regardless of which one is actually more relevant. Instead
this uses Reciprocal Rank Fusion (RRF): rank the chunks separately by
each method, then combine using 1/(k + rank) from each ranking. Because
it only looks at rank position, not raw score magnitude, it doesn't care
that the two scores live on different scales.

Run with:
    python retrieve/search.py
for an interactive prompt, same idea as retrieve/resolve.py.
"""

import os
import psycopg
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5

# 60 is the commonly used default for Reciprocal Rank Fusion, but it
# gives a good BM25 rank (e.g. 2nd) roughly the same weight as a
# mediocre dense rank (e.g. 19th) dragging alongside it - checked by
# hand on a real miss (a "data pad" question) where several other
# missions' near-identical walkthrough chunks out-scored the actually
# correct one this way, because dense embeddings weren't distinguishing
# which mission well for that kind of repetitive, formulaic content.
# A smaller k makes rank differences matter more, so a strong single
# signal isn't as easily dragged down by a weak one. This value needs
# validating against eval/metrics.py's full gold set, not just the one
# question it was diagnosed from - a k that fixes one miss could
# plausibly introduce others.
RRF_K = 10


def to_pgvector_literal(embedding):
    """Same format index/embed.py uses to write vectors - pgvector's own text format."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


def hybrid_search(question, model, cur, top_k=TOP_K):
    """
    Embeds the question, then runs one query that ranks every chunk two
    separate ways - by dense cosine similarity, and by BM25-style
    keyword ranking - and combines the two rankings with Reciprocal
    Rank Fusion. Returns the top_k chunks by combined score.
    """
    query_vector = to_pgvector_literal(model.encode(question))

    cur.execute(
        """
        with dense_ranked as (
            select id, row_number() over (order by embedding <=> %(query_vector)s) as rank
            from chunks
        ),
        bm25_ranked as (
            select id, row_number() over (
                order by ts_rank(tsv, plainto_tsquery('english', %(question)s)) desc
            ) as rank
            from chunks
        )
        select
            c.id,
            g.title,
            c.section_title,
            c.text,
            dense_ranked.rank as dense_rank,
            bm25_ranked.rank as bm25_rank,
            (1.0 / (%(rrf_k)s + dense_ranked.rank)) + (1.0 / (%(rrf_k)s + bm25_ranked.rank)) as combined_score
        from chunks c
        join dense_ranked on dense_ranked.id = c.id
        join bm25_ranked on bm25_ranked.id = c.id
        join guides g on g.published_file_id = c.guide_id
        order by combined_score desc
        limit %(top_k)s
        """,
        {
            "query_vector": query_vector,
            "question": question,
            "rrf_k": RRF_K,
            "top_k": top_k,
        },
    )
    return cur.fetchall()


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

                results = hybrid_search(question, model, cur)
                if not results:
                    print("  no results")
                    continue

                for chunk_id, guide_title, section_title, text, dense_rank, bm25_rank, combined_score in results:
                    print(f"\n  --- \"{guide_title}\", section \"{section_title}\" "
                          f"(dense_rank={dense_rank}, bm25_rank={bm25_rank}) ---")
                    print(f"  {text[:300]}{'...' if len(text) > 300 else ''}")


if __name__ == "__main__":
    main()
