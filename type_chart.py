from api import get_type
from constants import ALL_TYPES

_type_chart: dict[str, dict[str, float]] | None = None


def build_type_chart() -> dict[str, dict[str, float]]:
    """Build 18x18 attacker->defender->multiplier matrix."""
    global _type_chart
    if _type_chart is not None:
        return _type_chart

    chart: dict[str, dict[str, float]] = {t: {d: 1.0 for d in ALL_TYPES} for t in ALL_TYPES}

    for attacker in ALL_TYPES:
        data = get_type(attacker)
        relations = data["damage_relations"]

        for entry in relations.get("double_damage_to", []):
            defender = entry["name"]
            if defender in chart[attacker]:
                chart[attacker][defender] = 2.0

        for entry in relations.get("half_damage_to", []):
            defender = entry["name"]
            if defender in chart[attacker]:
                chart[attacker][defender] = 0.5

        for entry in relations.get("no_damage_to", []):
            defender = entry["name"]
            if defender in chart[attacker]:
                chart[attacker][defender] = 0.0

    _type_chart = chart
    return chart


def get_defensive_profile(types: list[str]) -> dict[str, float]:
    """Return multiplier per attacking type for a Pokemon with the given types."""
    chart = build_type_chart()
    profile: dict[str, float] = {}
    for attacker in ALL_TYPES:
        multiplier = 1.0
        for defender in types:
            if defender in chart[attacker]:
                multiplier *= chart[attacker][defender]
        profile[attacker] = multiplier
    return profile


def get_team_weaknesses(team: list[dict]) -> dict[str, int]:
    """Count how many team members are weak (>1.0x) to each type."""
    counts: dict[str, int] = {t: 0 for t in ALL_TYPES}
    for pokemon in team:
        types = [slot["type"]["name"] for slot in pokemon["types"]]
        profile = get_defensive_profile(types)
        for attacker, mult in profile.items():
            if mult > 1.0:
                counts[attacker] += 1
    return counts


def get_team_coverage(team_moves: list[str]) -> list[str]:
    """Return types the team can hit super effectively given a list of move types."""
    chart = build_type_chart()
    covered = set()
    for move_type in team_moves:
        if move_type not in chart:
            continue
        for defender, mult in chart[move_type].items():
            if mult >= 2.0:
                covered.add(defender)
    return sorted(covered)
