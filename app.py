import random
import streamlit as st
import plotly.graph_objects as go
from dotenv import load_dotenv
load_dotenv()

from api import (get_pokemon, get_type, get_move, get_all_pokemon_names,
                 get_smogon_moveset, get_smogon_format_meta,
                 SINGLES_FORMATS, DOUBLES_FORMATS,
                 ALL_SINGLES_FORMATS, ALL_DOUBLES_FORMATS,
                 get_sprite_url)
from team import analyze_team
from advisor import get_team_advice
from type_chart import build_type_chart, get_defensive_profile
from constants import TYPE_COLORS, ALL_TYPES, STAT_ORDER, STAT_LABELS
from pdf_export import generate_team_pdf
from html_export import generate_team_html

st.set_page_config(page_title="Pokémon Team Builder", layout="wide")

st.markdown("""
<style>
/* Prevent layout from compressing below a minimum width — scroll instead */
.stApp { min-width: 960px !important; }
[data-testid="block-container"] {
    padding-top: 0.6rem !important;
    padding-bottom: 0 !important;
    min-width: 940px !important;
}
.stVerticalBlock { gap: 0.25rem !important; }
[data-testid="stForm"] { padding: 0.5rem !important; border-radius: 6px; }
[data-testid="stExpander"] { margin-top: 0.2rem !important; }
h2 { margin: 0 0 0.25rem 0 !important; padding: 0 !important; }
h4 { margin: 0.1rem 0 0.1rem 0 !important; }
.stPlotlyChart { margin-top: 0 !important; }
div[data-testid="stHorizontalBlock"] { gap: 0.4rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ──────────────────────────────────────────────────────
for key, default in [
    ("team", []), ("type_chart", None), ("analysis", {}),
    ("claude_advice", ""), ("prev_team_names", []), ("pending_remove", None),
    ("all_names", None), ("select_key", 0), ("stat_overrides", {}),
    ("moveset_cache", {}), ("rec_cache", []), ("saved_teams", None),
    ("loaded_team_name", None), ("format_mode", "Singles"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.type_chart is None:
    with st.spinner("Loading type chart…"):
        st.session_state.type_chart = build_type_chart()

if st.session_state.all_names is None:
    with st.spinner("Loading Pokémon list…"):
        st.session_state.all_names = get_all_pokemon_names()


def type_badge(type_name: str, faded: bool = False) -> str:
    color = TYPE_COLORS.get(type_name, "#888")
    opacity = "0.45" if faded else "1"
    return (
        f'<span style="background:{color};color:#fff;padding:1px 6px;border-radius:4px;'
        f'font-size:0.75em;margin-right:3px;opacity:{opacity}">{type_name.capitalize()}</span>'
    )


SLOT_HEIGHT = 100


def render_team_slot(pokemon: dict | None, idx: int):
    with st.container(border=True):
        if pokemon is None:
            st.markdown(
                f"<div style='height:{SLOT_HEIGHT}px;display:flex;align-items:center;"
                f"justify-content:center;opacity:0.2;font-size:0.75em'>Slot {idx + 1} — Empty</div>",
                unsafe_allow_html=True,
            )
            return

        api_stats = {s["stat"]["name"]: s["base_stat"] for s in pokemon["stats"]}
        overrides = st.session_state.stat_overrides.get(pokemon["name"], {})
        api_bst = sum(api_stats.values())
        effective_bst = sum(overrides.get(s, api_stats.get(s, 0)) for s in STAT_ORDER) if overrides else api_bst
        bst_display = f"BST {effective_bst} <span style='opacity:0.4;font-size:0.9em'>(custom)</span>" if overrides else f"BST {api_bst}"
        types_html = "".join(type_badge(slot["type"]["name"]) for slot in pokemon["types"])
        sprite_src = get_sprite_url(pokemon)

        st.markdown(
            f"<div style='display:flex;align-items:center;height:{SLOT_HEIGHT}px;gap:6px'>"
            f"  <div style='flex:1;min-width:0'>"
            f"    <div style='font-size:0.85em;font-weight:600;margin-bottom:2px'>{pokemon['name'].capitalize()}</div>"
            f"    <div style='margin-bottom:2px'>{types_html}</div>"
            f"    <div style='font-size:0.72em;opacity:0.55'>{bst_display}</div>"
            f"  </div>"
            f"  <div style='width:90px;height:{SLOT_HEIGHT}px;flex-shrink:0;display:flex;align-items:center;justify-content:center'>"
            f"    <img src='{sprite_src}' style='max-width:90px;max-height:{SLOT_HEIGHT}px;object-fit:contain'>"
            f"  </div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("✕", key=f"remove_{idx}", help="Remove"):
            st.session_state.pending_remove = idx


TYPE_ABBR = {
    "normal": "Nor", "fire": "Fir", "water": "Wat", "electric": "Ele",
    "grass": "Grs", "ice": "Ice", "fighting": "Fig", "poison": "Psn",
    "ground": "Gnd", "flying": "Fly", "psychic": "Psy", "bug": "Bug",
    "rock": "Roc", "ghost": "Gho", "dragon": "Dra", "dark": "Drk",
    "steel": "Stl", "fairy": "Fai",
}
MULT_STYLE = {
    0.0:  ("background:#888;color:#fff",           "0×"),
    0.25: ("background:#2a7a2a;color:#fff",        "¼×"),
    0.5:  ("background:#5a9e5a;color:#fff",        "½×"),
    1.0:  ("background:transparent;color:inherit", ""),
    2.0:  ("background:#e87070;color:#fff",        "2×"),
    4.0:  ("background:#b52020;color:#fff",        "4×"),
}


def render_weakness_heatmap(team: list[dict]):
    if not team:
        return
    col_w = "34px"
    header_cells = '<th style="min-width:80px;max-width:80px;width:80px"></th>' + "".join(
        f'<th style="width:{col_w};min-width:{col_w};max-width:{col_w};padding:2px 0;'
        f'font-size:0.72em;text-align:center;background:{TYPE_COLORS.get(t,"#888")};'
        f'color:#fff;border-radius:3px 3px 0 0">{TYPE_ABBR[t]}</th>'
        for t in ALL_TYPES
    )
    body_rows = ""
    for pokemon in team:
        types = [slot["type"]["name"] for slot in pokemon["types"]]
        profile = get_defensive_profile(types)
        primary_type = types[0]
        name_color = TYPE_COLORS.get(primary_type, "#888")
        cells = (
            f'<td style="font-size:0.75em;font-weight:700;padding:2px 6px;white-space:nowrap;'
            f'max-width:80px;overflow:hidden;text-overflow:ellipsis;'
            f'background:{name_color};color:#fff;border-radius:4px">'
            f'{pokemon["name"].capitalize()}</td>'
        )
        for t in ALL_TYPES:
            val = profile[t]
            style, label = MULT_STYLE.get(val, ("", str(val)))
            cells += (
                f'<td style="width:{col_w};min-width:{col_w};max-width:{col_w};'
                f'text-align:center;font-size:0.68em;padding:2px 0;{style};border-radius:2px">'
                f'{label}</td>'
            )
        body_rows += f"<tr>{cells}</tr>"
    st.markdown(
        '<div style="overflow-x:auto">'
        '<table style="border-collapse:separate;border-spacing:1px;width:100%">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{body_rows}</tbody>"
        "</table></div>",
        unsafe_allow_html=True,
    )


PLOTLY_COLORS = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]


def render_radar_chart(team: list[dict]):
    if not team:
        return

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
            domain=dict(x=[0.25, 0.95], y=[0.05, 0.95]),
            radialaxis=dict(visible=True, range=[0, 100]),
        ),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=0),
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_type_profile(team: list[dict], analysis: dict):
    chart = build_type_chart()
    weakness_counts = analysis.get("weakness_counts", {})

    # ── Defensive: sort types by how many team members are weak to them ──
    weak_types = sorted(
        [(t, c) for t, c in weakness_counts.items() if c > 0],
        key=lambda x: -x[1],
    )

    def weak_badge(type_name: str, count: int) -> str:
        color = TYPE_COLORS.get(type_name, "#888")
        border = "3px solid #fff" if count >= 3 else "none"
        return (
            f'<span style="display:inline-flex;align-items:center;background:{color};color:#fff;'
            f'padding:1px 6px;border-radius:4px;font-size:0.75em;margin:2px 3px 2px 0;'
            f'border:{border}">'
            f'{type_name.capitalize()} <sup style="margin-left:2px;font-size:0.8em">{count}</sup></span>'
        )

    weak_html = "".join(weak_badge(t, c) for t, c in weak_types) or "<span style='opacity:0.4;font-size:0.8em'>None</span>"

    # ── Offensive: STAB types and what they hit super effectively ──
    stab_types = list({slot["type"]["name"] for p in team for slot in p["types"]})
    covered: set[str] = set()
    for st_type in stab_types:
        for defender, mult in chart[st_type].items():
            if mult >= 2.0:
                covered.add(defender)
    uncovered = [t for t in ALL_TYPES if t not in covered]

    cov_html = "".join(type_badge(t) for t in sorted(covered)) or "<span style='opacity:0.4;font-size:0.8em'>None</span>"
    miss_html = "".join(type_badge(t, faded=True) for t in uncovered) or "<span style='opacity:0.4;font-size:0.8em'>Full</span>"

    st.markdown(
        f"<div style='margin-bottom:4px'>"
        f"<span style='font-size:0.78em;font-weight:600'>Defensive Weaknesses</span>"
        f"<span style='font-size:0.68em;opacity:0.55;margin-left:6px'>white border = 3+ members weak</span>"
        f"</div>"
        f"<div style='margin-bottom:8px'>{weak_html}</div>"
        f"<div style='margin-bottom:4px'>"
        f"<span style='font-size:0.78em;font-weight:600'>Offensive STAB Coverage</span>"
        f"</div>"
        f"<div style='margin-bottom:4px'>{cov_html}</div>"
        f"<div style='font-size:0.75em;font-weight:600;opacity:0.6;margin-bottom:2px'>Not covered</div>"
        f"<div>{miss_html}</div>",
        unsafe_allow_html=True,
    )


def _effective_bst(member: dict) -> int:
    api_stats = {s["stat"]["name"]: s["base_stat"] for s in member["stats"]}
    overrides = st.session_state.stat_overrides.get(member["name"], {})
    return sum(overrides.get(s, api_stats.get(s, 0)) for s in STAT_ORDER) if overrides else sum(api_stats.values())


def get_recommendations(team: list[dict], analysis: dict, n: int = 4) -> list[dict]:
    chart = build_type_chart()
    current_names = {p["name"] for p in team}

    # Team BST stats — used to gate candidates to a reasonable power level
    team_bsts = [_effective_bst(p) for p in team]
    team_avg_bst = sum(team_bsts) / len(team_bsts)
    min_candidate_bst = max(400, int(team_avg_bst * 0.85))

    weakness_counts = analysis.get("weakness_counts", {})
    critical = [t for t, c in weakness_counts.items() if c >= 3]
    notable = [t for t, c in weakness_counts.items() if c >= 2]

    stab_types = {slot["type"]["name"] for p in team for slot in p["types"]}
    covered = {defender for st in stab_types for defender, m in chart[st].items() if m >= 2.0}
    gaps = [t for t in ALL_TYPES if t not in covered]

    # Score each type by how well it helps the team
    type_scores: dict[str, int] = {}
    for candidate in ALL_TYPES:
        score = 0
        for weak in critical:
            if chart[weak].get(candidate, 1.0) <= 0.5:
                score += 3
        for weak in notable:
            if chart[weak].get(candidate, 1.0) <= 0.5:
                score += 1
        for gap in gaps:
            if chart[candidate].get(gap, 1.0) >= 2.0:
                score += 2
        type_scores[candidate] = score

    top_types = sorted(type_scores, key=lambda t: -type_scores[t])[:4]

    # Gather candidate names from top types
    seen: set[str] = set()
    candidate_names: list[str] = []
    for type_name in top_types:
        type_data = get_type(type_name)
        for entry in type_data.get("pokemon", [])[:30]:
            name = entry["pokemon"]["name"]
            if name not in current_names and name not in seen and name.count("-") == 0:
                seen.add(name)
                candidate_names.append(name)

    # Fetch, filter by BST floor, and score
    results = []
    for name in candidate_names:
        if len(results) >= n * 4:
            break
        pdata = get_pokemon(name)
        if pdata is None:
            continue

        bst = sum(s["base_stat"] for s in pdata["stats"])

        # Hard gate: skip candidates below team power floor
        if bst < min_candidate_bst:
            continue

        poke_types = [slot["type"]["name"] for slot in pdata["types"]]
        profile = get_defensive_profile(poke_types)

        score = 0
        resists, covers = [], []
        for weak in critical:
            if profile.get(weak, 1.0) <= 0.5:
                score += 3
                resists.append(weak)
        for weak in notable:
            if profile.get(weak, 1.0) <= 0.5:
                score += 1
                if weak not in resists:
                    resists.append(weak)
        for gap in gaps:
            for pt in poke_types:
                if chart[pt].get(gap, 1.0) >= 2.0 and gap not in covers:
                    score += 2
                    covers.append(gap)

        # BST score relative to team average — prefer near or above average
        bst_diff = bst - team_avg_bst
        if bst_diff >= 80:
            score += 4
        elif bst_diff >= 20:
            score += 2
        elif bst_diff >= -40:
            score += 1

        if score > 0:
            results.append({"pokemon": pdata, "score": score, "resists": resists, "covers": covers, "bst": bst})

    results.sort(key=lambda x: -x["score"])
    top = results[:n]

    # Find best swap target after sorting
    for rec in top:
        rec_types = [slot["type"]["name"] for slot in rec["pokemon"]["types"]]
        rec_bst = rec["bst"]
        best_swap, best_swap_score = None, float("-inf")

        for member in team:
            m_types = [slot["type"]["name"] for slot in member["types"]]
            m_profile = get_defensive_profile(m_types)
            m_bst = _effective_bst(member)

            # Skip: never suggest replacing a significantly stronger Pokémon with a weaker one
            if m_bst > rec_bst * 1.15:
                continue

            swap_score = sum(1 for w in critical if m_profile.get(w, 1.0) > 1.0) * 3
            swap_score += sum(1 for w in notable if m_profile.get(w, 1.0) > 1.0)

            if set(m_types) & set(rec_types):
                swap_score += 2

            other_types = {
                slot["type"]["name"]
                for p in team if p["name"] != member["name"]
                for slot in p["types"]
            } | set(rec_types)
            unique_coverage = sum(
                1 for gap in gaps
                for mt in m_types
                if chart[mt].get(gap, 1.0) >= 2.0
                and not any(chart[ot].get(gap, 1.0) >= 2.0 for ot in other_types)
            )
            swap_score -= unique_coverage * 2

            # Prefer replacing lower BST members
            if m_bst < team_avg_bst * 0.85:
                swap_score += 3
            elif m_bst < team_avg_bst:
                swap_score += 1

            if swap_score > best_swap_score:
                best_swap_score = swap_score
                best_swap = member["name"]

        rec["replace"] = best_swap

    return top


def get_smogon_recommendations(team: list[dict], analysis: dict, format_mode: str, n: int = 4) -> list[dict]:
    import math
    formats = SINGLES_FORMATS[:3] if format_mode == "Singles" else DOUBLES_FORMATS

    # Merge meta across top formats (first format wins for duplicates)
    meta: dict[str, dict] = {}
    for fmt in formats:
        with st.spinner(f"Loading {fmt} competitive data…"):
            fmt_meta = get_smogon_format_meta(fmt)
        for name, data in fmt_meta.items():
            if name not in meta:
                meta[name] = data
        if len(meta) >= 150:
            break

    if not meta:
        return get_recommendations(team, analysis, n)

    current_names = {p["name"] for p in team}
    chart = build_type_chart()
    weakness_counts = analysis.get("weakness_counts", {})
    critical = [t for t, c in weakness_counts.items() if c >= 3]
    notable = [t for t, c in weakness_counts.items() if c >= 2]
    stab_types = {slot["type"]["name"] for p in team for slot in p["types"]}
    covered = {d for st_type in stab_types for d, m in chart[st_type].items() if m >= 2.0}
    gaps = [t for t in ALL_TYPES if t not in covered]

    # Teammate synergy: sum teammate co-occurrence rates across current team members
    synergy: dict[str, float] = {}
    for pokemon in team:
        for teammate, rate in meta.get(pokemon["name"], {}).get("teammates", {}).items():
            if teammate not in current_names:
                synergy[teammate] = synergy.get(teammate, 0) + rate

    # Pre-score without fetching Pokémon data — limits expensive API calls
    pre_scored = []
    for candidate, cdata in meta.items():
        if candidate in current_names:
            continue
        usage = cdata.get("usage", 0)
        pre = synergy.get(candidate, 0) * 10 + math.log1p(usage * 100) * 0.5
        pre_scored.append((candidate, pre))
    pre_scored.sort(key=lambda x: -x[1])

    # Fully score top candidates only
    results = []
    for candidate, _ in pre_scored[:50]:
        pdata = get_pokemon(candidate)
        if pdata is None:
            continue

        poke_types = [slot["type"]["name"] for slot in pdata["types"]]
        profile = get_defensive_profile(poke_types)
        bst = sum(s["base_stat"] for s in pdata["stats"])
        usage = meta[candidate].get("usage", 0)

        score = synergy.get(candidate, 0) * 10 + math.log1p(usage * 100) * 0.5
        resists, covers = [], []

        for weak in critical:
            if profile.get(weak, 1.0) <= 0.5:
                score += 3
                resists.append(weak)
        for weak in notable:
            if profile.get(weak, 1.0) <= 0.5:
                score += 1
                if weak not in resists:
                    resists.append(weak)
        for gap in gaps:
            for pt in poke_types:
                if chart[pt].get(gap, 1.0) >= 2.0 and gap not in covers:
                    score += 2
                    covers.append(gap)

        results.append({"pokemon": pdata, "score": score, "resists": resists,
                         "covers": covers, "bst": bst})

    results.sort(key=lambda x: -x["score"])
    top = results[:n]

    # Swap targets (same logic as rule-based)
    team_bsts = [_effective_bst(p) for p in team]
    team_avg_bst = sum(team_bsts) / len(team_bsts) if team_bsts else 500
    for rec in top:
        rec_types = [slot["type"]["name"] for slot in rec["pokemon"]["types"]]
        best_swap, best_swap_score = None, float("-inf")
        for member in team:
            m_types = [slot["type"]["name"] for slot in member["types"]]
            m_profile = get_defensive_profile(m_types)
            m_bst = _effective_bst(member)
            if m_bst > rec["bst"] * 1.15:
                continue
            swap_score = sum(1 for w in critical if m_profile.get(w, 1.0) > 1.0) * 3
            swap_score += sum(1 for w in notable if m_profile.get(w, 1.0) > 1.0)
            if set(m_types) & set(rec_types):
                swap_score += 2
            swap_score += 3 if m_bst < team_avg_bst * 0.85 else (1 if m_bst < team_avg_bst else 0)
            if swap_score > best_swap_score:
                best_swap_score = swap_score
                best_swap = member["name"]
        rec["replace"] = best_swap

    return top


def render_recommendations(team: list[dict], analysis: dict):
    with st.spinner("Finding recommendations…"):
        recs = get_smogon_recommendations(team, analysis, st.session_state.format_mode)
    st.session_state.rec_cache = recs

    if not recs:
        st.caption("No clear recommendations — your team looks well-balanced!")
        return

    cols = st.columns(len(recs))
    for col, rec in zip(cols, recs):
        pdata = rec["pokemon"]
        sprite_src = get_sprite_url(pdata)
        types_html = "".join(type_badge(slot["type"]["name"]) for slot in pdata["types"])
        resists_html = "".join(type_badge(t) for t in rec["resists"]) or "<span style='opacity:0.4;font-size:0.72em'>—</span>"
        covers_html = "".join(type_badge(t) for t in rec["covers"]) or "<span style='opacity:0.4;font-size:0.72em'>—</span>"

        replace_name = rec.get("replace", "")
        replace_label = (
            f"<div style='font-size:0.68em;margin-top:5px;padding:2px 6px;"
            f"background:rgba(255,100,100,0.15);border-radius:4px;display:inline-block'>"
            f"Replace <b>{replace_name.capitalize()}</b></div>"
            if replace_name else ""
        )

        with col:
            st.markdown(
                f"<div style='text-align:center'>"
                f"  <img src='{sprite_src}' style='height:72px;max-width:90px;object-fit:contain'>"
                f"  <div style='font-size:0.82em;font-weight:600'>{pdata['name'].capitalize()}</div>"
                f"  <div style='margin:2px 0'>{types_html}</div>"
                f"  <div style='font-size:0.68em;opacity:0.55'>BST {rec['bst']}</div>"
                f"  {replace_label}"
                f"  <div style='font-size:0.68em;opacity:0.7;margin-top:4px'>Resists</div>"
                f"  <div>{resists_html}</div>"
                f"  <div style='font-size:0.68em;opacity:0.7;margin-top:3px'>Covers</div>"
                f"  <div>{covers_html}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )



def recommend_moveset(pokemon: dict, format_mode: str = "Singles") -> list[dict]:
    formats = ALL_DOUBLES_FORMATS if format_mode == "Doubles" else ALL_SINGLES_FORMATS
    smogon_names = get_smogon_moveset(pokemon["name"], formats=formats)
    if not smogon_names:
        return []

    selected: list[dict] = []
    for move_name in smogon_names:
        if len(selected) >= 4:
            break
        data = get_move(move_name)
        if data is None:
            continue
        selected.append({
            "name": move_name,
            "power": data.get("power") or 0,
            "accuracy": data.get("accuracy") or 100,
            "type": data["type"]["name"],
            "category": data["damage_class"]["name"],
            "score": 0,
        })
    return selected


def render_movesets(team: list[dict]):
    if not team:
        return
    tabs = st.tabs([p["name"].capitalize() for p in team])
    for tab, pokemon in zip(tabs, team):
        with tab:
            fmt_mode = st.session_state.get("format_mode", "Singles")
            with st.spinner(f"Loading moves for {pokemon['name'].capitalize()}…"):
                moves = recommend_moveset(pokemon, format_mode=fmt_mode)
            st.session_state.moveset_cache[pokemon["name"]] = moves
            if not moves:
                st.caption(f"No Smogon competitive data found for {pokemon['name'].capitalize()} in {fmt_mode} formats.")
            for move in moves:
                color = TYPE_COLORS.get(move["type"], "#888")
                cat_icon = {"physical": "⚔️", "special": "✨", "status": "🔧"}.get(move["category"], "")
                power_str = f"PWR {move['power']}" if move["power"] else "—"
                acc_str = f"ACC {move['accuracy']}%" if move["accuracy"] else "—"
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;"
                    f"padding:5px 8px;border-radius:5px;background:rgba(128,128,128,0.07)'>"
                    f"  <span style='background:{color};color:#fff;padding:1px 7px;"
                    f"border-radius:4px;font-size:0.72em;white-space:nowrap'>{move['type'].capitalize()}</span>"
                    f"  <span style='font-size:0.82em;font-weight:600;flex:1'>{cat_icon} {move['name'].replace('-', ' ').title()}</span>"
                    f"  <span style='font-size:0.7em;opacity:0.55'>{power_str}</span>"
                    f"  <span style='font-size:0.7em;opacity:0.55'>{acc_str}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


def render_coverage_badges(analysis: dict):
    covered = analysis.get("offensive_coverage", [])
    missing = analysis.get("uncovered_types", [])
    covers_html = "".join(type_badge(t) for t in covered) if covered else "<span style='opacity:0.4;font-size:0.8em'>None</span>"
    missing_html = "".join(type_badge(t, faded=True) for t in missing) if missing else "<span style='opacity:0.4;font-size:0.8em'>Full coverage!</span>"
    st.markdown(
        f"<div style='margin-bottom:3px'><span style='font-size:0.78em;font-weight:600;margin-right:6px'>Covers</span>{covers_html}</div>"
        f"<div><span style='font-size:0.78em;font-weight:600;margin-right:6px'>Missing</span>{missing_html}</div>",
        unsafe_allow_html=True,
    )


# ── Team persistence helpers ─────────────────────────────────────────────────
TEAMS_FILE = "teams.json"
MAX_TEAMS = 5


def _load_teams_from_disk() -> dict:
    import json, os
    if os.path.exists(TEAMS_FILE):
        with open(TEAMS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_teams_to_disk(teams: dict):
    import json
    with open(TEAMS_FILE, "w") as f:
        json.dump(teams, f)


def _team_to_record(team: list[dict], stat_overrides: dict) -> dict:
    return {
        "pokemon": [p["name"] for p in team],
        "stat_overrides": stat_overrides,
    }


def _load_team_from_record(record: dict) -> tuple[list[dict], dict]:
    team = []
    for name in record.get("pokemon", []):
        data = get_pokemon(name)
        if data:
            team.append(data)
    return team, record.get("stat_overrides", {})


# Load saved teams into session state once
if st.session_state.saved_teams is None:
    st.session_state.saved_teams = _load_teams_from_disk()


# ── Header ──────────────────────────────────────────────────────────────────
st.markdown("## Pokémon Team Builder")
st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)

left, right = st.columns([4, 6])

# ── Left column ──────────────────────────────────────────────────────────────
with left:
    if st.session_state.pending_remove is not None:
        idx = st.session_state.pending_remove
        if 0 <= idx < len(st.session_state.team):
            st.session_state.team.pop(idx)
        st.session_state.pending_remove = None
        st.session_state.loaded_team_name = None

    fmt_col, sel_col = st.columns([1, 3])
    with fmt_col:
        st.session_state.format_mode = st.radio(
            "Format", ["Singles", "Doubles"],
            index=0 if st.session_state.format_mode == "Singles" else 1,
            horizontal=True, label_visibility="collapsed",
        )

    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        selected = st.selectbox(
            "",
            options=[""] + st.session_state.all_names,
            format_func=lambda x: "Search Pokémon…" if x == "" else x.replace("-", " ").title(),
            label_visibility="collapsed",
            key=f"pokemon_select_{st.session_state.select_key}",
        )
    with col_btn:
        add_clicked = st.button("Add", use_container_width=True, disabled=len(st.session_state.team) >= 6)

    if add_clicked and selected:
        if len(st.session_state.team) >= 6:
            st.warning("Team is full (6/6).")
        else:
            with st.spinner(f"Loading {selected}…"):
                data = get_pokemon(selected)
            if data is None:
                st.error(f"'{selected}' not found.")
            else:
                st.session_state.team.append(data)
                st.session_state.loaded_team_name = None
                st.session_state.select_key += 1
                st.rerun()

    if st.button("🎲 Random Pokémon", disabled=len(st.session_state.team) >= 6, use_container_width=True):
        with st.spinner("Picking a random Pokémon…"):
            data = get_pokemon(str(random.randint(1, 1025)))
        if data:
            st.session_state.team.append(data)
            st.session_state.loaded_team_name = None
            st.rerun()

    st.markdown(f"<div style='font-size:0.8em;font-weight:600;margin:4px 0 2px'>Team ({len(st.session_state.team)}/6)</div>", unsafe_allow_html=True)
    for row in range(3):
        c1, c2 = st.columns(2)
        for col_idx, col in enumerate([c1, c2]):
            i = row * 2 + col_idx
            pokemon = st.session_state.team[i] if i < len(st.session_state.team) else None
            with col:
                render_team_slot(pokemon, i)

    if st.session_state.pending_remove is not None:
        st.rerun()

    # ── Saved teams ──────────────────────────────────────────────────────────
    saved = st.session_state.saved_teams
    with st.expander(f"💾 Saved Teams ({len(saved)}/{MAX_TEAMS})", expanded=False):

        if saved:
            selected_team = st.selectbox(
                "Saved teams", list(saved.keys()), label_visibility="collapsed", key="saved_team_select"
            )

            col_load, col_del = st.columns(2)
            with col_load:
                if st.button("Load", use_container_width=True, key="load_team_btn"):
                    with st.spinner(f"Loading {selected_team}…"):
                        loaded, overrides = _load_team_from_record(saved[selected_team])
                    st.session_state.team = loaded
                    st.session_state.stat_overrides = overrides
                    st.session_state.loaded_team_name = selected_team
                    st.session_state.select_key += 1
                    st.rerun()
            with col_del:
                if st.button("Delete", use_container_width=True, key="del_team_btn", type="secondary"):
                    saved.pop(selected_team, None)
                    _save_teams_to_disk(saved)
                    st.rerun()

            # Rename
            col_rename, col_rename_btn = st.columns([3, 1])
            with col_rename:
                new_name = st.text_input("", placeholder="New name…", label_visibility="collapsed", key="rename_input")
            with col_rename_btn:
                if st.button("Rename", use_container_width=True, key="rename_btn") and new_name and new_name != selected_team:
                    if new_name not in saved:
                        saved[new_name] = saved.pop(selected_team)
                        _save_teams_to_disk(saved)
                        st.rerun()
                    else:
                        st.warning("Name already exists.")

            st.divider()

        # Save current team
        if st.session_state.team:
            col_name, col_save = st.columns([3, 1])
            with col_name:
                save_name = st.text_input("", placeholder="Team name…", label_visibility="collapsed", key="save_name_input")
            with col_save:
                can_save = len(saved) < MAX_TEAMS or save_name in saved
                if st.button("Save", use_container_width=True, key="save_team_btn", disabled=not can_save):
                    if save_name:
                        saved[save_name] = _team_to_record(st.session_state.team, st.session_state.stat_overrides)
                        _save_teams_to_disk(saved)
                        st.success(f"Saved as '{save_name}'!")
            if len(saved) >= MAX_TEAMS and save_name not in saved:
                st.caption(f"Max {MAX_TEAMS} teams reached. Delete one to save a new team.")
        else:
            st.caption("Add Pokémon to your team before saving.")

    STAT_SHORT = {"hp": "HP", "attack": "Atk", "defense": "Def",
                  "special-attack": "SpA", "special-defense": "SpD", "speed": "Spe"}

    if st.session_state.team:
        with st.expander("⚙️ Custom stats", expanded=False):
            st.caption("Edit individual stats per Pokémon. BST updates automatically. Leave at API values to use defaults.")
            for pokemon in st.session_state.team:
                name = pokemon["name"]
                api_stats = {s["stat"]["name"]: s["base_stat"] for s in pokemon["stats"]}
                overrides = st.session_state.stat_overrides.get(name, {})

                st.markdown(
                    f"<div style='font-size:0.8em;font-weight:700;margin:10px 0 0;"
                    f"background:rgba(99,110,250,0.15);border-left:3px solid #636EFA;"
                    f"padding:4px 8px;border-radius:0 4px 4px 0'>{name.capitalize()}</div>"
                    f"<div style='margin-bottom:10px'></div>",
                    unsafe_allow_html=True,
                )
                stat_cols = st.columns(6)
                new_overrides = {}
                for col, stat_key in zip(stat_cols, STAT_ORDER):
                    api_val = api_stats.get(stat_key, 0)
                    current_val = overrides.get(stat_key, api_val)
                    entered = col.number_input(
                        STAT_SHORT.get(stat_key, stat_key),
                        min_value=1, max_value=255,
                        value=current_val,
                        step=1,
                        key=f"stat_{name}_{stat_key}",
                    )
                    if entered != api_val:
                        new_overrides[stat_key] = entered

                effective_bst = sum(
                    new_overrides.get(s, api_stats.get(s, 0)) for s in STAT_ORDER
                )
                api_bst = sum(api_stats.values())
                diff = effective_bst - api_bst
                diff_str = f"+{diff}" if diff > 0 else str(diff)
                color = "#4caf50" if diff > 0 else "#e87070" if diff < 0 else "inherit"
                st.markdown(
                    f"<div style='font-size:0.72em;opacity:0.7;margin-bottom:6px'>"
                    f"BST: <b>{effective_bst}</b>"
                    f"{'&nbsp;<span style=color:' + color + '>' + diff_str + '</span>' if diff != 0 else ''}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if new_overrides:
                    st.session_state.stat_overrides[name] = new_overrides
                else:
                    st.session_state.stat_overrides.pop(name, None)

# ── Right column ─────────────────────────────────────────────────────────────
with right:
    team = st.session_state.team

    if not team:
        st.info("Add Pokémon to see analysis.")
    else:
        current_names = [p["name"] for p in team]
        if current_names != st.session_state.prev_team_names:
            st.session_state.analysis = analyze_team(team)
            st.session_state.prev_team_names = current_names
            st.session_state.claude_advice = ""

        analysis = st.session_state.analysis

        def section(title: str, color: str = "#4a90d9", top_margin: int = 0):
            st.markdown(
                f"<div style='margin-top:{top_margin}px;margin-bottom:8px;"
                f"border-left:4px solid {color};padding-left:8px;"
                f"font-size:0.9em;font-weight:700;letter-spacing:0.02em'>{title}</div>",
                unsafe_allow_html=True,
            )

        section("Type Weakness Heatmap", "#e87070")
        render_weakness_heatmap(team)
        st.divider()

        section("Stat Radar", "#636EFA")
        render_radar_chart(team)
        st.divider()

        section("Type Strengths & Weaknesses", "#00CC96")
        render_type_profile(team, analysis)
        st.divider()

        if len(team) >= 2:
            section(f"Recommended Replacements ({st.session_state.format_mode})", "#FFA15A")
            render_recommendations(team, analysis)

        st.divider()
        section("Recommended Movesets", "#AB63FA")
        render_movesets(team)

        st.divider()
        export_col1, export_col2 = st.columns(2)

        with export_col1:
            if st.button("Export as PDF", use_container_width=True):
                with st.spinner("Generating PDF…"):
                    try:
                        pdf_bytes = generate_team_pdf(
                            team,
                            analysis,
                            st.session_state.stat_overrides,
                            st.session_state.moveset_cache,
                            st.session_state.rec_cache,
                            team_name=st.session_state.loaded_team_name,
                        )
                        st.download_button(
                            label="Download PDF",
                            data=pdf_bytes,
                            file_name="pokemon_team_report.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"PDF generation failed: {e}")

        with export_col2:
            if st.button("Export as HTML", use_container_width=True):
                with st.spinner("Generating HTML…"):
                    try:
                        html_str = generate_team_html(
                            team,
                            analysis,
                            st.session_state.stat_overrides,
                            st.session_state.moveset_cache,
                            st.session_state.rec_cache,
                            team_name=st.session_state.loaded_team_name,
                        )
                        st.download_button(
                            label="Download HTML",
                            data=html_str.encode("utf-8"),
                            file_name="pokemon_team_report.html",
                            mime="text/html",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"HTML generation failed: {e}")

        # Claude analysis temporarily disabled
        # if len(team) >= 3:
        #     with st.expander("🤖 Claude's Team Analysis", expanded=True):
        #         if not st.session_state.claude_advice:
        #             with st.spinner("Asking Claude…"):
        #                 try:
        #                     st.session_state.claude_advice = get_team_advice(analysis, team)
        #                 except Exception as e:
        #                     st.session_state.claude_advice = f"Error: {e}"
        #         st.markdown(st.session_state.claude_advice)
        # else:
        #     st.caption("Add at least 3 Pokémon to unlock Claude's team analysis.")
