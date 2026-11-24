"""
Talent Dispersion: where each league's imbalance comes from, and how it lines up with Europe.

Makes one chart page from data/team_seasons.csv and data/uwcl_knockout_stages_2016_2026.csv:

  graphs/top_bottom_gap.html  For each European women's league, the average goal difference per game
                              of the team that finished first (right, red) and the team that finished
                              last (left, navy), with that league's Champions League finals and titles.

How the numbers are made:
  - First and last place follow the final table (points per game, then goal difference per game),
    averaged over every season in team_seasons.csv for that league.
  - Champions League finals and titles count every finalist/winner from that league,
    2016-17 to 2025-26.

Run from anywhere:
    pip install pandas plotly
    python graphs/system_chart.py
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent.parent
TEAMS_FILE = ROOT / "data" / "team_seasons.csv"
UWCL_FILE = ROOT / "data" / "uwcl_knockout_stages_2016_2026.csv"
OUT_FILE = ROOT / "graphs" / "top_bottom_gap.html"

WOMEN = "#ce0041"
NAVY = "#113476"
GOLD = "#99824c"
TEXT = "#000000"
PAGE_BG = "#F2F0EF"
PLOT_BG = "#fefefe"
GRID = "#e6e6e6"
FONT = "Times New Roman, Times, serif"
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}

LEAGUES = ["Liga F", "Première Ligue", "Frauen-Bundesliga", "WSL"]

# Which league each Champions League finalist plays in
NAME_FIXES = {"VfL Wolfsburg": "Wolfsburg", "Paris Saint-Germain": "PSG", "OL Lyonnes": "Lyon"}
CLUB_LEAGUE = {
    "Barcelona": "Liga F", "Real Madrid": "Liga F", "Atlético Madrid": "Liga F",
    "Lyon": "Première Ligue", "PSG": "Première Ligue", "Montpellier": "Première Ligue",
    "Wolfsburg": "Frauen-Bundesliga", "Bayern Munich": "Frauen-Bundesliga",
    "Chelsea": "WSL", "Arsenal": "WSL", "Manchester City": "WSL", "Manchester United": "WSL",
}


def first_last():
    t = pd.read_csv(TEAMS_FILE)
    t = t[(t["gender"] == "W") & (t["league"].isin(LEAGUES))].copy()
    t["ppg"] = t["Pts"] / t["P"]
    rows = []
    for (league, season), g in t.groupby(["league", "season"]):
        g = g.sort_values(["ppg", "gd_per_game"], ascending=False)
        rows.append({"league": league, "best": g["gd_per_game"].iloc[0],
                     "worst": g["gd_per_game"].iloc[-1]})
    out = pd.DataFrame(rows).groupby("league").agg(best=("best", "mean"), worst=("worst", "mean"),
                                                   seasons=("best", "size"))
    return out


def uwcl():
    u = pd.read_csv(UWCL_FILE)
    res = {lg: {"finals": 0, "titles": 0} for lg in LEAGUES}
    for col, key in [("finalists", "finals"), ("winners", "titles")]:
        for cell in u[col]:
            for club in cell.split(","):
                club = NAME_FIXES.get(club.strip(), club.strip())
                lg = CLUB_LEAGUE.get(club)
                if lg in res:
                    res[lg][key] += 1
    return res


def main():
    fl = first_last()
    eu = uwcl()
    # Order: biggest best-team margin at the top
    order = fl.sort_values("best", ascending=False).index.tolist()
    labels = [f"<b>{lg}</b><br>Finals {eu[lg]['finals']} · Titles {eu[lg]['titles']}" for lg in order]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=[fl.loc[lg, "worst"] for lg in order], orientation="h", name="Last-place team",
        marker=dict(color=NAVY, line=dict(color=GOLD, width=1.5)),
        text=[f"{fl.loc[lg, 'worst']:+.2f}" for lg in order], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>Last-place team: %{x:+.2f} goals per game<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=labels, x=[fl.loc[lg, "best"] for lg in order], orientation="h", name="First-place team",
        marker=dict(color=WOMEN, line=dict(color=GOLD, width=1.5)),
        text=[f"{fl.loc[lg, 'best']:+.2f}" for lg in order], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>First-place team: %{x:+.2f} goals per game<extra></extra>",
    ))
    lim = max(fl["best"].max(), -fl["worst"].min()) * 1.25
    fig.update_layout(
        title=dict(text="Where each league's gap comes from: the top or the bottom", x=0.01,
                   font=dict(size=22, color=TEXT)),
        barmode="overlay", bargap=0.35,
        font=dict(family=FONT, size=15, color=TEXT),
        paper_bgcolor=PAGE_BG, plot_bgcolor=PLOT_BG, height=520,
        margin=dict(t=80, r=40, b=110, l=10),
        hoverlabel=dict(font_family=FONT, bgcolor="white", bordercolor=GOLD),
        legend=dict(orientation="h", x=0, y=-0.2, font=dict(size=14), traceorder="reversed"),
        dragmode=False,
    )
    fig.update_xaxes(range=[-lim, lim], title_text="Average goal difference per game",
                     zeroline=True, zerolinecolor="#555555", zerolinewidth=2, gridcolor=GRID,
                     fixedrange=True)
    fig.update_yaxes(autorange="reversed", automargin=True, fixedrange=True)

    paragraphs = [
        "Each row shows how far the average champion finished ahead (red, right) and how far the average "
        "last-place team finished behind (navy, left), in goals per game. Leagues are ordered by how dominant "
        "their champion is. Under each league: its clubs' Champions League finals and titles, "
        "2016&ndash;17 to 2025&ndash;26.",
        "League tables: averages over every season in team_seasons.csv (2018&ndash;19 to 2024&ndash;25). "
        "Champions League: uwcl_knockout_stages_2016_2026.csv.",
    ]
    text = "\n".join(f"      <p>{p}</p>" for p in paragraphs)
    chart = fig.to_html(full_html=False, include_plotlyjs="cdn", config=PLOT_CONFIG)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Top or bottom: where the gap comes from | Talent Dispersion</title>
  <link rel="stylesheet" href="../css/style.css">
  <script>
    // Inside another page's frame, hide the site header and footer (that page has its own).
    if (window.self !== window.top) document.documentElement.classList.add("embedded");
  </script>
  <style>
    .wrap {{ flex: 1; width: 100%; max-width: 1200px; margin: 0 auto; padding: 16px 24px 32px; }}
    .text {{ max-width: 900px; color: {TEXT}; font-size: 0.9rem; line-height: 1.5; }}
    .text p {{ margin: 0 0 0.6em; }}
    .embedded .site-header, .embedded .site-footer {{ display: none; }}
    .embedded body {{ min-height: 0; }}
  </style>
</head>
<body>
  <header class="site-header">
    <div class="container">
      <a class="site-title" href="../index.html"><span class="mark">&#9632;</span> Talent Dispersion</a>
      <button class="nav-toggle" aria-expanded="false" aria-controls="site-nav">Menu</button>
      <nav class="site-nav" id="site-nav" aria-label="Main">
        <ul>
          <li><a href="../index.html">Home</a></li>
          <li><a href="../case-studies.html">Case Studies</a></li>
          <li><a href="../methodology.html">Methodology</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <div class="wrap">
{chart}
    <div class="text">
{text}
    </div>
  </div>

  <footer class="site-footer">
    <div class="container">
      <span>Talent Dispersion</span>
    </div>
  </footer>
  <script src="../js/main.js"></script>
</body>
</html>
"""
    OUT_FILE.write_text(html, encoding="utf-8")
    print(fl.loc[order].round(2).to_string())
    print({lg: eu[lg] for lg in order})
    print(f"Saved {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
