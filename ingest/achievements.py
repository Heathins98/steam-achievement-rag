"""
Grabs the Halo MCC achievement data from the Steam Web API and saves it
to ingest/cache/ as raw JSON.

This script does NOT parse or clean anything - it just calls the two
endpoints and writes exactly what Steam sends back to disk. Parsing
(splitting out sub_game, figuring out what to do with hidden
achievements, etc.) happens later in transform/, as its own separate
step, so we don't have to re-hit the API if the parsing logic changes.

Run it with:
    python ingest/achievements.py
"""

import os
import json
import requests

# Halo: The Master Chief Collection
APP_ID = 976730

# ingest/cache/, next to this script, no matter where you run it from
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


def fetch_schema(api_key, app_id):
    """
    Calls GetSchemaForGame. This is the endpoint that needs the API key.
    Gives us achievement names, display names, descriptions, and whether
    each one is hidden.
    """
    url = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
    params = {
        "key": api_key,
        "appid": app_id,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def fetch_global_percentages(app_id):
    """
    Calls GetGlobalAchievementPercentagesForApp. No API key needed for
    this one. Note Steam calls the parameter "gameid" here instead of
    "appid" - same number, just an inconsistent name on their end.
    """
    url = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/"
    params = {
        "gameid": app_id,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def save_json(data, filename):
    """Writes data out to ingest/cache/<filename>, pretty-printed so it's
    easy to open and read by hand."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"saved {path}")


def main():
    api_key = os.environ.get("STEAM_API_KEY")
    if not api_key:
        raise SystemExit("STEAM_API_KEY is not set - check your .env file")

    print("fetching achievement schema...")
    schema_data = fetch_schema(api_key, APP_ID)
    achievements = schema_data["game"]["availableGameStats"]["achievements"]
    print(f"  got {len(achievements)} achievements")
    save_json(schema_data, f"schema_{APP_ID}.json")

    print("fetching global achievement percentages...")
    percent_data = fetch_global_percentages(APP_ID)
    percentages = percent_data["achievementpercentages"]["achievements"]
    print(f"  got percentages for {len(percentages)} achievements")
    save_json(percent_data, f"global_pct_{APP_ID}.json")

    print("done")


if __name__ == "__main__":
    main()
