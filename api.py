import json
import os
import requests

CACHE_DIR = "cache"
BASE_URL = "https://pokeapi.co/api/v2"


def _ensure_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(key: str) -> str:
    return os.path.join(CACHE_DIR, f"{key}.json")


def _load_cache(key: str):
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def _save_cache(key: str, data: dict):
    _ensure_cache()
    with open(_cache_path(key), "w") as f:
        json.dump(data, f)


def get_pokemon(name: str) -> dict | None:
    name = name.lower().strip().replace(" ", "-")
    key = f"pokemon_{name}"
    cached = _load_cache(key)
    if cached is not None:
        return cached

    resp = requests.get(f"{BASE_URL}/pokemon/{name}", timeout=10)
    if resp.status_code in (400, 404):
        return None
    resp.raise_for_status()
    data = resp.json()
    _save_cache(key, data)
    return data


def get_type(type_name: str) -> dict:
    key = f"type_{type_name}"
    cached = _load_cache(key)
    if cached is not None:
        return cached

    resp = requests.get(f"{BASE_URL}/type/{type_name}", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    _save_cache(key, data)
    return data


def get_move(name: str) -> dict | None:
    key = f"move_{name}"
    cached = _load_cache(key)
    if cached is not None:
        return cached

    resp = requests.get(f"{BASE_URL}/move/{name}", timeout=10)
    if resp.status_code in (400, 404):
        return None
    resp.raise_for_status()
    data = resp.json()
    _save_cache(key, data)
    return data


def get_all_pokemon_names() -> list[str]:
    key = "all_pokemon_names"
    cached = _load_cache(key)
    if cached is not None:
        return cached

    resp = requests.get(f"{BASE_URL}/pokemon?limit=1302", timeout=30)
    resp.raise_for_status()
    names = [p["name"] for p in resp.json()["results"]]
    _save_cache(key, names)
    return names


SINGLES_FORMATS = ["gen9ou", "gen9ubers", "gen9uu", "gen9ru", "gen9nu", "gen9pu", "gen9lc"]
DOUBLES_FORMATS = ["gen9doublesou", "gen9vgc2024regh", "gen9doublesuu"]


def _smogon_month() -> str:
    """Most recent month Smogon stats are typically published for (~2 months ago)."""
    from datetime import datetime, timedelta
    d = datetime.now().replace(day=1) - timedelta(days=60)
    return d.strftime("%Y-%m")


def _fetch_and_index_chaos(fmt: str, month: str, fmt_tag: str = "singles") -> dict:
    """
    Download one chaos file, index moves per Pokémon into individual cache files,
    and return a slim meta dict: {pokeapi_name: {"usage": float, "teammates": {name: float}}}.
    Subsequent calls return the cached meta immediately via the sentinel.
    fmt_tag is "singles" or "doubles" and scopes the per-Pokémon move cache keys.
    """
    sentinel_key = f"smogon_fetched_{fmt}_{month}"
    meta_key = f"smogon_meta_{fmt}_{month}"

    if _load_cache(sentinel_key) is not None:
        return _load_cache(meta_key) or {}

    meta = {}
    url = f"https://www.smogon.com/stats/{month}/chaos/{fmt}-0.json"
    try:
        resp = requests.get(url, timeout=25)
        if resp.status_code == 200:
            full_data = resp.json().get("data", {})
            for smogon_name, poke_data in full_data.items():
                pokeapi_name = smogon_name.lower().replace(" ", "-")

                # Index moves — first (highest-tier) format wins, scoped by singles/doubles
                moves_key = f"smogon_moves_{fmt_tag}_{pokeapi_name}"
                if _load_cache(moves_key) is None:
                    moves = sorted(poke_data.get("Moves", {}).items(), key=lambda x: -x[1])
                    top = [m[0].lower().replace(" ", "-") for m in moves[:12]]
                    if top:
                        _save_cache(moves_key, top)

                # Build slim meta (usage + teammates)
                meta[pokeapi_name] = {
                    "usage": poke_data.get("usage", 0),
                    "teammates": {
                        k.lower().replace(" ", "-"): v
                        for k, v in poke_data.get("Teammates", {}).items()
                    },
                }
            _save_cache(meta_key, meta)
    except Exception:
        pass

    _save_cache(sentinel_key, True)
    return meta


def get_smogon_moveset(name: str, formats: list[str] | None = None) -> list[str] | None:
    """
    Return top competitive move names (PokeAPI format) from Smogon usage stats.
    Pass formats=DOUBLES_FORMATS to get doubles-specific moves.
    Returns None if the Pokémon isn't found in any tracked format.
    """
    if formats is None:
        formats = SINGLES_FORMATS

    fmt_tag = "doubles" if formats == DOUBLES_FORMATS else "singles"
    per_poke_key = f"smogon_moves_{fmt_tag}_{name}"

    cached = _load_cache(per_poke_key)
    if cached is not None:
        return cached or None  # [] means not found in any format

    month = _smogon_month()
    for fmt in formats:
        _fetch_and_index_chaos(fmt, month, fmt_tag=fmt_tag)
        cached = _load_cache(per_poke_key)
        if cached:
            return cached

    _save_cache(per_poke_key, [])
    return None


def get_smogon_format_meta(fmt: str) -> dict:
    """
    Return the slim meta dict for a format, downloading it if not yet cached.
    {pokeapi_name: {"usage": float, "teammates": {pokeapi_name: float}}}
    """
    month = _smogon_month()
    cached = _load_cache(f"smogon_meta_{fmt}_{month}")
    if cached is not None:
        return cached
    return _fetch_and_index_chaos(fmt, month)


def get_pokemon_species(name: str) -> dict | None:
    key = f"species_{name}"
    cached = _load_cache(key)
    if cached is not None:
        return cached

    resp = requests.get(f"{BASE_URL}/pokemon-species/{name}", timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    _save_cache(key, data)
    return data
