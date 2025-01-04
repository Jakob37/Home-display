import json


def save_selections(selections):
    with open("selections.json", "w") as fh:
        json.dump(selections, fh)


def load_selections():
    try:
        with open("selections.json", "r") as fh:
            selections = json.load(f)
            return selections
    except FileNotFoundError:
        print("File not found")
        return {}
