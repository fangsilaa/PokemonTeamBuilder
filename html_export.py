from __future__ import annotations
import plotly.graph_objects as go
from constants import TYPE_COLORS, ALL_TYPES, STAT_ORDER, STAT_LABELS
from type_chart import get_defensive_profile, build_type_chart

TYPE_ABBR = {
    "normal": "Nor", "fire": "Fir", "water": "Wat", "electric": "Ele",
    "grass": "Grs", "ice": "Ice", "fighting": "Fig", "poison": "Psn",
    "ground": "Gnd", "flying": "Fly", "psychic": "Psy", "bug": "Bug",
    "rock": "Roc", "ghost": "Gho", "dragon": "Dra", "dark": "Drk",
    "steel": "Stl", "fairy": "Fai",
}

MULT_STYLE = {
    0.0:  ("background:#555;color:#fff", "0×"),
    0.25: ("background:#2a6b2a;color:#fff", "¼×"),
    0.5:  ("background:#4a8f4a;color:#fff", "½×"),
    1.0:  ("", ""),
    2.0:  ("background:#b84040;color:#fff", "2×"),
    4.0:  ("background:#8b0000;color:#fff", "4×"),
}

PLOTLY_COLORS = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: #12121c;
    color: #dcdceb;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    padding: 28px 32px;
    max-width: 1400px;
    margin: 0 auto;
}
h1 { color: #636efa; font-size: 1.6em; text-align: center; margin-bottom: 5px; }
.subtitle { text-align: center; color: #9696af; font-size: 0.9em; margin-bottom: 20px; }
.divider { height: 2px; background: #636efa; margin: 0 0 24px; border-radius: 1px; }

.section-header {
    background: #1e1e2e;
    border-left: 4px solid #636efa;
    padding: 8px 14px;
    font-weight: 700;
    font-size: 0.82em;
    letter-spacing: 0.06em;
    color: #636efa;
    margin: 24px 0 12px;
    border-radius: 0 4px 4px 0;
}

/* Team grid */
.team-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 10px;
}
.pokemon-card {
    background: #1e1e2e;
    border: 1px solid #3c3c5a;
    border-radius: 8px;
    padding: 10px 8px 8px;
    text-align: center;
}
.pokemon-card img { width: 80px; height: 80px; object-fit: contain; }
.pokemon-name { font-weight: 700; font-size: 0.88em; margin: 6px 0 4px; }
.pokemon-bst { font-size: 0.72em; color: #9696af; margin-top: 4px; }

/* Type badges */
.type-badge {
    display: inline-block;
    color: #fff;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.72em;
    margin: 1px;
}

/* Heatmap */
.heatmap-wrap { overflow-x: auto; }
.heatmap { border-collapse: separate; border-spacing: 2px; width: 100%; }
.heatmap th { text-align: center; font-size: 0.7em; padding: 4px 2px; border-radius: 3px 3px 0 0; color: #fff; white-space: nowrap; }
.heatmap td { text-align: center; font-size: 0.74em; padding: 5px 2px; border-radius: 3px; font-weight: 600; }
.heatmap .name-cell {
    text-align: left;
    padding: 5px 10px;
    font-weight: 700;
    font-size: 0.8em;
    white-space: nowrap;
    border-radius: 4px;
    color: #fff;
    min-width: 90px;
}

/* Radar */
.radar-wrap { width: 100%; }

/* Type profile */
.type-profile { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.profile-label { font-size: 0.78em; font-weight: 700; margin-bottom: 7px; }
.profile-sublabel { font-size: 0.72em; opacity: 0.55; margin: 6px 0 3px; }

/* Type summary row */
.type-summary { display: flex; gap: 40px; flex-wrap: wrap; }
.type-summary-item { }
.type-summary-label { font-size: 0.78em; font-weight: 700; margin-bottom: 6px; }

/* Movesets */
.moveset-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
    gap: 12px;
}
.moveset-card {
    background: #1e1e2e;
    border: 1px solid #3c3c5a;
    border-radius: 8px;
    overflow: hidden;
}
.moveset-header {
    padding: 7px 10px;
    font-weight: 700;
    font-size: 0.85em;
    color: #fff;
    text-align: center;
}
.move-row {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 5px 9px;
    border-top: 1px solid #2a2a40;
    font-size: 0.78em;
}
.move-type { display: inline-block; color: #fff; padding: 1px 6px; border-radius: 3px; font-size: 0.82em; flex-shrink: 0; }
.move-name { flex: 1; }
.move-power { color: #9696af; font-size: 0.85em; }

/* Recommendations */
.rec-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
    gap: 12px;
}
.rec-card {
    background: #1e1e2e;
    border: 1px solid #3c3c5a;
    border-radius: 8px;
    overflow: hidden;
    text-align: center;
    padding-bottom: 12px;
}
.rec-sprite { width: 72px; height: 72px; object-fit: contain; margin-top: 10px; }
.rec-name { font-weight: 700; font-size: 0.88em; margin: 6px 0 3px; }
.rec-bst { font-size: 0.72em; color: #9696af; margin-bottom: 6px; }
.rec-replace {
    display: inline-block;
    font-size: 0.72em;
    background: rgba(232,112,112,0.15);
    color: #e87070;
    padding: 2px 8px;
    border-radius: 4px;
    margin-bottom: 7px;
}
.rec-sublabel { font-size: 0.7em; color: #9696af; margin: 5px 0 3px; }
"""


def _darken_hex(hex_color: str, factor: float = 0.65) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgb({int(r*factor)},{int(g*factor)},{int(b*factor)})"


def _type_badge(type_name: str, faded: bool = False) -> str:
    color = TYPE_COLORS.get(type_name, "#888")
    style = f"background:{color};" + ("opacity:0.4;" if faded else "")
    return f'<span class="type-badge" style="{style}">{type_name.capitalize()}</span>'


def _heatmap_html(team: list[dict]) -> str:
    header_cells = '<th style="min-width:90px"></th>'
    for t in ALL_TYPES:
        color = TYPE_COLORS.get(t, "#888")
        header_cells += f'<th style="background:{color}">{TYPE_ABBR[t]}</th>'

    rows = ""
    for i, pokemon in enumerate(team):
        types = [slot["type"]["name"] for slot in pokemon["types"]]
        profile = get_defensive_profile(types)
        color = TYPE_COLORS.get(types[0], "#888")
        bg = "#1e1e2e" if i % 2 == 0 else "#28283e"

        cells = f'<td class="name-cell" style="background:{_darken_hex(color)}">{pokemon["name"].capitalize()}</td>'
        for t in ALL_TYPES:
            val = profile[t]
            style, label = MULT_STYLE.get(val, ("", ""))
            cells += f'<td style="background:{bg};{style}">{label}</td>'
        rows += f"<tr>{cells}</tr>"

    return (
        '<div class="heatmap-wrap">'
        '<table class="heatmap">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table></div>"
    )


def _radar_html(team: list[dict]) -> str:
    fig = go.Figure()
    stat_names = [STAT_LABELS[s] for s in STAT_ORDER]
    for i, pokemon in enumerate(team):
        stat_map = {s["stat"]["name"]: s["base_stat"] for s in pokemon["stats"]}
        values = [stat_map.get(s, 0) for s in STAT_ORDER]
        values_norm = [v / 255 * 100 for v in values]
        fig.add_trace(go.Scatterpolar(
            r=values_norm + [values_norm[0]],
            theta=stat_names + [stat_names[0]],
            fill="toself",
            name=pokemon["name"].capitalize(),
            line=dict(color=PLOTLY_COLORS[i % len(PLOTLY_COLORS)]),
            opacity=0.6,
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], color="#9696af"),
            angularaxis=dict(color="#9696af"),
            bgcolor="#1e1e2e",
        ),
        paper_bgcolor="#12121c",
        font=dict(color="#dcdceb"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=380,
        margin=dict(l=60, r=60, t=20, b=70),
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def _type_profile_html(team: list[dict], analysis: dict) -> str:
    chart = build_type_chart()
    weakness_counts = analysis.get("weakness_counts", {})

    weak_types = sorted([(t, c) for t, c in weakness_counts.items() if c > 0], key=lambda x: -x[1])

    def weak_badge(type_name: str, count: int) -> str:
        color = TYPE_COLORS.get(type_name, "#888")
        border = "3px solid #fff" if count >= 3 else "none"
        return (
            f'<span class="type-badge" style="background:{color};border:{border};margin:2px">'
            f'{type_name.capitalize()} <sup>{count}</sup></span>'
        )

    weak_html = "".join(weak_badge(t, c) for t, c in weak_types) or '<span style="opacity:0.4">None</span>'

    stab_types = {slot["type"]["name"] for p in team for slot in p["types"]}
    covered = {d for st in stab_types for d, m in chart[st].items() if m >= 2.0}
    uncovered = [t for t in ALL_TYPES if t not in covered]

    cov_html = "".join(_type_badge(t) for t in sorted(covered)) or '<span style="opacity:0.4">None</span>'
    miss_html = "".join(_type_badge(t, faded=True) for t in uncovered) or '<span style="opacity:0.4">Full coverage!</span>'

    return f"""
    <div class="type-profile">
        <div>
            <div class="profile-label" style="color:#e87070">Defensive Weaknesses
                <span style="font-weight:400;font-size:0.85em;opacity:0.55">&nbsp;white border = 3+ members weak</span>
            </div>
            <div>{weak_html}</div>
        </div>
        <div>
            <div class="profile-label" style="color:#00cc96">Offensive STAB Coverage</div>
            <div style="margin-bottom:8px">{cov_html}</div>
            <div class="profile-sublabel">Not covered</div>
            <div>{miss_html}</div>
        </div>
    </div>"""


def _movesets_html(team: list[dict], movesets: dict) -> str:
    cards = ""
    for pokemon in team:
        name = pokemon["name"]
        moves = movesets.get(name, [])
        if not moves:
            continue
        color = TYPE_COLORS.get(pokemon["types"][0]["type"]["name"], "#888")

        move_rows = ""
        for move in moves:
            mcolor = TYPE_COLORS.get(move["type"], "#888")
            pwr = str(move["power"]) if move["power"] else "-"
            cat_icon = {"physical": "&#9876;", "special": "&#10022;", "status": "&#9670;"}.get(move["category"], "")
            move_rows += (
                f'<div class="move-row">'
                f'<span class="move-type" style="background:{mcolor}">{move["type"][:3].capitalize()}</span>'
                f'<span class="move-name">{cat_icon} {move["name"].replace("-", " ").title()}</span>'
                f'<span class="move-power">{pwr}</span>'
                f'</div>'
            )

        cards += (
            f'<div class="moveset-card">'
            f'<div class="moveset-header" style="background:{_darken_hex(color)}">{name.capitalize()}</div>'
            f'{move_rows}'
            f'</div>'
        )

    return f'<div class="moveset-grid">{cards}</div>'


def _recommendations_html(recommendations: list[dict]) -> str:
    if not recommendations:
        return '<p style="opacity:0.5;font-size:0.85em">No clear recommendations — your team looks well-balanced!</p>'

    cards = ""
    for rec in recommendations:
        pdata = rec["pokemon"]
        static = pdata.get("sprites", {}).get("front_default", "")
        showdown = f"https://play.pokemonshowdown.com/sprites/ani/{pdata['name']}.gif"

        types_html = "".join(_type_badge(slot["type"]["name"]) for slot in pdata["types"])

        replace = rec.get("replace", "")
        replace_html = f'<div class="rec-replace">Replace {replace.capitalize()}</div>' if replace else ""

        resists = rec.get("resists", [])
        resists_html = (
            f'<div class="rec-sublabel">Resists</div>'
            f'<div>{"".join(_type_badge(t) for t in resists)}</div>'
        ) if resists else ""

        covers = rec.get("covers", [])
        covers_html = (
            f'<div class="rec-sublabel">Covers</div>'
            f'<div>{"".join(_type_badge(t) for t in covers)}</div>'
        ) if covers else ""

        cards += (
            f'<div class="rec-card">'
            f'<img class="rec-sprite" src="{showdown}" onerror="this.src=\'{static}\'" alt="{pdata["name"]}">'
            f'<div class="rec-name">{pdata["name"].capitalize()}</div>'
            f'<div>{types_html}</div>'
            f'<div class="rec-bst">BST {rec["bst"]}</div>'
            f'{replace_html}'
            f'{resists_html}'
            f'{covers_html}'
            f'</div>'
        )

    return f'<div class="rec-grid">{cards}</div>'


def generate_team_html(
    team: list[dict],
    analysis: dict,
    stat_overrides: dict,
    movesets: dict[str, list[dict]],
    recommendations: list[dict] | None = None,
    team_name: str | None = None,
) -> str:
    subtitle = team_name if team_name else "  ·  ".join(p["name"].capitalize() for p in team)

    # Team overview cards
    team_cards = ""
    for pokemon in team:
        api_stats = {s["stat"]["name"]: s["base_stat"] for s in pokemon["stats"]}
        overrides = stat_overrides.get(pokemon["name"], {})
        bst = sum(overrides.get(s, api_stats.get(s, 0)) for s in STAT_ORDER) if overrides else sum(api_stats.values())
        bst_label = f"BST {bst}" + (" (custom)" if overrides else "")

        types_html = "".join(_type_badge(slot["type"]["name"]) for slot in pokemon["types"])
        static = pokemon.get("sprites", {}).get("front_default", "")
        showdown = f"https://play.pokemonshowdown.com/sprites/ani/{pokemon['name']}.gif"

        team_cards += (
            f'<div class="pokemon-card">'
            f'<img src="{showdown}" onerror="this.src=\'{static}\'" alt="{pokemon["name"]}">'
            f'<div class="pokemon-name">{pokemon["name"].capitalize()}</div>'
            f'<div>{types_html}</div>'
            f'<div class="pokemon-bst">{bst_label}</div>'
            f'</div>'
        )

    critical = analysis.get("critical_weaknesses", [])
    coverage = analysis.get("offensive_coverage", [])
    critical_html = "".join(_type_badge(t) for t in critical) or '<span style="opacity:0.4">None</span>'
    coverage_html = "".join(_type_badge(t) for t in coverage) or '<span style="opacity:0.4">None</span>'

    movesets_section = (
        '<div class="section-header">RECOMMENDED MOVESETS</div>'
        + _movesets_html(team, movesets)
    ) if movesets else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pokemon Team Report</title>
<style>{CSS}</style>
</head>
<body>

<h1>POKEMON TEAM REPORT</h1>
<div class="subtitle">{subtitle}</div>
<div class="divider"></div>

<div class="section-header">TEAM OVERVIEW</div>
<div class="team-grid">{team_cards}</div>

<div class="section-header">TYPE WEAKNESS HEATMAP</div>
{_heatmap_html(team)}

<div class="section-header">STAT RADAR</div>
<div class="radar-wrap">{_radar_html(team)}</div>

<div class="section-header">TYPE STRENGTHS &amp; WEAKNESSES</div>
{_type_profile_html(team, analysis)}

<div class="section-header">TYPE SUMMARY</div>
<div class="type-summary">
    <div class="type-summary-item">
        <div class="type-summary-label" style="color:#e87070">Critical Weaknesses</div>
        <div>{critical_html}</div>
    </div>
    <div class="type-summary-item">
        <div class="type-summary-label" style="color:#00cc96">Offensive Coverage</div>
        <div>{coverage_html}</div>
    </div>
</div>

{movesets_section}

<div class="section-header">RECOMMENDED REPLACEMENTS</div>
{_recommendations_html(recommendations or [])}

</body>
</html>"""
