# Pokémon Team Builder

A Streamlit web app for building and analyzing competitive Pokémon teams. Pulls live data from the [PokéAPI](https://pokeapi.co/) with local file caching so repeated lookups are instant.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Team Builder** — Search or randomly pick from 1302 Pokémon; build a team of up to 6
- **Animated Sprites** — Pokémon Showdown animated GIFs with static fallback
- **Type Weakness Heatmap** — Color-coded 6×18 grid showing every type matchup at a glance
- **Stat Radar** — Interactive Plotly polar chart comparing base stats across your team
- **Type Coverage Analysis** — Defensive weaknesses (with count badges) and offensive STAB coverage
- **Recommended Replacements** — Rule-based engine suggests up to 4 swaps to patch team weaknesses, factoring in BST, type utility, and coverage gaps
- **Recommended Movesets** — Scored by STAB bonus, physical/special preference, and move utility
- **Custom Stat Overrides** — Adjust any individual stat (1–255) per Pokémon; BST updates live
- **Saved Teams** — Save, load, rename, and delete up to 5 teams; persisted across sessions
- **PDF Export** — Dark-mode landscape report with heatmap, movesets, and recommendations

---

## Setup

### Prerequisites

- Python 3.10+
- pip

### Install

```bash
git clone https://github.com/your-username/PokemonAPI.git
cd PokemonAPI
pip install -r requirements.txt
```

### Environment (optional — for Claude AI analysis)

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_key_here
```

The Claude analysis panel is disabled by default to avoid token costs. To enable it, uncomment the relevant section at the bottom of `app.py`.

### Run

```bash
python -m streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Project Structure

```
PokemonAPI/
├── app.py            # Main Streamlit UI and session logic
├── api.py            # PokéAPI wrapper with file-based caching
├── team.py           # Team analysis (weakness counts, coverage, role balance)
├── type_chart.py     # 18×18 damage multiplier matrix
├── pdf_export.py     # Dark-mode PDF report generator (fpdf2)
├── advisor.py        # Claude AI team analysis (optional)
├── constants.py      # TYPE_COLORS, ALL_TYPES, STAT_ORDER, STAT_LABELS
├── requirements.txt
├── .streamlit/
│   └── config.toml   # Headless mode (no Ctrl+C cache prompt)
├── cache/            # Auto-created; stores PokéAPI JSON responses
└── teams.json        # Auto-created; stores saved teams
```

---

## Tech Stack

| Library | Use |
|---|---|
| [Streamlit](https://streamlit.io/) | Web UI framework |
| [PokéAPI](https://pokeapi.co/) | Pokémon data (no API key required) |
| [Plotly](https://plotly.com/) | Interactive stat radar chart |
| [fpdf2](https://py-fpdf2.readthedocs.io/) | PDF export |
| [Anthropic](https://www.anthropic.com/) | Claude AI analysis (optional) |
| [Pillow](https://python-pillow.org/) | Image handling |
| [Requests](https://docs.python-requests.org/) | HTTP client |

---

## Notes

- API responses are cached to `cache/` on first fetch; delete the folder to force a refresh
- Animated sprites are sourced from Pokémon Showdown and fall back to PokéAPI static sprites when unavailable
- The recommendation engine is fully rule-based and requires no AI credits
- PDF export uses static sprites (animated GIFs are not supported by fpdf2)
