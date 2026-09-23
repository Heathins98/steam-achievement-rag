"""
Fetches the top ~20 Steam Community Guides for Halo MCC and saves the
raw JSON to ingest/cache/. Same rule as achievements.py - this script
only captures, it does not parse or reshape anything.

Three chained Steam API calls, one feeding the next:
  1. QueryFiles       - search for guides for this app, get back a list
                         of guide IDs, sorted by Steam's rating
  2. GetDetails        - get title/author/vote info for each ID
  3. GetSubSectionData - get the actual section-by-section guide text
                         for each ID (this is what transform/chunk.py
                         will split into chunks later)

IMPORTANT - honesty check on how sure I am about each endpoint:
QueryFiles is well documented and the params/response shape below are
confirmed. GetDetails and GetSubSectionData are NOT well documented -
I could not find an authoritative response shape for either one. The
parameters below are my best-supported guess based on how the rest of
the Steam Web API is shaped, not something I confirmed against real
output. Inspect ingest/cache/guides_details_976730.json and one of the
guide_sections_*.json files by hand (same as milestone 4) before
assuming anything about their structure in transform/chunk.py.

Run with:
    python ingest/guides.py
"""

import os
import json
import time
import requests

# Halo: The Master Chief Collection
APP_ID = 976730

# Started at 20 (milestone 6's "~20 top guides"). Raised to 50 after
# eval/metrics.py showed 37 of 100 gold-set questions hitting achievements
# with zero guide coverage at all - specifically campaign completion and
# LASO playlist achievements, since the top-voted guides at 20 skewed
# multiplayer-compilation-heavy. 50 also matches the scale the project
# brief itself originally estimated ("~50 guide fetches").
NUM_GUIDES = 50

# Round 1: after raising NUM_GUIDES to 50, a coverage check showed 44 of
# the 94 still-uncovered achievements were Halo 4 - by far the biggest
# single group. A targeted "Halo 4" search fetch dropped that to 3.
#
# Round 2: with Halo 4 fixed, the remaining ~52 uncovered achievements
# are spread thin across several sub-games instead of one dominant
# group - H3: ODST (11) and Halo: Reach (10) are the next-biggest, so
# those are the next two targeted searches. Diminishing returns are
# expected here compared to round 1 (no single fix will be as large),
# which is exactly why this list only grows one deliberate step at a
# time instead of guessing a big batch of searches up front.
TARGETED_SEARCHES = ["ODST", "Halo Reach"]
GUIDES_PER_SEARCH = 15

HERE = os.path.dirname(__file__)
CACHE_DIR = os.path.join(HERE, "cache")


def find_top_guide_ids(api_key, app_id, count):
    """
    Searches Steam's published-file listing for this app, filtered down
    to just Guides (filetype 10), sorted by Steam's own "ranked by vote"
    score - a general best/top-rated ranking that weighs both up and
    down votes, not just a raw upvote count.
    """
    url = "https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/"
    params = {
        "key": api_key,
        "appid": app_id,
        "filetype": 10,        # k_PFI_MatchingFileType_AllGuides
        "query_type": 0,       # k_PublishedFileQueryType_RankedByVote
        "numperpage": count,
        "page": 1,
        "return_vote_data": True,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def find_guide_ids_by_search(api_key, app_id, search_text, count):
    """
    Same idea as find_top_guide_ids, but ranked by how well the guide's
    title/description matches search_text, not by vote score - for
    pulling in guides about something specific that pure vote-ranking
    keeps missing (confirmed: search_text is a real QueryFiles param,
    "text to match in the item's title or description").
    """
    url = "https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/"
    params = {
        "key": api_key,
        "appid": app_id,
        "filetype": 10,        # k_PFI_MatchingFileType_AllGuides
        "query_type": 12,      # k_PublishedFileQueryType_RankedByTextSearch
        "search_text": search_text,
        "numperpage": count,
        "page": 1,
        "return_vote_data": True,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def extract_guide_ids(query_data, source_filename):
    """
    Pulls the list of guide ids out of a QueryFiles response - shared by
    both the top-voted and the targeted-search fetches, since they
    return the same response shape. Fails loudly with the exact file to
    go inspect if the shape doesn't match, same reasoning as before.
    """
    found_guides = query_data.get("response", {}).get("publishedfiledetails")
    if found_guides is None:
        raise SystemExit(
            f"couldn't find 'publishedfiledetails' in the QueryFiles "
            f"response - open ingest/cache/{source_filename} by hand and "
            f"see what the top-level keys actually look like"
        )
    return [g["publishedfileid"] for g in found_guides]


def fetch_guide_details(api_key, published_file_ids):
    """
    Gets title/author/vote info for a batch of guide IDs in one call.
    Steam wants each id passed as its own indexed query param, e.g.
    publishedfileids[0]=X&publishedfileids[1]=Y - not a single list.
    """
    url = "https://api.steampowered.com/IPublishedFileService/GetDetails/v1/"
    params = {
        "key": api_key,
        "includevotes": True,
    }
    for index, file_id in enumerate(published_file_ids):
        params[f"publishedfileids[{index}]"] = file_id

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def fetch_guide_sections(api_key, published_file_id):
    """
    Gets the section-by-section text for a single guide. This is the
    endpoint with the least documentation of the three - if the
    response only turns out to contain a table of contents instead of
    full section text, there's probably an extra parameter needed here
    that I wasn't able to confirm. Check the saved JSON by hand first.
    """
    url = "https://api.steampowered.com/IPublishedFileService/GetSubSectionData/v1/"
    params = {
        "key": api_key,
        "publishedfileid": published_file_id,
        "appid": APP_ID,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def save_json(data, filename):
    """Writes data out to ingest/cache/<filename>, pretty-printed."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"saved {path}")


def main():
    api_key = os.environ.get("STEAM_API_KEY")
    if not api_key:
        raise SystemExit("STEAM_API_KEY is not set - check your .env file")

    print(f"searching for top {NUM_GUIDES} guides...")
    query_data = find_top_guide_ids(api_key, APP_ID, NUM_GUIDES)
    save_json(query_data, "guides_query_976730.json")
    guide_ids = extract_guide_ids(query_data, "guides_query_976730.json")
    print(f"  found {len(guide_ids)} guides")

    # on top of the vote-ranked list above, pull in guides for whatever's
    # specifically under-covered (right now just Halo 4) - skip anything
    # already in guide_ids so it doesn't get fetched or processed twice
    for search_text in TARGETED_SEARCHES:
        print(f"searching for guides matching {search_text!r}...")
        search_filename = f"guides_search_{search_text.replace(' ', '_')}.json"
        search_data = find_guide_ids_by_search(api_key, APP_ID, search_text, GUIDES_PER_SEARCH)
        save_json(search_data, search_filename)

        found_ids = extract_guide_ids(search_data, search_filename)
        new_ids = [gid for gid in found_ids if gid not in guide_ids]
        print(f"  found {len(found_ids)} guides, {len(new_ids)} new")
        guide_ids.extend(new_ids)

    print(f"fetching guide details for {len(guide_ids)} guides...")
    details_data = fetch_guide_details(api_key, guide_ids)
    save_json(details_data, "guides_details_976730.json")

    print("fetching section text for each guide...")
    for guide_id in guide_ids:
        sections_data = fetch_guide_sections(api_key, guide_id)
        save_json(sections_data, f"guide_sections_{guide_id}.json")
        # a short pause between requests - just being a polite API
        # citizen, not a real rate limit concern at this scale
        time.sleep(0.5)

    print("done")


if __name__ == "__main__":
    main()
