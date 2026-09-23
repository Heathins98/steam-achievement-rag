"""
Scores two things against the gold set (eval/goldset.py):

  1. The resolver alone (retrieve/resolve.py) - milestone 9's baseline:
     "resolver only, no embeddings. Score it."
  2. The combined pipeline (retrieve/answer.py) - milestone 10's
     "add dense + BM25 for the unresolved tail. Score again." This is
     resolve first, falling through to hybrid search only when the
     resolver can't find a name match.

Printing both in one run is the point - the interesting number isn't
either score alone, it's the difference between them, since that
difference is literally what hybrid search bought you.

The two scores use different correctness checks, because they're
answering slightly different questions:
  - resolver alone: did it name the exact right achievement (api_name)?
  - combined pipeline: did any chunk it returned actually belong to the
    right achievement (checked via achievement_chunks)? This one has to
    be chunk-based instead of name-based, since a successful hybrid
    search doesn't return an achievement name at all - just chunks.

Both are still broken down by "phrasing" tier (exact_name / rephrased /
vague) for the same reason as before: a single blended percentage
doesn't say much on its own.

Run with:
    python eval/metrics.py
"""

import os
import sys
import psycopg
from sentence_transformers import SentenceTransformer

# retrieve/ and eval/ have no __init__.py - they're just plain scripts,
# same as everything else in this project - so make both directories
# importable regardless of where this gets run from
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "retrieve"))
sys.path.insert(0, os.path.dirname(__file__))

from resolve import resolve_question
from answer import find_chunks, MODEL_NAME
from goldset import GOLD_SET


def score_gold_set(cur):
    """
    Runs every question in GOLD_SET through the resolver. Returns a list
    of result dicts, one per question, recording what the resolver
    actually returned and whether that matched the expected answer.
    """
    results = []
    for entry in GOLD_SET:
        api_name, display_name, method = resolve_question(entry["question"], cur)
        results.append({
            "question": entry["question"],
            "expected": entry["answer_api_name"],
            "got": api_name,
            "phrasing": entry["phrasing"],
            "method": method,
            "correct": api_name == entry["answer_api_name"],
        })
    return results


def print_report(results):
    """Prints the overall score, a per-phrasing-tier breakdown, and every missed question."""
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    print(f"Overall: {correct}/{total} correct ({correct / total:.1%})")

    print("\nBy phrasing tier:")
    for tier in ("exact_name", "rephrased", "vague"):
        tier_results = [r for r in results if r["phrasing"] == tier]
        if not tier_results:
            continue
        tier_correct = sum(1 for r in tier_results if r["correct"])
        tier_total = len(tier_results)
        print(f"  {tier:12s} {tier_correct}/{tier_total} ({tier_correct / tier_total:.1%})")

    missed = [r for r in results if not r["correct"]]
    if missed:
        print(f"\n{len(missed)} missed questions:")
        for r in missed:
            got = r["got"] if r["got"] else "(unresolved)"
            print(f"  [{r['phrasing']}] \"{r['question']}\"")
            print(f"      expected {r['expected']}, got {got}")


def get_expected_chunk_ids(cur, expected_api_name):
    """Returns the set of chunk ids actually linked to the expected achievement."""
    cur.execute("select chunk_id from achievement_chunks where achievement_id = %s", (expected_api_name,))
    return {row[0] for row in cur.fetchall()}


def score_combined_pipeline(model, cur):
    """
    Runs every question in GOLD_SET through retrieve/answer.py's
    find_chunks() (resolve, falling through to hybrid search). Each
    question gets one of three outcomes, not just correct/incorrect:
      "correct"      - a returned chunk is actually linked to the
                        expected achievement
      "wrong"        - the expected achievement DOES have linked chunks,
                        but none of them were among what got returned
      "no_coverage"  - the expected achievement has ZERO chunks linked
                        to it at all in this 20-guide corpus, so no
                        system could have answered this correctly no
                        matter how good the resolver or search is - this
                        is a gap in the guide data, not a retrieval
                        failure, and conflating the two would hide a
                        real, separate finding
    """
    results = []
    for entry in GOLD_SET:
        method, display_name, chunks = find_chunks(entry["question"], model, cur)
        returned_chunk_ids = {chunk_id for chunk_id, guide_title, section_title, text in chunks}
        expected_chunk_ids = get_expected_chunk_ids(cur, entry["answer_api_name"])

        if not expected_chunk_ids:
            outcome = "no_coverage"
        elif returned_chunk_ids & expected_chunk_ids:
            outcome = "correct"
        else:
            outcome = "wrong"

        results.append({
            "question": entry["question"],
            "expected": entry["answer_api_name"],
            "phrasing": entry["phrasing"],
            "method": method,
            "outcome": outcome,
        })
    return results


def print_combined_report(results):
    """Same shape as print_report(), but split three ways instead of two - see score_combined_pipeline()."""
    total = len(results)
    correct = sum(1 for r in results if r["outcome"] == "correct")
    wrong = sum(1 for r in results if r["outcome"] == "wrong")
    no_coverage = sum(1 for r in results if r["outcome"] == "no_coverage")

    print(f"Overall: {correct}/{total} correct ({correct / total:.1%})")
    print(f"  {wrong} wrong, {no_coverage} not answerable (expected achievement has no guide coverage at all)")

    answerable = total - no_coverage
    if answerable:
        print(f"Among questions that were actually answerable: {correct}/{answerable} ({correct / answerable:.1%})")

    print("\nBy phrasing tier (of the total, not just answerable):")
    for tier in ("exact_name", "rephrased", "vague"):
        tier_results = [r for r in results if r["phrasing"] == tier]
        if not tier_results:
            continue
        tier_correct = sum(1 for r in tier_results if r["outcome"] == "correct")
        tier_total = len(tier_results)
        print(f"  {tier:12s} {tier_correct}/{tier_total} ({tier_correct / tier_total:.1%})")

    print("\nHow questions were answered:")
    for method in ("resolved", "searched"):
        method_results = [r for r in results if r["method"] == method]
        if not method_results:
            continue
        method_correct = sum(1 for r in method_results if r["outcome"] == "correct")
        method_total = len(method_results)
        print(f"  {method:9s} {method_total} questions, {method_correct} correct ({method_correct / method_total:.1%})")

    wrong_results = [r for r in results if r["outcome"] == "wrong"]
    if wrong_results:
        print(f"\n{len(wrong_results)} wrong - resolver/search found something, just not the right thing:")
        for r in wrong_results:
            print(f"  [{r['phrasing']}, {r['method']}] \"{r['question']}\" (expected {r['expected']})")

    no_coverage_results = [r for r in results if r["outcome"] == "no_coverage"]
    if no_coverage_results:
        print(f"\n{len(no_coverage_results)} not answerable - expected achievement has zero linked chunks:")
        for r in no_coverage_results:
            print(f"  [{r['phrasing']}] \"{r['question']}\" (expected {r['expected']})")


def main():
    database_url = os.environ["DATABASE_URL"]

    print("=" * 60)
    print("RESOLVER ALONE (milestone 9 baseline)")
    print("=" * 60)
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            resolver_results = score_gold_set(cur)
    print_report(resolver_results)

    print()
    print("=" * 60)
    print("RESOLVE + HYBRID SEARCH FALLBACK (milestone 10)")
    print("=" * 60)
    print(f"loading {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            combined_results = score_combined_pipeline(model, cur)
    print_combined_report(combined_results)


if __name__ == "__main__":
    main()
