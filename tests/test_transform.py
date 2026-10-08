from src import etl

COMPETITIONS = {
    "competitions": [
        {"id": "sr:competition:1", "name": "ATP Vienna, Austria", "type": "singles", "gender": "men",
         "category": {"id": "sr:category:3", "name": "ATP"}},
        {"id": "sr:competition:2", "name": "ATP Vienna Doubles", "parent_id": "sr:competition:1",
         "type": "doubles", "gender": "men", "category": {"id": "sr:category:3", "name": "ATP"}},
        {"id": "sr:competition:3", "name": "No category cup", "type": "doubles", "gender": "women"},
        {"name": "missing id"},
    ]
}

COMPLEXES = {
    "complexes": [
        {"id": "sr:complex:1", "name": "Nacional", "venues": [
            {"id": "sr:venue:1", "name": "Court 1", "city_name": "Santiago", "country_name": "Chile",
             "country_code": "CHL", "timezone": "America/Santiago"},
            {"id": "sr:venue:2", "name": "Court 2"},
        ]},
        {"id": "sr:complex:2", "name": "Empty complex"},
    ]
}

RANKINGS = {
    "rankings": [
        {"name": "ATP", "year": 2026, "week": 38, "gender": "men", "competitor_rankings": [
            {"rank": 1, "movement": 0, "points": 7510, "competitions_played": 20,
             "competitor": {"id": "sr:competitor:1", "name": "Pavic, Mate", "country": "Croatia",
                            "country_code": "HRV", "abbreviation": "PAV"}},
            {"rank": 2, "movement": "-1", "points": "7000", "competitions_played": 18,
             "competitor": {"id": "sr:competitor:2", "name": "Doe, John"}},
            {"rank": None, "competitor": {"id": "sr:competitor:3"}},
        ]}
    ]
}


def test_transform_competitions_flattens_and_defaults():
    cats, comps, skipped = etl.transform_competitions(COMPETITIONS)
    assert cats == [{"category_id": "sr:category:3", "category_name": "ATP"}]
    assert len(comps) == 3 and skipped == 1
    by_id = {c["competition_id"]: c for c in comps}
    assert by_id["sr:competition:1"]["parent_id"] is None
    assert by_id["sr:competition:2"]["parent_id"] == "sr:competition:1"
    assert by_id["sr:competition:3"]["category_id"] is None


def test_transform_complexes_applies_defaults():
    cxs, vens, skipped = etl.transform_complexes(COMPLEXES)
    assert len(cxs) == 2 and len(vens) == 2 and skipped == 0
    court2 = next(v for v in vens if v["venue_id"] == "sr:venue:2")
    assert court2["country_code"] == "UNK" and court2["city_name"] == "Unknown"


def test_transform_rankings_coerces_types_and_skips_bad_rows():
    comps, rows, snapshots, skipped = etl.transform_rankings(RANKINGS)
    assert skipped == 1 and len(rows) == 2 and len(comps) == 2
    assert rows[1]["movement"] == -1 and rows[1]["points"] == 7000
    assert snapshots == [("ATP", 2026, 38, "men")]
    doe = next(c for c in comps if c["competitor_id"] == "sr:competitor:2")
    assert doe["abbreviation"] == "DOE" and doe["country_code"] == "UNK"


def test_long_values_are_clipped_to_column_size():
    payload = {"competitions": [{"id": "x" * 80, "name": "n" * 150, "type": "t" * 40, "gender": "g" * 30}]}
    _, comps, _ = etl.transform_competitions(payload)
    assert len(comps[0]["competition_id"]) == 50 and len(comps[0]["competition_name"]) == 100
