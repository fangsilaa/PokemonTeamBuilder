import anthropic


def get_team_advice(analysis: dict, team: list[dict]) -> str:
    team_names = [p["name"].capitalize() for p in team]
    team_types = []
    for p in team:
        types = "/".join(slot["type"]["name"].capitalize() for slot in p["types"])
        team_types.append(f"{p['name'].capitalize()} ({types})")

    critical = analysis.get("critical_weaknesses", [])
    coverage = analysis.get("offensive_coverage", [])
    uncovered = analysis.get("uncovered_types", [])
    roles = analysis.get("role_balance", {})
    stat_summary = analysis.get("stat_summary", {})

    stat_lines = []
    for stat, vals in stat_summary.items():
        stat_lines.append(f"  {stat}: avg {vals['avg']}, max {vals['max']}")

    user_message = f"""Team: {', '.join(team_types)}

Offensive coverage (types hit super effectively): {', '.join(coverage) if coverage else 'none'}
Types with no super effective coverage: {', '.join(uncovered) if uncovered else 'none'}

Critical weaknesses (3+ team members weak): {', '.join(critical) if critical else 'none'}

Stat spread:
{chr(10).join(stat_lines)}

Role balance: {roles}

Please provide:
1. Overall team assessment (2-3 sentences)
2. Top 2-3 weaknesses or gaps to address
3. One or two specific Pokémon swap suggestions with reasoning"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="Act as a competitive Pokémon team analyst. Be concise, specific, and practical.",
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text
