"""
Talent Dispersion: data collection
----------------------------------
Downloads every source that can be fetched automatically and saves it, unchanged
except for reshaping, into the data/ folder.

    data/matches_men_europe.csv     Match results for the Premier League, La Liga,
                                    Ligue 1 and Bundesliga, 2018-19 to 2024-25
                                    (openfootball/football.json, public domain).
    data/raw/ewf_standings.csv      English Women's Football Database final
                                    standings (Rob Clapp, May 2024), via TidyTuesday.

The other tables (RSSSF and futbol24) can't be downloaded automatically. They were
transcribed from each source page into data/raw/transcribed_tables.csv, with the
page's URL on every row.

Next step: python data_prep.py

Run from anywhere (needs internet access):
    python collect_data.py

Note: openfootball is missing the final matchday (10 games) of La Liga 2024-25.
"""

import csv
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MATCHES_FILE = ROOT / "data" / "matches_men_europe.csv"
EWF_FILE = ROOT / "data" / "raw" / "ewf_standings.csv"

OPENFOOTBALL = "https://raw.githubusercontent.com/openfootball/football.json/master"
EWF_URL = ("https://raw.githubusercontent.com/rfordatascience/tidytuesday/main/"
           "data/2024/2024-07-16/ewf_standings.csv")
SEASONS = ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
LEAGUES = {"en.1": "Premier League", "es.1": "La Liga", "fr.1": "Ligue 1", "de.1": "Bundesliga"}

# La Liga 2024-25's table comes from futbol24, which names teams differently.
# Rename openfootball's names so the match results line up with that table.
NAME_FIXES = {
    ("La Liga", "2024-25"): {
        "FC Barcelona": "Barcelona",
        "Real Madrid CF": "Real Madrid",
        "Club Atlético de Madrid": "Atlético Madrid",
        "Athletic Club": "Athletic Bilbao",
        "Real Betis Balompié": "Real Betis",
        "RC Celta de Vigo": "Celta de Vigo",
        "Rayo Vallecano de Madrid": "Rayo Vallecano",
        "RCD Mallorca": "Real Mallorca",
        "Real Sociedad de Fútbol": "Real Sociedad",
        "RCD Espanyol de Barcelona": "RCD Espanyol",
        "Real Valladolid CF": "Real Valladolid",
    }
}


def collect_matches():
    rows = []
    for season in SEASONS:
        for code, league in LEAGUES.items():
            url = f"{OPENFOOTBALL}/{season}/{code}.json"
            with urllib.request.urlopen(url) as response:
                matches = json.load(response)["matches"]
            fixes = NAME_FIXES.get((league, season), {})
            count = 0
            for m in matches:
                score = m.get("score", {}).get("ft")
                if not score:  # skip unplayed / missing results
                    continue
                rows.append({
                    "league": league,
                    "season": season,
                    "date": m.get("date", ""),
                    "home_team": fixes.get(m["team1"], m["team1"]),
                    "away_team": fixes.get(m["team2"], m["team2"]),
                    "home_goals": score[0],
                    "away_goals": score[1],
                    "source_url": f"https://github.com/openfootball/football.json/blob/master/{season}/{code}.json",
                })
                count += 1
            print(f"  {league} {season}: {count} matches")

    MATCHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MATCHES_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {MATCHES_FILE.relative_to(ROOT)} ({len(rows)} matches)")


def collect_ewf():
    EWF_FILE.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(EWF_URL) as response:
        EWF_FILE.write_bytes(response.read())
    print(f"Saved {EWF_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    collect_matches()
    collect_ewf()
