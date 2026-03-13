Raspberry pi based node for a home display.

## Usage

1. Create the config file. Copy `example.config` to `app.config`, then update `[weather]` and `[pollen]` values for your location.
2. Set up Python deps (venv recommended). Run `python3 -m venv .venv`, then `. .venv/bin/activate`, then `pip install -r requirements.txt`.
3. Start the app. Run `. ./env.sh`, then `flask run` or `python3 app.py`.

Open `http://127.0.0.1:5000/` in a browser.

## Traffic View

The `/traffic` page can show live departures and arrivals for one configured train station and one configured bus station.

1. Add a Trafiklab realtime key in `[traffic]` in `app.config` using `trafiklab_realtime_api_key`.
2. If you resolve stops from `train_query` / `bus_query`, also add `trafiklab_static_api_key`. If you already know the exact `train_area_id` / `bus_area_id`, you can skip the static key entirely.
3. The app still accepts `trafiklab_api_key` as a shared fallback for both calls.
4. Stop lookup results are cached on disk in `data/traffic_stop_cache.json` and refresh every 24 hours by default. You can change that with `stop_lookup_cache_hours`.
5. Open the traffic view from the train icon in the header.

Trafiklab docs:
- Stop Lookup: `https://www.trafiklab.se/api/our-apis/trafiklab-realtime-apis/stop-lookup/`
- Timetables: `https://www.trafiklab.se/api/our-apis/trafiklab-realtime-apis/timetables/`

## Feature Flags

Food tracking is currently disabled. To enable it, set `ENABLE_FOOD_TRACKING = True` in `app.py`.
