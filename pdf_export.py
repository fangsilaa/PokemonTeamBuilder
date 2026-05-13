from __future__ import annotations
import io
import requests
from fpdf import FPDF
from constants import TYPE_COLORS, ALL_TYPES, STAT_ORDER, STAT_LABELS
from type_chart import get_defensive_profile, build_type_chart

# ── Dark mode palette ─────────────────────────────────────────────────────────
BG       = (18,  18,  28)
SURFACE  = (30,  30,  46)
SURFACE2 = (40,  40,  60)
BORDER   = (60,  60,  90)
TEXT     = (220, 220, 235)
SUBTEXT  = (150, 150, 175)
ACCENT   = (99,  110, 250)
ACCENT2  = (0,   204, 150)
WARN     = (232, 112, 112)

TYPE_ABBR = {
    "normal": "Nor", "fire": "Fir", "water": "Wat", "electric": "Ele",
    "grass": "Grs", "ice": "Ice", "fighting": "Fig", "poison": "Psn",
    "ground": "Gnd", "flying": "Fly", "psychic": "Psy", "bug": "Bug",
    "rock": "Roc", "ghost": "Gho", "dragon": "Dra", "dark": "Drk",
    "steel": "Stl", "fairy": "Fai",
}

MULT_LABEL = {0.0: "0×", 0.25: "¼×", 0.5: "½×", 1.0: "", 2.0: "2×", 4.0: "4×"}
MULT_COLOR = {
    0.0:  (100, 100, 100),
    0.25: (30,  110, 60),
    0.5:  (50,  140, 80),
    1.0:  None,
    2.0:  (180, 70,  70),
    4.0:  (140, 20,  20),
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _darken(rgb: tuple[int, int, int], factor: float = 0.6) -> tuple[int, int, int]:
    return tuple(int(c * factor) for c in rgb)


def _fetch_image(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


class DarkPDF(FPDF):
    def header(self):
        self.set_fill_color(*BG)
        self.rect(0, 0, self.w, self.h, "F")

    def _accent_bar(self):
        self.set_fill_color(*ACCENT)
        self.rect(0, 0, self.w, 1.5, "F")


def _section_header(pdf: DarkPDF, usable_w: float, title: str, y_gap: float = 5):
    pdf.ln(y_gap)
    bar_y = pdf.get_y()
    pdf.set_fill_color(*SURFACE)
    pdf.rect(10, bar_y, usable_w, 9, "F")
    pdf.set_fill_color(*ACCENT)
    pdf.rect(10, bar_y, 3, 9, "F")
    pdf.set_xy(15, bar_y)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*ACCENT)
    pdf.cell(usable_w - 5, 9, title.upper())
    pdf.ln(9)


def generate_team_pdf(
    team: list[dict],
    analysis: dict,
    stat_overrides: dict,
    movesets: dict[str, list[dict]],
    recommendations: list[dict] | None = None,
    team_name: str | None = None,
) -> bytes:
    pdf = DarkPDF(orientation="L", unit="mm", format="A4")
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf._accent_bar()

    usable_w = pdf.w - 20  # 297 - 20 margins

    # ── Title ──────────────────────────────────────────────────────────────────
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*ACCENT)
    pdf.cell(usable_w, 10, "POKEMON TEAM REPORT", ln=True, align="C")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*SUBTEXT)
    subtitle = team_name if team_name else "  ·  ".join(p["name"].capitalize() for p in team)
    pdf.cell(usable_w, 5, subtitle, ln=True, align="C")

    pdf.ln(2)
    pdf.set_fill_color(*ACCENT)
    pdf.rect(10, pdf.get_y(), usable_w, 0.5, "F")
    pdf.ln(4)

    # ── Team sprites + info ────────────────────────────────────────────────────
    _section_header(pdf, usable_w, "Team Overview", y_gap=0)

    slot_w = usable_w / 6
    sprite_h = 26
    row_y = pdf.get_y() + 1
    card_h = sprite_h + 22  # sprite + name + types + BST

    for i, pokemon in enumerate(team):
        x = 10 + i * slot_w

        pdf.set_fill_color(*SURFACE)
        pdf.set_draw_color(*BORDER)
        pdf.set_line_width(0.3)
        pdf.rect(x + 0.5, row_y - 1, slot_w - 1, card_h, "FD")

        sprite_url = pokemon.get("sprites", {}).get("front_default")
        if sprite_url:
            img_data = _fetch_image(sprite_url)
            if img_data:
                try:
                    pdf.image(io.BytesIO(img_data), x=x + slot_w / 2 - 11, y=row_y, w=22, h=sprite_h)
                except Exception:
                    pass

        # Name
        pdf.set_xy(x, row_y + sprite_h + 1)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*TEXT)
        pdf.cell(slot_w, 5, pokemon["name"].capitalize(), align="C")

        # Type badges
        types = [slot["type"]["name"] for slot in pokemon["types"]]
        badge_w = (slot_w - 4) / len(types)
        bx = x + 2
        by = row_y + sprite_h + 7
        for t in types:
            r, g, b = _hex_to_rgb(TYPE_COLORS.get(t, "#888888"))
            pdf.set_fill_color(r, g, b)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_xy(bx, by)
            pdf.cell(badge_w - 1, 4.5, t.capitalize(), align="C", fill=True)
            bx += badge_w

        # BST
        api_bst = sum(s["base_stat"] for s in pokemon["stats"])
        overrides = stat_overrides.get(pokemon["name"], {})
        api_stats = {s["stat"]["name"]: s["base_stat"] for s in pokemon["stats"]}
        bst = sum(overrides.get(s, api_stats.get(s, 0)) for s in STAT_ORDER) if overrides else api_bst
        pdf.set_xy(x, row_y + sprite_h + 13)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*SUBTEXT)
        label = f"BST {bst}" + (" *" if overrides else "")
        pdf.cell(slot_w, 4.5, label, align="C")

    pdf.set_y(row_y + card_h + 2)

    # ── Type Weakness Heatmap ──────────────────────────────────────────────────
    _section_header(pdf, usable_w, "Type Weakness Heatmap")

    name_col_w = 28
    type_col_w = (usable_w - name_col_w) / len(ALL_TYPES)
    cell_h = 6.5
    table_y = pdf.get_y() + 1

    # Header row
    pdf.set_xy(10, table_y)
    pdf.set_fill_color(*SURFACE2)
    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.15)
    pdf.cell(name_col_w, cell_h, "", border=1, fill=True)

    for t in ALL_TYPES:
        r, g, b = _hex_to_rgb(TYPE_COLORS.get(t, "#888888"))
        pdf.set_fill_color(*_darken((r, g, b), 0.85))
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.cell(type_col_w, cell_h, TYPE_ABBR[t], align="C", fill=True, border=1)
    pdf.ln()

    for row_i, pokemon in enumerate(team):
        types = [slot["type"]["name"] for slot in pokemon["types"]]
        profile = get_defensive_profile(types)
        primary_type = types[0]
        r, g, b = _hex_to_rgb(TYPE_COLORS.get(primary_type, "#888888"))

        row_bg = SURFACE if row_i % 2 == 0 else SURFACE2
        pdf.set_fill_color(*row_bg)
        pdf.rect(10, pdf.get_y(), usable_w, cell_h, "F")

        pdf.set_fill_color(*_darken((r, g, b), 0.75))
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_draw_color(*BORDER)
        pdf.cell(name_col_w, cell_h, pokemon["name"].capitalize(), fill=True, border=1)

        for t in ALL_TYPES:
            val = profile.get(t, 1.0)
            color = MULT_COLOR.get(val)
            label = MULT_LABEL.get(val, "")
            if color:
                pdf.set_fill_color(*color)
                pdf.set_text_color(255, 255, 255)
                fill = True
            else:
                pdf.set_fill_color(*row_bg)
                pdf.set_text_color(*SUBTEXT)
                fill = True
            pdf.set_font("Helvetica", "B" if label else "", 7)
            pdf.cell(type_col_w, cell_h, label, align="C", fill=fill, border=1)
        pdf.ln()

    # ── Type Summary ───────────────────────────────────────────────────────────
    _section_header(pdf, usable_w, "Type Summary")
    pdf.ln(1)

    critical = analysis.get("critical_weaknesses", [])
    coverage = analysis.get("offensive_coverage", [])

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*WARN)
    pdf.cell(45, 6.5, "  Critical Weaknesses:")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT)
    pdf.cell(usable_w - 45, 6.5, ", ".join(t.capitalize() for t in critical) or "None", ln=True)

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*ACCENT2)
    pdf.cell(45, 6.5, "  Offensive Coverage:")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT)
    pdf.cell(usable_w - 45, 6.5, ", ".join(t.capitalize() for t in coverage) or "None", ln=True)

    # ── Page 2: Movesets + Replacements ───────────────────────────────────────
    # Force a new page so absolute-positioned card loops always start in bounds.
    # Without this, the moveset header lands near the bottom of page 1 and the
    # card loop's set_xy calls trigger cascading auto-breaks onto pages 3, 4, etc.
    if movesets or recommendations:
        pdf.add_page()
        pdf._accent_bar()

    # ── Recommended Movesets ───────────────────────────────────────────────────
    if movesets:
        _section_header(pdf, usable_w, "Recommended Movesets")

        col_w = usable_w / len(team)
        top_y = pdf.get_y() + 1
        # Use the maximum move count across all pokemon so all cards are the same height
        max_moves = max((len(movesets.get(p["name"], [])) for p in team), default=0)
        col_card_h = 7 + max_moves * 5.5 + 2

        for i, pokemon in enumerate(team):
            moves = movesets.get(pokemon["name"], [])
            x = 10 + i * col_w
            y = top_y

            prim_type = pokemon["types"][0]["type"]["name"]
            r, g, b = _hex_to_rgb(TYPE_COLORS.get(prim_type, "#888888"))

            pdf.set_fill_color(*SURFACE)
            pdf.set_draw_color(*BORDER)
            pdf.set_line_width(0.2)
            pdf.rect(x + 0.3, y, col_w - 0.6, col_card_h, "FD")

            # Header bar
            pdf.set_fill_color(*_darken((r, g, b), 0.75))
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_xy(x + 0.3, y)
            pdf.cell(col_w - 0.6, 7, pokemon["name"].capitalize(), align="C", fill=True)
            y += 7.5

            for move in moves:
                pdf.set_xy(x + 2, y)
                mr, mg, mb = _hex_to_rgb(TYPE_COLORS.get(move["type"], "#888888"))
                pdf.set_fill_color(*_darken((mr, mg, mb), 0.85))
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 6.5)
                pdf.cell(9, 4.5, move["type"][:3].capitalize(), align="C", fill=True)

                pdf.set_text_color(*TEXT)
                pdf.set_font("Helvetica", "", 7)
                move_name = move["name"].replace("-", " ").title()
                pdf.cell(col_w - 23, 4.5, move_name)

                pdf.set_text_color(*SUBTEXT)
                pdf.set_font("Helvetica", "", 6.5)
                pwr = str(move["power"]) if move["power"] else "-"
                pdf.cell(10, 4.5, pwr, align="R")
                y += 5.5

        pdf.set_y(top_y + col_card_h + 4)

    # ── Recommended Replacements ───────────────────────────────────────────────
    if recommendations:
        _section_header(pdf, usable_w, "Recommended Replacements")

        rec_col_w = usable_w / len(recommendations)
        top_y = pdf.get_y() + 2
        rec_card_h = 50

        for i, rec in enumerate(recommendations):
            pdata = rec["pokemon"]
            x = 10 + i * rec_col_w
            y = top_y

            prim_type = pdata["types"][0]["type"]["name"]
            r, g, b = _hex_to_rgb(TYPE_COLORS.get(prim_type, "#888888"))

            pdf.set_fill_color(*SURFACE)
            pdf.set_draw_color(*BORDER)
            pdf.set_line_width(0.25)
            pdf.rect(x + 0.5, y, rec_col_w - 1, rec_card_h, "FD")

            # Sprite
            sprite_url = pdata.get("sprites", {}).get("front_default")
            if sprite_url:
                img_data = _fetch_image(sprite_url)
                if img_data:
                    try:
                        pdf.image(io.BytesIO(img_data), x=x + rec_col_w / 2 - 10, y=y + 1, w=20, h=20)
                    except Exception:
                        pass
            y += 22

            # Name bar
            pdf.set_fill_color(*_darken((r, g, b), 0.75))
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_xy(x + 0.5, y)
            pdf.cell(rec_col_w - 1, 5.5, pdata["name"].capitalize(), align="C", fill=True)
            y += 6

            # BST
            pdf.set_xy(x + 0.5, y)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*SUBTEXT)
            pdf.cell(rec_col_w - 1, 4.5, f"BST {rec['bst']}", align="C")
            y += 5

            # Replace
            replace = rec.get("replace", "")
            if replace:
                pdf.set_xy(x + 0.5, y)
                pdf.set_font("Helvetica", "B", 7.5)
                pdf.set_text_color(*WARN)
                pdf.cell(rec_col_w - 1, 4.5, f"Replace: {replace.capitalize()}", align="C")
                y += 5

            # Resists
            resists = rec.get("resists", [])
            if resists:
                pdf.set_xy(x + 0.5, y)
                pdf.set_font("Helvetica", "B", 7)
                pdf.set_text_color(*ACCENT2)
                pdf.cell(rec_col_w - 1, 4, "Resists: " + ", ".join(t.capitalize() for t in resists), align="C")
                y += 4.5

            # Covers
            covers = rec.get("covers", [])
            if covers:
                pdf.set_xy(x + 0.5, y)
                pdf.set_font("Helvetica", "B", 7)
                pdf.set_text_color(*ACCENT)
                pdf.cell(rec_col_w - 1, 4, "Covers: " + ", ".join(t.capitalize() for t in covers), align="C")

        pdf.set_y(top_y + rec_card_h + 4)

    return bytes(pdf.output())
