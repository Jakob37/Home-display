import json
from pathlib import Path

OUT_BASE = Path("data")
SELECTIONS_PATH = OUT_BASE / "selections.json"
FOODS_PATH = OUT_BASE / "foods.json"
FOOD_WEEKS_PATH = OUT_BASE / "food_weeks.json"
TRAFFIC_STOP_CACHE_PATH = OUT_BASE / "traffic_stop_cache.json"


def save_json(json_dict: dict[str, any], path: Path):
    print(f"Writing {json_dict} to {path}")
    if not OUT_BASE.exists():
        OUT_BASE.mkdir(parents=True)
    with open(path, "w") as fh:
        json.dump(json_dict, fh)


def load_json(path: Path) -> dict[str, any]:
    try:
        with open(path, "r") as fh:
            selections = json.load(fh) or {}
            return selections
    except FileNotFoundError:
        print("File not found, creating empty")
        empty = {}
        save_json(empty, path)
        return empty


def save_selections(selections):
    save_json(selections, SELECTIONS_PATH)


def load_selections() -> dict[str, any]:
    return load_json(SELECTIONS_PATH)


def save_foods(foods):
    save_json(foods, FOODS_PATH)


def load_foods() -> dict[str, any]:
    return load_json(FOODS_PATH)


def save_food_weeks(food_weeks: dict[str, any]) -> None:
    return save_json(food_weeks, FOOD_WEEKS_PATH)


def load_food_weeks() -> dict[str, any]:
    return load_json(FOOD_WEEKS_PATH)


def save_traffic_stop_cache(cache_entries: dict[str, any]) -> None:
    save_json(cache_entries, TRAFFIC_STOP_CACHE_PATH)


def load_traffic_stop_cache() -> dict[str, any]:
    cache_entries = load_json(TRAFFIC_STOP_CACHE_PATH)
    return cache_entries if isinstance(cache_entries, dict) else {}
