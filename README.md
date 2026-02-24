Raspberry pi based node for a home display.

## Usage

1. Create the config file. Copy `example.config` to `app.config`, then update `[weather]` and `[pollen]` values for your location.
2. Set up Python deps (venv recommended). Run `python3 -m venv .venv`, then `. .venv/bin/activate`, then `pip install -r requirements.txt`.
3. Start the app. Run `. ./env.sh`, then `flask run` or `python3 app.py`.

Open `http://127.0.0.1:5000/` in a browser.

## Feature Flags

Food tracking is currently disabled. To enable it, set `ENABLE_FOOD_TRACKING = True` in `app.py`.
