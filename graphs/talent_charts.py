"""
Talent Dispersion: where the world's top 100 women's players play.

Makes two interactive chart pages from data/womensT100.csv:

  graphs/t100_by_league.html  Top-100 players in each league, every year 2016-2025.
  graphs/t100_top_clubs.html  The clubs with the most top-100 players. Pick a year
                              (2016-2025) and how many clubs to show (2, 5, 10, All).

Ranking rules for the club chart:
  - Clubs are ranked by how many top-100 players they have.
  - Tied clubs share a place, and the next place is skipped
    (two clubs tied 10th means the next club is 12th).
  - "Top N" shows every club placed N or better, so a tie at the cut-off can show more than N.
  - "All" shows every club placed 19th or better, and groups the rest as "Other".

Input (keep the repo's folder structure):
    data/womensT100.csv

Run from anywhere:
    pip install pandas plotly
    python graphs/talent_charts.py
"""

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent.parent   # repo root (this file is in graphs/)
DATA_FILE = ROOT / "data" / "womensT100.csv"
OUT_DIR = ROOT / "graphs"

# Same look as charts.py
WOMEN = "#ce0041"   # Arsenal red
NAVY = "#113476"    # Arsenal navy
GOLD = "#99824c"    # markers / outlines
TEXT = "#000000"
PAGE_BG = "#F2F0EF"
PLOT_BG = "#fefefe"
GRID = "#e6e6e6"
FONT = "Times New Roman, Times, serif"
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}

PROJECT_LEAGUES = ["WSL", "NWSL", "Liga F", "Première Ligue", "Frauen-Bundesliga"]
OTHER_LEAGUES = "Other leagues"

# One colour, marker shape and dash per line, so lines can be told apart without colour.
LEAGUE_STYLE = {
    "WSL":               dict(color=WOMEN,     symbol="circle",       dash="solid"),
    "NWSL":              dict(color=NAVY,      symbol="square",       dash="solid"),
    "Liga F":            dict(color=GOLD,      symbol="diamond",      dash="solid"),
    "Première Ligue":    dict(color="#1f7a5c", symbol="triangle-up",  dash="solid"),
    "Frauen-Bundesliga": dict(color="#555555", symbol="x",            dash="solid"),
    OTHER_LEAGUES:       dict(color="#a8a8a8", symbol="circle-open",  dash="dot"),
}

ALL_VIEW_CLUBS = 19   # "All" view: clubs placed 19th or better, then "Other"


# ----------------------------------------------------------------------------
# Shared page template (same header/footer as the other chart pages)
# ----------------------------------------------------------------------------
def page(title, body, extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Talent Dispersion</title>
  <link rel="stylesheet" href="../css/style.css">
  <script>
    // Inside another page's frame, hide the site header and footer (that page has its own).
    if (window.self !== window.top) document.documentElement.classList.add("embedded");
  </script>
  <style>
    .wrap {{ flex: 1; width: 100%; max-width: 1200px; margin: 0 auto; padding: 16px 24px 32px; }}
    .text {{ max-width: 900px; color: {TEXT}; }}
    .embedded .site-header, .embedded .site-footer {{ display: none; }}
    .embedded body {{ min-height: 0; }}
  </style>
{extra_head}
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
{body}
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


def paragraphs_html(paragraphs):
    return "\n".join(f"      <p>{p}</p>" for p in paragraphs)


# ----------------------------------------------------------------------------
# Chart 1: top-100 players by league, per year
# ----------------------------------------------------------------------------
def chart_by_league(df):
    df = df.copy()
    df["group"] = df["league"].where(df["league"].isin(PROJECT_LEAGUES), OTHER_LEAGUES)
    counts = (df.groupby(["year", "group"]).size()
                .unstack(fill_value=0)
                .reindex(columns=PROJECT_LEAGUES + [OTHER_LEAGUES], fill_value=0))
    years = counts.index.tolist()

    fig = go.Figure()
    for group in counts.columns:
        s = LEAGUE_STYLE[group]
        fig.add_trace(go.Scatter(
            x=years, y=counts[group].tolist(), name=group, mode="lines+markers",
            line=dict(color=s["color"], width=2, dash=s["dash"]),
            marker=dict(symbol=s["symbol"], size=10, color=s["color"],
                        line=dict(color=GOLD, width=1)),
            hovertemplate=f"<b>{group}</b><br>%{{x}}: %{{y}} of the top 100<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="Where the world's top 100 players play, by league", x=0.01,
                   font=dict(size=22, color=TEXT)),
        font=dict(family=FONT, size=15, color=TEXT),
        paper_bgcolor=PAGE_BG, plot_bgcolor=PLOT_BG, height=600,
        margin=dict(t=80, r=30, b=120, l=70),
        hoverlabel=dict(font_family=FONT, bgcolor="white", bordercolor=GOLD),
        legend=dict(orientation="h", x=0, y=-0.15, font=dict(size=14)),
        dragmode=False,
    )
    fig.update_xaxes(tickmode="array", tickvals=years, showline=True, linecolor="#888888",
                     fixedrange=True)
    fig.update_yaxes(title_text="Players in the top 100", rangemode="tozero",
                     showline=True, linecolor="#888888", gridcolor=GRID, fixedrange=True)

    first, last = years[0], years[-1]
    wsl0, wsl1 = counts.loc[first, "WSL"], counts.loc[last, "WSL"]
    nwsl_peak_year = counts["NWSL"].idxmax()
    nwsl_peak, nwsl1 = counts["NWSL"].max(), counts.loc[last, "NWSL"]
    paragraphs = [
        f"Each line counts how many of that year's top 100 women's players were at a club in that league. "
        f"The WSL went from {wsl0} in {first} to {wsl1} in {last}. The NWSL peaked at {nwsl_peak} in "
        f"{nwsl_peak_year} and had {nwsl1} in {last}.",
        "Rankings for 2018&ndash;2025 are the Guardian's annual top 100; 2016&ndash;2017 are from The Offside "
        "Rule, which ran the list before the Guardian. A player counts for the club listed with her ranking. "
        "\"Other leagues\" groups every league outside the five in this project.",
    ]
    body = (f"{fig.to_html(full_html=False, include_plotlyjs='cdn', config=PLOT_CONFIG)}\n"
            f"    <div class=\"text\">\n{paragraphs_html(paragraphs)}\n    </div>")
    (OUT_DIR / "t100_by_league.html").write_text(page("Top 100 players by league", body),
                                                 encoding="utf-8")
    return counts


# ----------------------------------------------------------------------------
# Chart 2: clubs with the most top-100 players (year + top-N controls)
# ----------------------------------------------------------------------------
def club_table(year_df):
    """Clubs for one year with competition ranks (ties share a place, next place skipped)."""
    g = (year_df.groupby(["club", "league"])
                .agg(players=("name", "count"),
                     names=("name", lambda s: list(s)))
                .reset_index()
                .sort_values(["players", "club"], ascending=[False, True]))
    g["place"] = g["players"].rank(method="min", ascending=False).astype(int)
    tied = g["place"].duplicated(keep=False)
    g["label"] = [("T" if t else "") + str(p) for p, t in zip(g["place"], tied)]
    return g


def chart_top_clubs(df):
    data = {}
    for year, ydf in df.sort_values("rank").groupby("year"):
        t = club_table(ydf)
        data[int(year)] = [
            dict(club=r.club, league=r.league, players=int(r.players),
                 place=int(r.place), label=r.label, names=r.names)
            for r in t.itertuples()
        ]
    years = sorted(data)
    latest = years[-1]
    t_latest = club_table(df[df.year == latest])
    top4 = t_latest.head(4)
    top4_text = ", ".join(f"{r.club} ({r.players})" for r in top4.itertuples())

    controls = f"""
    <h2 class="chart-title">Clubs with the most top-100 players</h2>
    <div class="controls">
      <label for="yearSelect">Year</label>
      <select id="yearSelect">
        {''.join(f'<option value="{y}"{" selected" if y == latest else ""}>{y}</option>' for y in years)}
      </select>
      <span class="sep">Show</span>
      <div class="seg" role="group" aria-label="Number of clubs">
        <button type="button" data-n="2">Top 2</button>
        <button type="button" data-n="5">Top 5</button>
        <button type="button" data-n="10" class="active">Top 10</button>
        <button type="button" data-n="all">All</button>
      </div>
    </div>
    <p id="note" class="chart-note"></p>
    <div id="chart"></div>"""

    paragraphs = [
        f"In {latest}, {top4_text} held {int(top4.players.sum())} of the world's top 100 players between "
        "them. Hover over a bar to see the players.",
        "Clubs are ranked by how many top-100 players they have. Tied clubs share a place (shown as T) and "
        "the next place is skipped, so two clubs tied 10th means the next club is 12th. A \"Top\" view shows "
        f"every club placed at that rank or better, so ties can show extra clubs. \"All\" shows clubs placed "
        f"{ALL_VIEW_CLUBS}th or better and groups the rest as Other.",
        "Club is the club listed with the ranking. Players at a US college are grouped as University (NCAA).",
    ]

    script = f"""
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
  <script>
  (function () {{
    const DATA = {json.dumps(data, ensure_ascii=False)};
    const ALL_VIEW = {ALL_VIEW_CLUBS};
    const COLORS = {{ bar: "{WOMEN}", other: "#a8a8a8", outline: "{GOLD}" }};
    const yearSel = document.getElementById("yearSelect");
    const buttons = document.querySelectorAll(".seg button");
    const note = document.getElementById("note");
    let n = "10";

    function rows(year, n) {{
      const clubs = DATA[year];
      if (n === "all") {{
        const shown = clubs.filter(c => c.place <= ALL_VIEW);
        const rest = clubs.filter(c => c.place > ALL_VIEW);
        if (rest.length) {{
          shown.push({{ club: "Other (" + rest.length + " clubs)", league: "", label: "",
                       players: rest.reduce((s, c) => s + c.players, 0), names: [], other: true }});
        }}
        return shown;
      }}
      return clubs.filter(c => c.place <= Number(n));
    }}

    function draw() {{
      const year = yearSel.value;
      const r = rows(year, n);
      const shownClubs = r.filter(c => !c.other).length;
      note.textContent = (n !== "all" && shownClubs > Number(n))
        ? "A tie at the cut-off shows " + shownClubs + " clubs."
        : "";
      const labels = r.map(c => c.other ? c.club : c.label + ". " + c.club);
      const hover = r.map(c => c.other
        ? "<b>" + c.club + "</b><br>" + c.players + " players"
        : "<b>" + c.club + "</b> (" + c.league + ")<br>" + c.players + " of the top 100<br>" +
          c.names.join("<br>"));
      const trace = {{
        type: "bar", orientation: "h",
        x: r.map(c => c.players), y: labels,
        text: r.map(c => c.players), textposition: "outside", cliponaxis: false,
        marker: {{ color: r.map(c => c.other ? COLORS.other : COLORS.bar),
                  line: {{ color: COLORS.outline, width: 1.5 }} }},
        hovertext: hover, hoverinfo: "text",
      }};
      const height = Math.max(260, 90 + r.length * 34);
      const layout = {{
        font: {{ family: "{FONT}", size: 15, color: "{TEXT}" }},
        paper_bgcolor: "{PAGE_BG}", plot_bgcolor: "{PLOT_BG}",
        height: height, margin: {{ t: 20, r: 40, b: 50, l: 10 }},
        xaxis: {{ title: "Players in the top 100", gridcolor: "{GRID}", rangemode: "tozero",
                 fixedrange: true, dtick: 2 }},
        yaxis: {{ autorange: "reversed", automargin: true, fixedrange: true }},
        hoverlabel: {{ font: {{ family: "{FONT}" }}, bgcolor: "white", bordercolor: "{GOLD}" }},
        bargap: 0.25, dragmode: false,
      }};
      Plotly.react("chart", [trace], layout, {json.dumps(PLOT_CONFIG)});
    }}

    yearSel.addEventListener("change", draw);
    buttons.forEach(b => b.addEventListener("click", () => {{
      buttons.forEach(x => x.classList.remove("active"));
      b.classList.add("active");
      n = b.dataset.n;
      draw();
    }}));
    draw();
  }})();
  </script>"""

    extra_head = f"""  <style>
    .chart-title {{ font-size: 1.4rem; margin: 8px 0 12px; }}
    .controls {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px; color: {TEXT}; }}
    .controls select {{ font-family: {FONT}; font-size: 1rem; padding: 4px 8px;
                        border: 2px solid {WOMEN}; background: white; }}
    .controls .sep {{ margin-left: 12px; }}
    .seg button {{ font-family: {FONT}; font-size: 1rem; padding: 5px 12px; cursor: pointer;
                   background: white; color: {TEXT}; border: 2px solid {WOMEN}; margin-right: -2px; }}
    .seg button.active {{ background: {WOMEN}; color: white; font-weight: bold; }}
    .chart-note {{ color: {TEXT}; font-style: italic; min-height: 1.4em; margin: 8px 0 0; }}
  </style>"""

    body = (f"{controls}\n    <div class=\"text\">\n{paragraphs_html(paragraphs)}\n    </div>\n{script}")
    (OUT_DIR / "t100_top_clubs.html").write_text(
        page("Clubs with the most top-100 players", body, extra_head), encoding="utf-8")
    return data


def main():
    df = pd.read_csv(DATA_FILE)
    counts = chart_by_league(df)
    chart_top_clubs(df)
    print("Top-100 players by league:")
    print(counts.to_string())
    print(f"Saved charts to {OUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
