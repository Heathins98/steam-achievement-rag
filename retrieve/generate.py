"""
Generation - milestone 11, the last step in the pipeline. Takes
whatever chunks retrieve/answer.py found for a question and has Claude
write an actual answer from them, citing which guide it came from,
instead of just printing raw chunk text back at the user.

This is deliberately a thin wrapper around one API call - all the real
work already happened in resolve.py/search.py by the time this runs.
All generate_answer() does is hand Claude the question plus whatever
chunks were retrieved and ask it to answer using only what's there, not
its own general knowledge of the game.

Keeps the last HISTORY_LIMIT question/answer pairs and resends them on
every turn, so a follow-up like "which is the closest day for that?" can
actually be understood - Claude sees what "that" meant. Worth being
honest about the limit of this, though: only the *answer* step gets the
conversation history. find_chunks() (the resolve/search step) still only
ever sees the current question on its own, so a vague follow-up that
depends entirely on earlier context can still retrieve nothing relevant
- conversation memory here means "Claude can follow the thread," not
"the system re-derives what you're really asking and searches for it."
That second, harder thing (rewriting the follow-up into a self-contained
query before retrieval) is a different feature, not built here.

Run with:
    python retrieve/generate.py
for an interactive prompt, same idea as the earlier retrieve/ scripts.
"""

import os
import datetime
import psycopg
import anthropic
from sentence_transformers import SentenceTransformer

from answer import find_chunks, MODEL_NAME

# a fast, cheap model is enough here - this is short grounded synthesis
# from a handful of provided excerpts, not open-ended reasoning
GENERATION_MODEL = "claude-haiku-4-5-20251001"

# how many previous question/answer pairs to resend on every turn. Only
# the plain question text and Claude's written answer go into history -
# NOT the guide excerpts that backed that answer (see main(), which adds
# the bare question, not build_prompt()'s output) - the answer text
# already carries whatever information Claude needs to reference later,
# so there's no reason to keep re-sending old excerpt blocks turn after
# turn. This cap is about keeping requests bounded over a long session,
# not about excerpt volume, which never accumulates in the first place.
HISTORY_LIMIT = 10

SYSTEM_PROMPT_TEMPLATE = """You answer questions about how to get achievements in \
Halo: The Master Chief Collection, using only the guide excerpts you are \
given below - never your own general knowledge of the game. If the \
excerpts do not actually answer the question, say so plainly instead of \
guessing or filling in gaps. Keep answers short and direct - a couple of \
sentences, not the full walkthrough repeated back verbatim. Always name \
which guide the information came from.

Earlier questions and answers in this conversation are included for \
context - use them to understand references like "that achievement" or \
"the one you just mentioned" in a follow-up question.

Today's date is {today}. Some achievements only trigger on specific \
calendar dates (e.g. a seasonal sign, or "play on the Nth of any \
month") - use today's date to answer questions like "which is the \
soonest date" or "can I get this today" correctly, instead of guessing."""


def build_system_prompt():
    """
    Fills in today's date fresh on every call, not once at import time -
    a long-running session shouldn't keep answering with a date that's
    gone stale. Claude has no built-in sense of "now" the way this
    coding session does (that comes from the harness injecting the date
    every turn) - a raw API call like this one only knows what's
    actually in the prompt.
    """
    today = datetime.date.today().strftime("%A, %B %d, %Y")
    return SYSTEM_PROMPT_TEMPLATE.format(today=today)


def build_prompt(question, chunks):
    """
    Formats the question and retrieved chunks into one prompt. Each
    excerpt keeps its source guide title attached right next to the
    text, so Claude can actually cite it instead of guessing which
    guide it came from.
    """
    excerpts = []
    for index, (chunk_id, guide_title, section_title, text) in enumerate(chunks, start=1):
        excerpts.append(f'[Excerpt {index}, from "{guide_title}"]\n{text}')

    excerpt_block = "\n\n".join(excerpts)
    return f"Question: {question}\n\nGuide excerpts:\n\n{excerpt_block}"


def generate_answer(client, question, chunks, history):
    """
    Sends the question and chunks to Claude, along with whatever
    conversation history has built up so far, and returns the written
    answer. Does NOT mutate history - main() decides what to keep.
    """
    if not chunks:
        return "No guide content was found for this question."

    messages = history + [
        {"role": "user", "content": build_prompt(question, chunks)},
    ]

    response = client.messages.create(
        model=GENERATION_MODEL,
        max_tokens=400,
        system=build_system_prompt(),
        messages=messages,
    )
    return response.content[0].text


def trim_history(history, limit):
    """
    Keeps only the last `limit` question/answer pairs (each pair is a
    user message + an assistant message, so 2 * limit entries), dropping
    the oldest ones first.
    """
    max_messages = limit * 2
    return history[-max_messages:]


def main():
    database_url = os.environ["DATABASE_URL"]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is not set - check your .env file")
    client = anthropic.Anthropic(api_key=api_key)

    print(f"loading {MODEL_NAME}...")
    embedding_model = SentenceTransformer(MODEL_NAME)

    print(f"Ask a question (or type 'quit') - remembers the last {HISTORY_LIMIT} exchanges:")
    history = []
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            while True:
                question = input("\n> ").strip()
                if not question or question.lower() in ("quit", "exit"):
                    break

                method, display_name, chunks = find_chunks(question, embedding_model, cur)
                found_via = f" -> {display_name}" if display_name else ""
                print(f"  ({method}{found_via}, {len(chunks)} chunk(s) retrieved)")

                answer = generate_answer(client, question, chunks, history)
                print(f"\n{answer}")

                # only the plain question goes in history, not the full
                # prompt with excerpts baked in - keeps old excerpt
                # blocks from being reprocessed as if they were the
                # user's own words in later turns
                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": answer})
                history = trim_history(history, HISTORY_LIMIT)


if __name__ == "__main__":
    main()
