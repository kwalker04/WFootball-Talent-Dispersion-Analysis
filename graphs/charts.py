"""
Talent Dispersion: goal-difference charts
-----------------------------------------
Builds the two interactive charts for the site, plus static PNG views for the PDF.

    graphs/gd_gap.html            best-minus-worst gap in goal difference per game,
                                   women's vs men's league. Buttons switch between
                                   full men's leagues and men's leagues cut to the
                                   women's league size.
    graphs/gd_by_position.html    goal difference per game by finishing position,
                                   women's vs men's league cut to the same size.
    graphs/gd_gap_full.png, graphs/gd_gap_cut.png, graphs/gd_by_position.png

How the men's leagues are cut
    For each season, the men's league keeps its top N teams from the final table,
    where N is the number of teams in that season's women's league. Goal difference
    is then recalculated using only the games those N teams played against each other
    (a "mini-league"), so results against the teams that were cut don't count.
    MLS match results aren't in the dataset, so for MLS the cut uses the top N
    teams' full-season goal difference instead.

Input (keep the repo's folder structure):
    data/team_seasons.csv
    data/matches_men_europe.csv   (made by build_match_data.py)

Run:
    pip install pandas numpy plotly kaleido
    python make_charts.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

TEAMS_FILE = Path("data/team_seasons.csv")
MATCHES_FILE = Path("data/matches_men_europe.csv")
OUT_DIR = Path("graphs")

# Women's league -> men's league in the same country.
PAIRS = {
    "England": ("WSL", "Premier League"),
    "Spain": ("Liga F", "La Liga"),
    "France": ("Première Ligue", "Ligue 1"),
    "Germany": ("Frauen-Bundesliga", "Bundesliga"),
    "USA": ("NWSL", "MLS"),
}
EUROPE = ["England", "Spain", "France", "Germany"]

# Arsenal palette.
WOMEN = "#ce0041"   # Arsenal red
MEN = "#113476"     # Arsenal navy
GOLD = "#99824c"    # markers / outlines
TEXT = "#000000"
PAGE_BG = "#F2F0EF"
PLOT_BG = "#fefefe"
GRID = "#e3dfdc"
FONT = "Times New Roman, Times, serif"

PLOT_CONFIG = {"modeBarButtons": [["toImage"]], "displaylogo": False}


# ----------------------------------------------------------------------------
# Data preparation
# ----------------------------------------------------------------------------
def season_key(season):
    """'2023-24' and '2023' both map to '2023', so European and US seasons line up."""
    return str(season)[:4]


def final_order(table):
    """Sort a league table into final order: points per game, then GD per game."""
    table = table.assign(ppg=table["Pts"] / table["P"])
    return table.sort_values(["ppg", "gd_per_game"], ascending=False)


def mini_league(matches, teams):
    """Table built only from games between the given teams, in final order.
    Returns each team's goal difference per game."""
    teams = set(teams)
    games = matches[matches["home_team"].isin(teams) & matches["away_team"].isin(teams)]
    stats = {t: {"P": 0, "Pts": 0, "GF": 0, "GA": 0} for t in teams}
    for g in games.itertuples():
        for team, gf, ga in ((g.home_team, g.home_goals, g.away_goals),
                             (g.away_team, g.away_goals, g.home_goals)):
            s = stats[team]
            s["P"] += 1
            s["GF"] += gf
            s["GA"] += ga
            s["Pts"] += 3 if gf > ga else 1 if gf == ga else 0
    missing = [t for t, s in stats.items() if s["P"] == 0]
    if missing:
        raise ValueError(f"No head-to-head games found for: {missing}")
    table = pd.DataFrame(stats).T.astype(float)
    table["gd_per_game"] = (table["GF"] - table["GA"]) / table["P"]
    return final_order(table)["gd_per_game"].to_numpy()


def build_seasons(teams, matches):
    """For each country and each season both leagues have: the women's league,
    the full men's league and the cut men's league, as GD per game in final order."""
    teams = teams.assign(key=teams["season"].map(season_key))
    seasons = {}
    for country, (women, men) in PAIRS.items():
        w_all = teams[teams["league"] == women]
        m_all = teams[teams["league"] == men]
        rows = []
        for key in sorted(set(w_all["key"]) & set(m_all["key"])):
            w = final_order(w_all[w_all["key"] == key])
            m = final_order(m_all[m_all["key"] == key])
            n = len(w)
            top_n = m.head(n)
            season_matches = matches[(matches["league"] == men) &
                                     (matches["season"] == m["season"].iloc[0])]
            if len(season_matches):
                cut = mini_league(season_matches, top_n["team"])
            else:  # MLS: no match results, use full-season GD of the top N
                cut = top_n["gd_per_game"].to_numpy()
            rows.append({
                "season": key,
                "n": n,
                "women": w["gd_per_game"].to_numpy(),
                "men_full": m["gd_per_game"].to_numpy(),
                "men_cut": cut,
            })
        seasons[country] = rows
    return seasons


def average_gap(rows, field):
    """Average of (1st-place team's GD per game - last-place team's)."""
    return float(np.mean([r[field][0] - r[field][-1] for r in rows]))


# ----------------------------------------------------------------------------
# Shared styling
# ----------------------------------------------------------------------------
def base_layout(fig, title, height):
    fig.update_layout(
        title=dict(text=title, x=0.01, font=dict(size=22, color=TEXT)),
        font=dict(family=FONT, size=15, color=TEXT),
        paper_bgcolor=PAGE_BG,
        plot_bgcolor=PLOT_BG,
        height=height,
        hoverlabel=dict(font_family=FONT, bgcolor="white", bordercolor=GOLD),
        legend=dict(orientation="h", x=0, y=-0.18, font=dict(size=15)),
        dragmode=False,
    )
    fig.update_xaxes(showline=True, linecolor="#888888", fixedrange=True)
    fig.update_yaxes(showline=True, linecolor="#888888", gridcolor=GRID,
                     zerolinecolor="#bbbbbb", fixedrange=True)


def write_page(fig, path, page_title, paragraphs):
    """Save the chart as a standalone HTML page with explanatory text below it."""
    chart = fig.to_html(full_html=False, include_plotlyjs="cdn", config=PLOT_CONFIG)
    text = "\n".join(f"    <p>{p}</p>" for p in paragraphs)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title}</title>
  <style>
    body {{ margin: 0; background: {PAGE_BG}; color: {TEXT};
            font-family: "Times New Roman", Times, serif; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 16px 24px 32px; }}
    .text {{ max-width: 900px; font-size: 18px; line-height: 1.6; }}
    .text p {{ margin: 0 0 1em; }}
  </style>
</head>
<body>
  <div class="wrap">
{chart}
    <div class="text">
{text}
    </div>
  </div>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


# ----------------------------------------------------------------------------
# Chart 1: best-minus-worst gap, full vs cut men's leagues
# ----------------------------------------------------------------------------
def chart_gap(seasons):
    countries = list(PAIRS)
    labels = [f"{c}<br>{PAIRS[c][0]} vs {PAIRS[c][1]}" for c in countries]
    women = [average_gap(seasons[c], "women") for c in countries]
    men_full = [average_gap(seasons[c], "men_full") for c in countries]
    men_cut = [average_gap(seasons[c], "men_cut") for c in countries]
    n_seasons = [len(seasons[c]) for c in countries]

    bar_style = dict(line=dict(color=GOLD, width=2.5))
    hover = ("<b>%{customdata[0]}</b><br>%{fullData.name}: %{y:.2f} goals per game"
             "<br>Seasons averaged: %{customdata[1]}<extra></extra>")
    custom = list(zip(countries, n_seasons))

    fig = go.Figure()
    fig.add_bar(x=labels, y=women, name="Women's league", marker=dict(color=WOMEN, **bar_style),
                text=[f"{v:.1f}" for v in women], textposition="outside",
                customdata=custom, hovertemplate=hover)
    fig.add_bar(x=labels, y=men_full, name="Men's league (all teams)",
                marker=dict(color=MEN, **bar_style),
                text=[f"{v:.1f}" for v in men_full], textposition="outside",
                customdata=custom, hovertemplate=hover)
    fig.add_bar(x=labels, y=men_cut, name="Men's league (cut to women's size)",
                marker=dict(color=MEN, **bar_style), visible=False,
                text=[f"{v:.1f}" for v in men_cut], textposition="outside",
                customdata=custom, hovertemplate=hover)

    base_layout(fig, "Gap between the best and worst team, in goal difference per game", 620)
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.06,
                      margin=dict(t=130, r=30, b=110, l=80))
    fig.update_traces(textfont=dict(color=TEXT, size=15), cliponaxis=False)
    fig.update_yaxes(title_text="Goals per game: 1st-place team minus last-place team",
                     range=[0, max(women) * 1.15])

    fig.layout.updatemenus = [dict(
        type="buttons", direction="right", active=0, showactive=True,
        x=0.01, xanchor="left", y=1.13, yanchor="top",
        bgcolor="white", bordercolor=WOMEN, borderwidth=1,
        font=dict(family=FONT, size=15, color=TEXT),
        buttons=[
            dict(label="Full men's leagues", method="update",
                 args=[{"visible": [True, True, False]}]),
            dict(label="Men's leagues cut to women's size", method="update",
                 args=[{"visible": [True, False, True]}]),
        ],
    )]

    w_eu = np.mean([women[countries.index(c)] for c in EUROPE])
    full_eu = np.mean([men_full[countries.index(c)] for c in EUROPE])
    cut_eu = np.mean([men_cut[countries.index(c)] for c in EUROPE])
    paragraphs = [
        "Both views tell the same story: in every European country, the gap between the best "
        "and worst women's team is far larger than in the men's league, which already points to "
        "talent in women's football being concentrated in a few clubs rather than spread widely.",
        f"Cutting each men's league to the size of its women's league makes the disparity even "
        f"clearer. A full men's league has six to eight extra teams at the bottom, and the teams "
        f"above them pile up goal difference in those extra games against easier opponents, which "
        f"stretches the men's gap and makes it look closer to the women's than a like-for-like "
        f"comparison would. Once the men's leagues are cut to the same size, with goal difference "
        f"counted only in games among those top teams, the European men's gap falls from about "
        f"{full_eu:.1f} to about {cut_eu:.1f} goals per game, while the women's gap stays at about "
        f"{w_eu:.1f}. The women's gap goes from roughly {w_eu / full_eu:.1f} times the men's to "
        f"about {w_eu / cut_eu:.1f} times.",
        "Note: MLS match results aren't in the dataset, so the cut MLS figure uses the top teams' "
        "full-season goal difference rather than games among themselves.",
    ]
    write_page(fig, OUT_DIR / "gd_gap.html", "Best vs worst team gap", paragraphs)

    # Static views for the PDF (no buttons).
    fig.update_layout(updatemenus=[], margin=dict(t=80))
    fig.write_image(OUT_DIR / "gd_gap_full.png", width=1200, height=620, scale=2)
    fig.data[1].visible = False
    fig.data[2].visible = True
    fig.update_layout(title_text="Gap between the best and worst team, men's leagues cut "
                                 "to women's league size")
    fig.write_image(OUT_DIR / "gd_gap_cut.png", width=1200, height=620, scale=2)

    print("Gap (goals per game): women / men full / men cut")
    for c, w, f, k in zip(countries, women, men_full, men_cut):
        print(f"  {c:8} {w:.2f} / {f:.2f} / {k:.2f}")
    print(f"  Europe   {w_eu:.2f} / {full_eu:.2f} / {cut_eu:.2f}")


# ----------------------------------------------------------------------------
# Chart 2: GD per game by finishing position, men's leagues cut to the same size
# ----------------------------------------------------------------------------
def chart_by_position(seasons):
    countries = list(PAIRS)
    fig = make_subplots(rows=1, cols=5, shared_yaxes=True, horizontal_spacing=0.025,
                        subplot_titles=[f"{c}<br><span style='font-size:13px'>"
                                        f"{PAIRS[c][0]} vs {PAIRS[c][1]}</span>"
                                        for c in countries])

    for i, country in enumerate(countries, start=1):
        rows = seasons[country]
        # League size can vary between seasons, so each season is placed on a common
        # set of positions (the median league size) before averaging.
        size = int(np.median([r["n"] for r in rows]))
        grid = np.linspace(0, 1, size)
        interp = lambda gd: np.interp(grid, np.linspace(0, 1, len(gd)), gd)
        women = np.mean([interp(r["women"]) for r in rows], axis=0)
        men = np.mean([interp(r["men_cut"]) for r in rows], axis=0)
        positions = np.arange(1, size + 1)

        for values, name, color in ((women, "Women's league", WOMEN),
                                    (men, "Men's league (cut to same size)", MEN)):
            fig.add_scatter(
                x=positions, y=values, name=name, mode="lines+markers",
                line=dict(color=color, width=3),
                marker=dict(color=GOLD, size=9, line=dict(color=color, width=1.5)),
                legendgroup=name, showlegend=(i == 1),
                hovertemplate=f"<b>{country}</b><br>{name}<br>Position %{{x}}"
                              "<br>GD per game: %{y:+.2f}<extra></extra>",
                row=1, col=i,
            )
        fig.update_xaxes(title_text="Finishing position", tickvals=[1, (size + 1) // 2, size],
                         row=1, col=i)

    base_layout(fig, "Goal difference per game by finishing position", 560)
    fig.update_layout(margin=dict(t=130, r=20, b=110, l=80))
    fig.update_yaxes(title_text="Goal difference per game", row=1, col=1)
    fig.update_annotations(font=dict(size=16, color=TEXT), yshift=6)

    paragraphs = [
        "Each line is the average goal difference per game for the team finishing in each "
        "position, averaged over 2018&ndash;19 to 2024&ndash;25 (USA: 2018&ndash;2025, no 2020). "
        "The women's lines start much higher at the top and finish much lower at the bottom: a few "
        "dominant clubs and a few heavily outmatched ones.",
        "The men's leagues are cut to the same number of teams as the women's league in each "
        "season, and their goal difference is recalculated using only the games those teams played "
        "against each other. This chart compares the leagues position by position, so equal league "
        "sizes give a one-to-one comparison. MLS match results aren't in the dataset, so MLS uses "
        "the top teams' full-season goal difference.",
    ]
    write_page(fig, OUT_DIR / "gd_by_position.html", "Goal difference by finishing position",
               paragraphs)
    fig.write_image(OUT_DIR / "gd_by_position.png", width=1500, height=560, scale=2)


def main():
    teams = pd.read_csv(TEAMS_FILE)
    matches = pd.read_csv(MATCHES_FILE)
    OUT_DIR.mkdir(exist_ok=True)
    seasons = build_seasons(teams, matches)

    chart_gap(seasons)
    chart_by_position(seasons)
    print(f"Saved charts to {OUT_DIR}/")


if __name__ == "__main__":
    main()
