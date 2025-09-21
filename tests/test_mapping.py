import json
from pathlib import Path

from src.mapping import MappingManager
from src.tracker import create_tracker


def test_mapping_manager_prefers_non_promo(tmp_path: Path) -> None:
    tracker = create_tracker(tmp_path)
    mapping = MappingManager(tracker.config, tracker.store)
    data = [
        {"arena_id": 1, "name": "Promo", "set": "ppp", "rarity": "rare", "set_type": "promo", "released_at": "2020-01-01"},
        {"arena_id": 1, "name": "Main", "set": "main", "rarity": "rare", "set_type": "expansion", "released_at": "2021-01-01"},
        {"arena_id": 2, "name": "Other", "set": "oth", "rarity": "common", "set_type": "promo", "released_at": "2019-01-01"},
    ]
    tracker.config.paths.mapping_cache.write_text(json.dumps(data))
    count = mapping.update_from_cache()
    assert count == 2
    metadata = tracker.store.get_metadata_map()
    assert metadata[1] == ("Main", "main", "rare")
    assert metadata[2] == ("Other", "oth", "common")
