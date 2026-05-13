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
