"""
Talent Dispersion: data cleaning and preparation
------------------------------------------------
Combines every source into one cleaned table per team-season, checks it, and
calculates the fields used in the charts.

Inputs (made by collect_data.py, plus the transcribed tables):
    data/matches_men_europe.csv        openfootball match results (men's Europe)
    data/raw/ewf_standings.csv         English Women's Football Database standings
    data/raw/transcribed_tables.csv    RSSSF / futbol24 tables, as shown on the source pages

Outputs:
    data/team_seasons.csv     one row per team per season
    data/league_seasons.csv   one row per league-season (competitive-balance measures)

Steps
    1. Build league tables from the openfootball match results (W/D/L, goals; points = 3W + D).
    2. Load the WSL tables (2018-19 to 2023-24) from the English Women's Football Database.
    3. Load the transcribed RSSSF and futbol24 tables.
    4. Clean: tidy team names and correct known errors in the sources.
    5. Check every table: W + D + L = P for every team; league-wide wins = losses,
       goals for = goals against, and draws even. Points that don't equal 3W + D
       are reported (they are documented points deductions).
    6. Calculate win/draw/loss %, goal difference per game, and per league-season the
       standard deviation of win % and the Noll-Scully ratio (also without FC Barcelona
       for Liga F).

Run from anywhere:
    pip install pandas numpy
    python data_prep.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MATCHES_FILE = DATA / "matches_men_europe.csv"
EWF_FILE = DATA / "raw" / "ewf_standings.csv"
TRANSCRIBED_FILE = DATA / "raw" / "transcribed_tables.csv"
TEAM_OUT = DATA / "team_seasons.csv"
LEAGUE_OUT = DATA / "league_seasons.csv"

WOMENS_LEAGUES = {"NWSL", "WSL", "Liga F", "Première Ligue", "Frauen-Bundesliga"}
FIRST_SEASON, LAST_EWF_SEASON = "2018-19", "2023-24"

EWF_SOURCE = "English Women's Football Database (Rob Clapp, May 2024) via TidyTuesday"
EWF_URL = "https://github.com/rfordatascience/tidytuesday/tree/main/data/2024/2024-07-16"
OPENFOOTBALL_SOURCE = "openfootball/football.json (match results, aggregated)"

# Errors in the sources, found by the points check (points should equal 3W + D).
CORRECTIONS = {
    ("NWSL", "2025", "Kansas City Current"): {"Pts": 65},   # RSSSF lists 55 (21-2-3)
    ("NWSL", "2023", "Portland Thorns FC"): {"Pts": 35},    # RSSSF lists 36 (10-5-7)
}

COLUMNS = ["league", "season", "team", "P", "W", "D", "L", "GF", "GA", "Pts",
           "source", "source_url"]


# ----------------------------------------------------------------------------
# 1-3. Load each source as a league table
# ----------------------------------------------------------------------------
def tables_from_matches(matches):
    """Aggregate match results into one row per team per league-season."""
    home = pd.DataFrame({
        "league": matches["league"], "season": matches["season"],
        "team": matches["home_team"], "GF": matches["home_goals"],
        "GA": matches["away_goals"], "source_url": matches["source_url"],
    })
    away = pd.DataFrame({
        "league": matches["league"], "season": matches["season"],
        "team": matches["away_team"], "GF": matches["away_goals"],
        "GA": matches["home_goals"], "source_url": matches["source_url"],
    })
    games = pd.concat([home, away], ignore_index=True)
    games["W"] = (games["GF"] > games["GA"]).astype(int)
    games["D"] = (games["GF"] == games["GA"]).astype(int)
    games["L"] = (games["GF"] < games["GA"]).astype(int)

    table = (games.groupby(["league", "season", "team"], as_index=False)
             .agg(P=("GF", "size"), W=("W", "sum"), D=("D", "sum"), L=("L", "sum"),
                  GF=("GF", "sum"), GA=("GA", "sum"), source_url=("source_url", "first")))
    table["Pts"] = 3 * table["W"] + table["D"]
    table["source"] = OPENFOOTBALL_SOURCE
    return table


def load_openfootball():
    matches = pd.read_csv(MATCHES_FILE)
    # La Liga 2024-25 is missing its final matchday in openfootball, so that season's
    # table comes from the transcribed futbol24 table instead.
    complete = ~((matches["league"] == "La Liga") & (matches["season"] == "2024-25"))
    return tables_from_matches(matches[complete])


def load_ewf():
    ewf = pd.read_csv(EWF_FILE)
    ewf = ewf[ewf["tier"] == 1].copy()
    # "2018-2019" -> "2018-19"
    ewf["season"] = ewf["season"].str[:5] + ewf["season"].str[7:9]
    ewf = ewf[(ewf["season"] >= FIRST_SEASON) & (ewf["season"] <= LAST_EWF_SEASON)]
    return pd.DataFrame({
        "league": "WSL", "season": ewf["season"], "team": ewf["team_name"],
        "P": ewf["played"], "W": ewf["wins"], "D": ewf["draws"], "L": ewf["losses"],
        "GF": ewf["goals_for"], "GA": ewf["goals_against"], "Pts": ewf["points"],
        "source": EWF_SOURCE, "source_url": EWF_URL,
    })


def load_transcribed():
    return pd.read_csv(TRANSCRIBED_FILE, dtype={"season": str})


# ----------------------------------------------------------------------------
# 4. Clean
# ----------------------------------------------------------------------------
def clean(df):
    df = df.copy()
    df["season"] = df["season"].astype(str)
    # Footnote markers (e.g. "Angel City FC*") and stray whitespace.
    df["team"] = (df["team"].str.replace(r"\*+$", "", regex=True)
                  .str.replace(r"\s+", " ", regex=True).str.strip())
    for col in ["P", "W", "D", "L", "GF", "GA", "Pts"]:
        df[col] = df[col].astype(int)

    for (league, season, team), fixes in CORRECTIONS.items():
        mask = (df["league"] == league) & (df["season"] == season) & (df["team"] == team)
        if mask.sum() != 1:
            raise ValueError(f"Correction target not found: {league} {season} {team}")
        for col, value in fixes.items():
            print(f"  Corrected {league} {season} {team}: {col} "
                  f"{df.loc[mask, col].iloc[0]} -> {value}")
            df.loc[mask, col] = value
    return df


# ----------------------------------------------------------------------------
# 5. Check
# ----------------------------------------------------------------------------
def check(df):
    bad_rows = df[df["W"] + df["D"] + df["L"] != df["P"]]
    if len(bad_rows):
        raise ValueError(f"W + D + L != P for:\n{bad_rows}")

    for (league, season), t in df.groupby(["league", "season"]):
        problems = []
        if t["W"].sum() != t["L"].sum():
            problems.append(f"wins {t['W'].sum()} != losses {t['L'].sum()}")
        if t["GF"].sum() != t["GA"].sum():
            problems.append(f"goals for {t['GF'].sum()} != goals against {t['GA'].sum()}")
        if t["D"].sum() % 2:
            problems.append(f"odd number of draws ({t['D'].sum()})")
        if problems:
            raise ValueError(f"{league} {season}: " + "; ".join(problems))

    deductions = df[3 * df["W"] + df["D"] != df["Pts"]]
    for r in deductions.itertuples():
        print(f"  Points deduction: {r.league} {r.season} {r.team} "
              f"({3 * r.W + r.D - r.Pts} points)")
    print(f"  All {df.groupby(['league', 'season']).ngroups} league-seasons pass the checks")


# ----------------------------------------------------------------------------
# 6. Calculate
# ----------------------------------------------------------------------------
def add_team_fields(df):
    df = df.copy()
    df["gender"] = np.where(df["league"].isin(WOMENS_LEAGUES), "W", "M")
    df["GD"] = df["GF"] - df["GA"]
    df["win_pct"] = (df["W"] / df["P"]).round(4)
    df["draw_pct"] = (df["D"] / df["P"]).round(4)
    df["loss_pct"] = (df["L"] / df["P"]).round(4)
    df["gd_per_game"] = (df["GD"] / df["P"]).round(3)
    df = df.sort_values(["league", "season", "Pts"], ascending=[True, True, False], kind="stable")
    return df[["league", "gender", "season", "team", "P", "W", "D", "L", "GF", "GA", "GD",
               "Pts", "win_pct", "draw_pct", "loss_pct", "gd_per_game", "source", "source_url"]]


def balance(t):
    """Standard deviation of win % and the Noll-Scully ratio for one league-season.
    Expected SD if all teams were equally good = sqrt(p(1-p) * mean(1/G)), where p is
    the league's win rate and G each team's games played (handles uneven schedules)."""
    win_pct = t["W"] / t["P"]
    p = t["W"].sum() / t["P"].sum()
    actual = win_pct.std(ddof=0)
    expected = np.sqrt(p * (1 - p) * (1 / t["P"]).mean())
    return actual, actual / expected


def league_table(df):
    rows = []
    for (league, season), t in df.groupby(["league", "season"]):
        sd, ns = balance(t)
        if league == "Liga F":
            sd_nb, ns_nb = balance(t[t["team"] != "FC Barcelona"])
        else:
            sd_nb, ns_nb = sd, ns
        rows.append({
            "league": league, "gender": t["gender"].iloc[0], "season": season,
            "teams": len(t), "avg_games": round(t["P"].mean(), 1),
            "sd_win_pct": round(sd * 100, 2), "noll_scully": round(ns, 3),
            "sd_win_pct_no_barca": round(sd_nb * 100, 2), "noll_scully_no_barca": round(ns_nb, 3),
            "source": t["source"].iloc[0], "source_url": t["source_url"].iloc[0],
        })
    return pd.DataFrame(rows)


def main():
    print("Loading sources")
    combined = pd.concat([load_openfootball()[COLUMNS], load_ewf()[COLUMNS],
                          load_transcribed()[COLUMNS]], ignore_index=True)
    print(f"  {len(combined)} team-season rows")

    print("Cleaning")
    combined = clean(combined)

    print("Checking")
    check(combined)

    print("Calculating")
    teams = add_team_fields(combined)
    leagues = league_table(teams)
    teams.to_csv(TEAM_OUT, index=False)
    leagues.to_csv(LEAGUE_OUT, index=False)
    print(f"Saved {TEAM_OUT.relative_to(ROOT)} ({len(teams)} rows)")
    print(f"Saved {LEAGUE_OUT.relative_to(ROOT)} ({len(leagues)} rows)")


if __name__ == "__main__":
    main()
