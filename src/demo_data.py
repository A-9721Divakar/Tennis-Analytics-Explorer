"""Synthetic demo data shaped exactly like the Sportradar JSON payloads.

IMPORTANT: everything generated here is FICTIONAL sample data (player names,
points, rankings). It exists so the app can be explored without an API key and
so the whole pipeline (transform -> load -> queries -> dashboard) can be tested
offline. All IDs are prefixed with ``demo:`` so demo rows are easy to detect
and are replaced automatically when real API data is loaded.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List

SEED = 2026

FIRST_NAMES = [
    "Alex", "Marco", "Luca", "Mateo", "Jonas", "Ivan", "Karim", "Diego", "Nikola", "Tomas",
    "Andre", "Felix", "Hugo", "Oscar", "Pablo", "Rafael", "Viktor", "Yuki", "Arjun", "Liam",
    "Sofia", "Elena", "Maria", "Anna", "Chloe", "Ines", "Petra", "Mila", "Nora", "Zoe",
    "Aiko", "Priya", "Lucia", "Emma", "Clara", "Freya", "Ivana", "Katya", "Renata", "Sara",
]
LAST_NAMES = [
    "Almeida", "Bergman", "Castillo", "Dvorak", "Eriksen", "Fontaine", "Grbic", "Hartmann",
    "Iglesias", "Jovanovic", "Kovac", "Lindqvist", "Moretti", "Novak", "Ortega", "Petrov",
    "Quintero", "Romero", "Sato", "Tanaka", "Ulrich", "Vargas", "Weber", "Xavier", "Yilmaz",
    "Zielinski", "Bianchi", "Carvalho", "Delgado", "Esposito", "Fischer", "Gallo", "Horvat",
    "Ivanov", "Jansen", "Klein", "Lopez", "Maier", "Nakamura", "Olsen", "Pereira", "Ramos",
    "Silva", "Torres", "Urban", "Vidal", "Wagner", "Yamada", "Zhang", "Kumar",
]
COUNTRIES = [
    ("Croatia", "HRV"), ("Australia", "AUS"), ("El Salvador", "SLV"), ("Chile", "CHL"),
    ("Spain", "ESP"), ("Argentina", "ARG"), ("United States", "USA"), ("France", "FRA"),
    ("Germany", "DEU"), ("Italy", "ITA"), ("Great Britain", "GBR"), ("Netherlands", "NLD"),
    ("India", "IND"), ("Japan", "JPN"), ("Brazil", "BRA"), ("Austria", "AUT"),
    ("Colombia", "COL"), ("Serbia", "SRB"), ("Poland", "POL"), ("Canada", "CAN"),
    ("Czech Republic", "CZE"), ("Mexico", "MEX"), ("Sweden", "SWE"), ("Belgium", "BEL"),
    ("Switzerland", "CHE"), ("Greece", "GRC"), ("China", "CHN"), ("South Korea", "KOR"),
    ("Uruguay", "URY"), ("Ecuador", "ECU"),
]
# city, country, code, timezone
CITIES = [
    ("Vienna", "Austria", "AUT", "Europe/Vienna"),
    ("Santiago", "Chile", "CHL", "America/Santiago"),
    ("Zagreb", "Croatia", "HRV", "Europe/Zagreb"),
    ("Melbourne", "Australia", "AUS", "Australia/Melbourne"),
    ("Madrid", "Spain", "ESP", "Europe/Madrid"),
    ("Buenos Aires", "Argentina", "ARG", "America/Argentina/Buenos_Aires"),
    ("New York", "United States", "USA", "America/New_York"),
    ("Paris", "France", "FRA", "Europe/Paris"),
    ("Munich", "Germany", "DEU", "Europe/Berlin"),
    ("Rome", "Italy", "ITA", "Europe/Rome"),
    ("London", "Great Britain", "GBR", "Europe/London"),
    ("Rotterdam", "Netherlands", "NLD", "Europe/Amsterdam"),
    ("Pune", "India", "IND", "Asia/Kolkata"),
    ("Tokyo", "Japan", "JPN", "Asia/Tokyo"),
    ("Sao Paulo", "Brazil", "BRA", "America/Sao_Paulo"),
    ("Bogota", "Colombia", "COL", "America/Bogota"),
    ("Belgrade", "Serbia", "SRB", "Europe/Belgrade"),
    ("Warsaw", "Poland", "POL", "Europe/Warsaw"),
    ("Toronto", "Canada", "CAN", "America/Toronto"),
    ("Prague", "Czech Republic", "CZE", "Europe/Prague"),
    ("Mexico City", "Mexico", "MEX", "America/Mexico_City"),
    ("Stockholm", "Sweden", "SWE", "Europe/Stockholm"),
    ("Brussels", "Belgium", "BEL", "Europe/Brussels"),
    ("Basel", "Switzerland", "CHE", "Europe/Zurich"),
    ("Athens", "Greece", "GRC", "Europe/Athens"),
    ("Shanghai", "China", "CHN", "Asia/Shanghai"),
    ("Seoul", "South Korea", "KOR", "Asia/Seoul"),
    ("Montevideo", "Uruguay", "URY", "America/Montevideo"),
    ("Guayaquil", "Ecuador", "ECU", "America/Guayaquil"),
    ("Salzburg", "Austria", "AUT", "Europe/Vienna"),
]
# (id suffix, name, gender)
CATEGORIES = [
    ("3", "ATP", "men"),
    ("6", "WTA", "women"),
    ("785", "ITF Men", "men"),
    ("213", "ITF Women", "women"),
    ("2", "Challenger", "men"),
    ("1024", "Exhibition", "mixed"),
]
COMPETITION_SUFFIXES = [("Singles", "singles"), ("Doubles", "doubles"), ("Qualification", "singles")]


def _competitions(rng: random.Random) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    counter = 1
    for cat_id, cat_name, gender in CATEGORIES:
        category = {"id": f"demo:category:{cat_id}", "name": cat_name}
        cities = rng.sample(CITIES, 14 if cat_name in {"ATP", "WTA"} else 9)
        for city, country, _code, _tz in cities:
            parent_id = f"demo:competition:{counter}"
            counter += 1
            parent_name = f"{cat_name} {city}"
            items.append(
                {
                    "id": parent_id,
                    "name": parent_name,
                    "type": "mixed",
                    "gender": gender,
                    "category": category,
                }
            )
            for suffix, comp_type in COMPETITION_SUFFIXES:
                items.append(
                    {
                        "id": f"demo:competition:{counter}",
                        "name": f"{parent_name}, {country} {suffix}",
                        "parent_id": parent_id,
                        "type": comp_type,
                        "gender": gender,
                        "category": category,
                    }
                )
                counter += 1
    return {"generated_at": "demo", "competitions": items}


def _complexes(rng: random.Random) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    venue_counter = 1
    for idx, (city, country, code, tz) in enumerate(CITIES, start=1):
        name = "Nacional" if city == "Santiago" else f"{city} Tennis Centre"
        venue_count = 3 if city == "Santiago" else rng.randint(1, 4)
        venues = []
        for v in range(1, venue_count + 1):
            label = "Centre Court" if v == 1 else f"Court {v}"
            venues.append(
                {
                    "id": f"demo:venue:{venue_counter}",
                    "name": f"{name} - {label}",
                    "city_name": city,
                    "country_name": country,
                    "country_code": code,
                    "timezone": tz,
                }
            )
            venue_counter += 1
        items.append({"id": f"demo:complex:{idx}", "name": name, "venues": venues})
    return {"generated_at": "demo", "complexes": items}


def _players(rng: random.Random, count: int) -> List[Dict[str, Any]]:
    players, seen = [], set()
    while len(players) < count:
        name = f"{rng.choice(LAST_NAMES)}, {rng.choice(FIRST_NAMES)}"
        if name in seen:
            continue
        seen.add(name)
        country, code = rng.choice(COUNTRIES)
        players.append(
            {
                "id": f"demo:competitor:{len(players) + 1000}",
                "name": name,
                "country": country,
                "country_code": code,
                "abbreviation": name.split(",")[0][:3].upper(),
                "base": max(400, int(9000 * (0.965 ** len(players)) + rng.randint(-150, 150))),
                "played": rng.randint(8, 30),
            }
        )
    return players


def _rankings(rng: random.Random, weeks=(36, 37, 38), year: int = 2026) -> Dict[str, Any]:
    rankings = []
    for ranking_name, gender in (("ATP", "men"), ("WTA", "women")):
        players = _players(rng, 100)
        for p in players:  # unique ids per gender
            p["id"] = f"{p['id']}:{gender[0]}"
        previous: Dict[str, int] = {}
        for week in weeks:
            scored = []
            for p in players:
                jitter = rng.randint(-90, 90) if rng.random() > 0.3 else 0
                p["base"] = max(300, p["base"] + jitter)
                scored.append((p["base"], p))
            scored.sort(key=lambda t: -t[0])
            entries = []
            for position, (points, p) in enumerate(scored, start=1):
                movement = previous.get(p["id"], position) - position
                entries.append(
                    {
                        "rank": position,
                        "movement": movement,
                        "points": points,
                        "competitions_played": p["played"] + (week - weeks[0]),
                        "competitor": {
                            "id": p["id"],
                            "name": p["name"],
                            "country": p["country"],
                            "country_code": p["country_code"],
                            "abbreviation": p["abbreviation"],
                        },
                    }
                )
                previous[p["id"]] = position
            rankings.append(
                {
                    "type_id": 1,
                    "name": ranking_name,
                    "year": year,
                    "week": week,
                    "gender": gender,
                    "competitor_rankings": entries,
                }
            )
    return {"generated_at": "demo", "rankings": rankings}


def build_demo_payloads(seed: int = SEED) -> Dict[str, Dict[str, Any]]:
    """Return {'competitions': ..., 'complexes': ..., 'rankings': ...} demo payloads."""
    rng = random.Random(seed)
    return {
        "competitions": _competitions(rng),
        "complexes": _complexes(rng),
        "rankings": _rankings(rng),
    }
