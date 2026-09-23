"""
Parses the sub_game out of each achievement's description and loads
everything into the achievements table.

Steam doesn't give us sub_game as its own field - it's buried inside the
description text as a prefix, like "Halo: Reach: Complete Winter
Contingency." Splitting on the first colon doesn't work (confirmed by
hand-inspection): some sub-game names have a colon inside them
("Halo: Reach"), and some mission names inside the description also have
a colon ("Complete ONI: Sword Base."). So instead of splitting on ":",
this checks whether the description starts with one of a small list of
known prefixes.

Confirmed by grepping the raw JSON for "ODST": all 97 achievements using
the "H3: " prefix are actually "H3: ODST: " - there is no separate plain
"H3: " bucket. Halo 3 proper uses the full "Halo 3: " prefix instead
(that's a different 89 achievements). So "H3: ODST: " has to be checked
before "H3: ", or every ODST achievement would get mislabeled as plain
Halo 3.

Run with:
    python transform/parse_subgame.py
"""

import os
import json
import psycopg

HERE = os.path.dirname(__file__)
SCHEMA_FILE = os.path.join(HERE, "..", "ingest", "cache", "schema_976730.json")
PERCENT_FILE = os.path.join(HERE, "..", "ingest", "cache", "global_pct_976730.json")

# Order matters - a more specific prefix has to be checked before a
# shorter one it starts with, or the shorter one would win first. There
# is no plain "Halo: " entry here on purpose - it was never seen on its
# own in the data, only as part of "Halo: Reach: ". Same reason
# "H3: ODST: " has to come before "H3: " - every "H3: ODST: ..."
# description also starts with "H3: ".
KNOWN_PREFIXES = [
    "Halo: Reach: ",
    "H3: ODST: ",
    "Halo 2A MP: ",
    "Halo 2 MP: ",
    "Halo CE: ",
    "Halo 2: ",
    "Halo 3: ",
    "Halo 4: ",
    "H3: ",
]


def parse_sub_game(description):
    """
    Looks at the start of an achievement's description and returns the
    sub_game name (prefix with the trailing ": " removed) if it matches
    one of the known prefixes. Returns None if this achievement is
    collection-wide, like "Kill 100 Grunts." with no prefix at all.
    """
    for prefix in KNOWN_PREFIXES:
        if description.startswith(prefix):
            return prefix[:-2]  # chop off the trailing ": "
    return None


def load_achievements():
    """Reads the two raw JSON files from milestone 3 and turns them into
    a list of dicts, one per achievement, ready to load into Postgres."""
    with open(SCHEMA_FILE) as f:
        schema_data = json.load(f)
    achievements = schema_data["game"]["availableGameStats"]["achievements"]

    with open(PERCENT_FILE) as f:
        percent_data = json.load(f)
    percentages = percent_data["achievementpercentages"]["achievements"]

    # turn the percentages list into a name -> percent lookup
    percent_by_name = {}
    for entry in percentages:
        percent_by_name[entry["name"]] = entry["percent"]

    rows = []
    for achievement in achievements:
        # hidden achievements don't have a "description" key at all,
        # not just an empty one, so use .get() here
        description = achievement.get("description", "")
        rows.append({
            "api_name": achievement["name"],
            "display_name": achievement["displayName"],
            "description": description if description else None,
            "is_hidden": bool(achievement["hidden"]),
            "sub_game": parse_sub_game(description),
            "global_pct": percent_by_name.get(achievement["name"]),
        })
    return rows


def upsert_achievements(rows):
    """
    Loads every row into the achievements table. Uses ON CONFLICT so
    running this script again (e.g. after Steam updates a description)
    updates the existing rows instead of erroring out or duplicating them.
    """
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO achievements
                        (api_name, display_name, description, is_hidden, sub_game, global_pct)
                    VALUES
                        (%(api_name)s, %(display_name)s, %(description)s, %(is_hidden)s, %(sub_game)s, %(global_pct)s)
                    ON CONFLICT (api_name) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        description  = EXCLUDED.description,
                        is_hidden    = EXCLUDED.is_hidden,
                        sub_game     = EXCLUDED.sub_game,
                        global_pct   = EXCLUDED.global_pct
                    """,
                    row,
                )
        conn.commit()


def main():
    rows = load_achievements()
    print(f"parsed {len(rows)} achievements")

    with_sub_game = sum(1 for r in rows if r["sub_game"] is not None)
    print(f"  {with_sub_game} matched a known sub_game prefix")
    print(f"  {len(rows) - with_sub_game} are collection-wide (no prefix)")

    upsert_achievements(rows)
    print(f"loaded {len(rows)} rows into achievements")


if __name__ == "__main__":
    main()
