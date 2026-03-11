Raspberry pi based node for a home display.

## Usage

1. Create the config file. Copy `example.config` to `app.config`, then update `[weather]` and `[pollen]` values for your location.
2. Set up Python deps (venv recommended). Run `python3 -m venv .venv`, then `. .venv/bin/activate`, then `pip install -r requirements.txt`.
3. Start the app. Run `. ./env.sh`, then `flask run` or `python3 app.py`.

Open `http://127.0.0.1:5000/` in a browser.

## Traffic View

The `/traffic` page can show live departures and arrivals for one configured train station and one configured bus station.

1. Add a Trafiklab API key in `[traffic]` in `app.config`.
2. Set either `train_query` / `bus_query` or the exact `train_area_id` / `bus_area_id`.
3. If you use the `*_query` fields, the app resolves the correct Trafiklab stop group automatically.
4. Open the traffic view from the train icon in the header.

Trafiklab docs:
- Stop Lookup: `https://www.trafiklab.se/api/our-apis/trafiklab-realtime-apis/stop-lookup/`
- Timetables: `https://www.trafiklab.se/api/our-apis/trafiklab-realtime-apis/timetables/`

## Feature Flags

Food tracking is currently disabled. To enable it, set `ENABLE_FOOD_TRACKING = True` in `app.py`.
