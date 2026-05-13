from constants import ALL_TYPES, STAT_ORDER
from type_chart import get_defensive_profile, get_team_weaknesses, get_team_coverage, build_type_chart


def analyze_team(team: list[dict]) -> dict:
    if not team:
        return {}

    # Weakness counts
    weakness_counts = get_team_weaknesses(team)
    critical_weaknesses = [t for t, c in weakness_counts.items() if c >= 3]

    # Offensive coverage from all move types across the team
    move_types = []
    for pokemon in team:
        for move_entry in pokemon.get("moves", [])[:20]:  # sample first 20 moves
            move_name = move_entry["move"]["name"]
            # We'll use the pokemon's own types as proxy for move types
            # (move type lookup would require extra API calls per move)
        for slot in pokemon["types"]:
            move_types.append(slot["type"]["name"])

    chart = build_type_chart()
    covered_types = set()
    for move_type in move_types:
        if move_type not in chart:
            continue
        for defender, mult in chart[move_type].items():
            if mult >= 2.0:
                covered_types.add(defender)

    uncovered_types = [t for t in ALL_TYPES if t not in covered_types]

    # Stat summary
    stat_totals: dict[str, list[int]] = {s: [] for s in STAT_ORDER}
    for pokemon in team:
        for stat_entry in pokemon["stats"]:
            stat_name = stat_entry["stat"]["name"]
            if stat_name in stat_totals:
                stat_totals[stat_name].append(stat_entry["base_stat"])

    stat_summary = {}
    for stat, values in stat_totals.items():
        if values:
            stat_summary[stat] = {
                "avg": round(sum(values) / len(values), 1),
                "max": max(values),
            }

    # Role balance via base stat thresholds
    roles = {"physical_attacker": 0, "special_attacker": 0, "tank": 0, "speedster": 0}
    for pokemon in team:
        stats = {s["stat"]["name"]: s["base_stat"] for s in pokemon["stats"]}
        if stats.get("speed", 0) >= 100:
            roles["speedster"] += 1
        if stats.get("attack", 0) >= 100:
            roles["physical_attacker"] += 1
        if stats.get("special-attack", 0) >= 100:
            roles["special_attacker"] += 1
        if stats.get("hp", 0) >= 90 or stats.get("defense", 0) >= 90 or stats.get("special-defense", 0) >= 90:
            roles["tank"] += 1

    return {
        "weakness_counts": weakness_counts,
        "critical_weaknesses": critical_weaknesses,
        "offensive_coverage": sorted(covered_types),
        "uncovered_types": uncovered_types,
        "stat_summary": stat_summary,
        "role_balance": roles,
    }
