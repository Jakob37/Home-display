import json
from pathlib import Path

OUT_BASE = Path("data")
SELECTIONS_PATH = OUT_BASE / "selections.json"
FOODS_PATH = OUT_BASE / "foods.json"


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
        print("File not found")
        return {}


def save_selections(selections):
    save_json(selections, SELECTIONS_PATH)


def load_selections() -> dict[str, any]:
    return load_json(SELECTIONS_PATH)


def save_foods(foods):
    save_json(foods, FOODS_PATH)


def load_foods() -> dict[str, any]:
    return load_json(FOODS_PATH)
