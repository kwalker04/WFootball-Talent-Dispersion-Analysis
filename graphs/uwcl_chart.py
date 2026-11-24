"""
Talent Dispersion: who gets anywhere in the UEFA Women's Champions League?

Makes one interactive chart page from data/uwcl_knockout_stages_2016_2026.csv:

  graphs/uwcl_stages.html  How many times each club reached the quarter-finals, semi-finals,
                           final, or won the competition, 2016-17 to 2025-26.

Controls on the page:
  - Stage buttons: Quarter-finals (default), Semi-finals, Final, Winner.
  - View: "Grouped" (top 8 clubs vs Other) or "By club" (one bar per top club, plus Other).
    "Other" always shows, even at 0; hovering over it lists the clubs inside it.

The eight top clubs are the top and secondary teams in the "Top teams by league" table:
Barcelona, Lyon, PSG, Chelsea, Arsenal, Manchester City, Wolfsburg, Bayern Munich.

Input (keep the repo's folder structure):
    data/uwcl_knockout_stages_2016_2026.csv
    columns: year, quarterfinalists, semifinalists, finalists, winners
    (each cell is a comma-separated list of clubs)

Run from anywhere:
    pip install pandas
    python graphs/uwcl_chart.py
"""

import json
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent   # repo root (this file is in graphs/)
DATA_FILE = ROOT / "data" / "uwcl_knockout_stages_2016_2026.csv"
OUT_FILE = ROOT / "graphs" / "uwcl_stages.html"

# Same look as the other charts
WOMEN = "#ce0041"
GOLD_OUTLINE = "#99824c"
OTHER_GREY = "#a8a8a8"
TEXT = "#000000"
PAGE_BG = "#F2F0EF"
PLOT_BG = "#fefefe"
GRID = "#e6e6e6"
FONT = "Times New Roman, Times, serif"

# Stage button shading (metallic colours at 70% opacity)
STAGE_BG = {
    "quarterfinalists": "#ffffff",
    "semifinalists": "rgba(205, 127, 50, 0.7)",   # bronze #CD7F32
    "finalists": "rgba(192, 192, 192, 0.7)",      # silver #C0C0C0
    "winners": "rgba(212, 175, 55, 0.7)",         # gold #D4AF37
}
STAGES = [
    ("quarterfinalists", "Quarter-finals", 8),
    ("semifinalists", "Semi-finals", 4),
    ("finalists", "Final", 2),
    ("winners", "Winner", 1),
]

# Same club under different names in the source
NAME_FIXES = {"VfL Wolfsburg": "Wolfsburg", "Paris Saint-Germain": "PSG", "OL Lyonnes": "Lyon"}

TOP_CLUBS = ["Barcelona", "Lyon", "PSG", "Chelsea", "Arsenal", "Manchester City",
             "Wolfsburg", "Bayern Munich"]


def load_counts():
    df = pd.read_csv(DATA_FILE)
    counts, seasons = {}, len(df)
    for col, _, per_season in STAGES:
        c = Counter()
        for year, cell in zip(df["year"], df[col]):
            clubs = [NAME_FIXES.get(x.strip(), x.strip()) for x in str(cell).split(",")]
            if len(clubs) != per_season:
                raise ValueError(f"{year} {col}: expected {per_season} clubs, got {len(clubs)}")
            c.update(clubs)
        counts[col] = c
    return counts, seasons, df["year"].iloc[0], df["year"].iloc[-1]


def main():
    counts, seasons, first, last = load_counts()

    # Fixed club order for every stage: by quarter-final appearances, then name
    qf = counts["quarterfinalists"]
    order = sorted(TOP_CLUBS, key=lambda c: (-qf[c], c))

    data = {}
    for col, label, per_season in STAGES:
        c = counts[col]
        others = sorted(((k, v) for k, v in c.items() if k not in TOP_CLUBS),
                        key=lambda kv: (-kv[1], kv[0]))
        data[col] = {
            "label": label,
            "places": per_season * seasons,
            "clubs": [{"club": k, "n": c[k]} for k in order],
            "other": sum(v for _, v in others),
            "other_list": [f"{k} {v}" for k, v in others],
        }

    semis = data["semifinalists"]
    qf_d = data["quarterfinalists"]
    top_qf = qf_d["places"] - qf_d["other"]
    paragraphs = [
        f"Over the last {seasons} seasons ({first} to {last}), the eight top clubs filled {top_qf} of the "
        f"{qf_d['places']} quarter-final places. From the semi-finals on, nobody else got through: they took "
        f"all {semis['places'] - semis['other']} of {semis['places']} semi-final places, every place in the "
        "final, and every title.",
        "The eight top clubs are the top and secondary teams in the table above: Barcelona, Lyon, PSG, Chelsea, "
        "Arsenal, Manchester City, Wolfsburg and Bayern Munich. Lyon and OL Lyonnes are counted as one club. "
        "Hover over the Other bar to see which clubs it includes.",
    ]
    text = "\n".join(f"      <p>{p}</p>" for p in paragraphs)

    stage_buttons = "\n".join(
        f'        <button type="button" data-stage="{col}" style="background:{STAGE_BG[col]}"'
        f'{" class=\"active\"" if col == "quarterfinalists" else ""}>{label}</button>'
        for col, label, _ in STAGES
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Champions League stages reached | Talent Dispersion</title>
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
    .chart-title {{ font-size: 1.4rem; margin: 8px 0 12px; }}
    .headline {{ color: {TEXT}; font-size: 1.15rem; margin: 14px 0 8px; min-height: 1.5em; }}
    .controls {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px 18px; color: {TEXT}; }}
    .seg {{ display: inline-flex; flex-wrap: wrap; }}
    .seg button {{ font-family: {FONT}; font-size: 1rem; padding: 6px 14px; cursor: pointer;
                   color: {TEXT}; border: 2px solid {WOMEN}; margin-right: -2px; background: white; }}
    .seg button.active {{ font-weight: bold; outline: 3px solid {TEXT}; outline-offset: -5px; }}
    .view button.active {{ background: {WOMEN}; color: white; outline: none; }}
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
    <h2 class="chart-title">Who reaches the late stages of the Champions League, {first} to {last}</h2>
    <div class="controls">
      <span>Stage</span>
      <div class="seg stage" role="group" aria-label="Stage">
{stage_buttons}
      </div>
      <span>View</span>
      <div class="seg view" role="group" aria-label="View">
        <button type="button" data-view="grouped">Grouped</button>
        <button type="button" data-view="club" class="active">By club</button>
      </div>
    </div>
    <p id="headline" class="headline"></p>
    <div id="chart"></div>
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
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
  <script>
  (function () {{
    const DATA = {json.dumps(data, ensure_ascii=False)};
    let stage = "quarterfinalists", view = "club";

    function draw() {{
      const d = DATA[stage];
      const top = d.places - d.other;
      const otherHover = "<b>Other</b>: " + d.other + " of " + d.places + "<br>" +
        (d.other_list.length ? d.other_list.join("<br>") : "No other club reached this stage");
      let labels, values, colors, hover;
      if (view === "grouped") {{
        labels = ["Top 8 clubs", "Other"];
        values = [top, d.other];
        colors = ["{WOMEN}", "{OTHER_GREY}"];
        hover = ["<b>Top 8 clubs</b>: " + top + " of " + d.places + "<br>" +
                 d.clubs.map(c => c.club + " " + c.n).join("<br>"), otherHover];
      }} else {{
        labels = d.clubs.map(c => c.club).concat(["Other"]);
        values = d.clubs.map(c => c.n).concat([d.other]);
        colors = d.clubs.map(() => "{WOMEN}").concat(["{OTHER_GREY}"]);
        hover = d.clubs.map(c => "<b>" + c.club + "</b>: " + c.n + " time" + (c.n === 1 ? "" : "s"))
                 .concat([otherHover]);
      }}
      document.getElementById("headline").textContent =
        d.label + ": the top 8 clubs took " + top + " of " + d.places + " places; every other club combined took " +
        d.other + ".";
      const trace = {{
        type: "bar", orientation: "h", x: values, y: labels,
        text: values.map(String), textposition: "outside", cliponaxis: false,
        marker: {{ color: colors, line: {{ color: "{GOLD_OUTLINE}", width: 1.5 }} }},
        hovertext: hover, hoverinfo: "text",
      }};
      const layout = {{
        font: {{ family: "{FONT}", size: 15, color: "{TEXT}" }},
        paper_bgcolor: "{PAGE_BG}", plot_bgcolor: "{PLOT_BG}",
        height: Math.max(240, 90 + labels.length * 42),
        margin: {{ t: 10, r: 50, b: 50, l: 10 }},
        xaxis: {{ title: "Times reached (" + d.places + " places in total)", gridcolor: "{GRID}",
                 rangemode: "tozero", fixedrange: true }},
        yaxis: {{ autorange: "reversed", automargin: true, fixedrange: true }},
        hoverlabel: {{ font: {{ family: "{FONT}" }}, bgcolor: "white", bordercolor: "{GOLD_OUTLINE}" }},
        bargap: 0.3, dragmode: false,
      }};
      Plotly.react("chart", [trace], layout, {{ displayModeBar: false, responsive: true }});
    }}

    document.querySelectorAll(".stage button").forEach(b => b.addEventListener("click", () => {{
      document.querySelectorAll(".stage button").forEach(x => x.classList.remove("active"));
      b.classList.add("active"); stage = b.dataset.stage; draw();
    }}));
    document.querySelectorAll(".view button").forEach(b => b.addEventListener("click", () => {{
      document.querySelectorAll(".view button").forEach(x => x.classList.remove("active"));
      b.classList.add("active"); view = b.dataset.view; draw();
    }}));
    draw();
  }})();
  </script>
</body>
</html>
"""
    OUT_FILE.write_text(html, encoding="utf-8")
    for col, label, _ in STAGES:
        d = data[col]
        print(f"{label:15s} top 8: {d['places'] - d['other']:3d} / {d['places']:3d}   other: {d['other']}")
    print(f"Saved {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
