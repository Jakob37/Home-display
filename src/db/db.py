import json
from pathlib import Path

OUT_BASE = Path("data")
SELECTIONS_PATH = OUT_BASE / "selections.json"


def save_selections(selections):
    print(f"Writing {selections} to {SELECTIONS_PATH}")
    if not OUT_BASE.exists():
        OUT_BASE.mkdir(parents=True)
    with open(SELECTIONS_PATH, "w") as fh:
        json.dump(selections, fh)


def load_selections():
    try:
        with open(SELECTIONS_PATH, "r") as fh:
            selections = json.load(fh)
            return selections
    except FileNotFoundError:
        print("File not found")
        return {}
