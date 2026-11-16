#!/usr/bin/env python3

import configparser
import datetime
import os
from pathlib import Path
from urllib.parse import urlencode

from flask import Flask, Response, abort, redirect, render_template, jsonify, request, url_for

from src.constants import COLORS, DAYS, ICONS
from src.db.db import (
    load_food_weeks,
    load_foods,
    load_selections,
    save_food_weeks,
    save_foods,
    save_selections,
)
from src.traffic import TrafficApiError, get_station_timetables, resolve_stop_group
from src.weather_request import WeatherApiError, get_weather_snapshot
from src.pollen import get_pollen_snapshot
from src.meteogram import readable_meteogram

app = Flask(__name__)
DEV_RELOAD = os.environ.get("HOME_DISPLAY_DEV") == "1"
if DEV_RELOAD:
    app.config.update(TEMPLATES_AUTO_RELOAD=True, SEND_FILE_MAX_AGE_DEFAULT=0)


@app.context_processor
def development_context():
    return {"dev_reload": DEV_RELOAD}


@app.get("/_dev/revision")
def development_revision():
    if not DEV_RELOAD:
        abort(404)
    root = Path(app.root_path)
    files = [root / "app.py"]
    for directory in ("src", "templates", "static"):
        files.extend(p for p in (root / directory).rglob("*")
                     if p.suffix in {".py", ".html", ".css", ".js"})
    response = jsonify(revision="|".join(
        f"{p.relative_to(root)}:{p.stat().st_mtime_ns}" for p in sorted(files)
    ))
    response.headers["Cache-Control"] = "no-store"
    return response

config = configparser.ConfigParser()
config.read("app.config")

cache = dict()
cache["clock_seconds"] = False

USE_LOCAL = False
DEBUG_MODE = True
DEBUG_TEMP = 3
ENABLE_FOOD_TRACKING = False
ENABLE_POLLEN = False
DEFAULT_FORECAST_DAYS = 7
DEFAULT_RADAR_AREA = "nordic"
DEFAULT_RADAR_TYPE = "reflectivity"
RADAR_ALLOWED_AREAS = (
    "central_norway",
    "eastern_norway",
    "finnmark",
    "nordic",
    "nordland",
    "northern_nordland",
    "northwestern_norway",
    "norway",
    "southeastern_norway",
    "southern_nordland",
    "southern_norway",
    "southwestern_norway",
    "troms",
    "western_norway",
    "xband",
)
RADAR_ALLOWED_TYPES = (
    "5level_reflectivity",
    "fir_preciptype",
    "lx_reflectivity",
    "preciptype",
    "reflectivity",
)


class WeatherIcon:
    def __init__(self, icon: str, color: str):
        self.icon = icon
        self.color = color


def get_weather_icons(temperature: int) -> str:

    weather_icons = []
    if temperature <= 0:
        weather_icons.append(WeatherIcon(ICONS.snowflake, COLORS.blue))
    if temperature <= 7:
        weather_icons.append(WeatherIcon(ICONS.mitten, COLORS.blue))
        weather_icons.append(WeatherIcon(ICONS.mitten, COLORS.blue))
    if temperature <= 12:
        weather_icons.append(WeatherIcon(ICONS.hat, COLORS.blue))

    if temperature <= 0:
        weather_icons.append(WeatherIcon(ICONS.temperature_empty, COLORS.deepblue))
    elif temperature <= 7:
        weather_icons.append(WeatherIcon(ICONS.temperature_low, COLORS.lightblue))
    elif temperature <= 12:
        weather_icons.append(WeatherIcon(ICONS.temperature_half, COLORS.yellow))
    elif temperature <= 20:
        weather_icons.append(WeatherIcon(ICONS.temperature_full, COLORS.orange))
    else:
        weather_icons.append(WeatherIcon(ICONS.temperature_high, COLORS.red))

    return weather_icons


def _build_debug_forecast(days: int) -> list[dict]:
    today = datetime.date.today()
    return [
        {
            "date": (today + datetime.timedelta(days=i)).isoformat(),
            "weekday": (today + datetime.timedelta(days=i)).strftime("%a"),
            "min_temp": DEBUG_TEMP - 2,
            "max_temp": DEBUG_TEMP + 2,
            "symbol": "partly cloudy",
            "icon": "fa-cloud-sun",
        }
        for i in range(days)
    ]


def _get_weather_page_data(days: int = DEFAULT_FORECAST_DAYS) -> dict:
    if USE_LOCAL:
        return {
            "temperature": DEBUG_TEMP,
            "long_term_forecast": _build_debug_forecast(days),
            "error": "",
        }

    lund_lat = float(config["weather"]["lat"])
    lund_long = float(config["weather"]["long"])

    try:
        weather_snapshot = get_weather_snapshot(lund_lat, lund_long, days=days)
    except WeatherApiError as exc:
        return {
            "temperature": None,
            "long_term_forecast": [],
            "error": str(exc),
        }

    return {
        "temperature": round(weather_snapshot["temperature"]),
        "long_term_forecast": weather_snapshot["long_term_forecast"],
        "error": "",
    }


def require_food_tracking_enabled() -> None:
    if not ENABLE_FOOD_TRACKING:
        abort(404)


def _get_radar_page_data() -> dict:
    area = request.args.get("area", DEFAULT_RADAR_AREA).strip().lower()
    radar_type = request.args.get("type", DEFAULT_RADAR_TYPE).strip().lower()

    if area not in RADAR_ALLOWED_AREAS:
        area = DEFAULT_RADAR_AREA
    if radar_type not in RADAR_ALLOWED_TYPES:
        radar_type = DEFAULT_RADAR_TYPE

    radar_url = "https://api.met.no/weatherapi/radar/2.0/?" + urlencode(
        {
            "area": area,
            "type": radar_type,
            "content": "animation",
        }
    )

    return {
        "radar_url": radar_url,
        "radar_embed_url": "https://embed.windy.com/embed.html?" + urlencode({
            "type": "map", "location": "coordinates",
            # Focus on Skåne and southern Sweden rather than Lake Vänern.
            "lat": 56.2,
            "lon": 14.0,
            "zoom": 7, "overlay": "radar", "product": "radar",
            "level": "surface", "metricRain": "mm", "metricTemp": "°C",
            "metricWind": "m/s",
        }),
        "area": area,
        "radar_type": radar_type,
        "radar_areas": RADAR_ALLOWED_AREAS,
        "radar_types": RADAR_ALLOWED_TYPES,
    }


@app.context_processor
def inject_feature_flags():
    return {"enable_food_tracking": ENABLE_FOOD_TRACKING}


@app.get("/weather/meteogram.svg")
def meteogram_image():
    local_path = Path(app.static_folder) / "assets/meteogram.svg" if USE_LOCAL else None
    return Response(readable_meteogram(local_path), mimetype="image/svg+xml")


def _get_traffic_stop_config(prefix: str, default_label: str, default_mode: str) -> dict | None:
    if not config.has_section("traffic"):
        return None

    area_id = config.get("traffic", f"{prefix}_area_id", fallback="").strip()
    query = config.get("traffic", f"{prefix}_query", fallback="").strip()
    if not area_id and not query:
        return None

    return {
        "label": config.get("traffic", f"{prefix}_label", fallback=default_label).strip(),
        "area_id": area_id,
        "query": query,
        "transport_mode": config.get(
            "traffic", f"{prefix}_transport_mode", fallback=default_mode
        )
        .strip()
        .upper(),
    }


def _traffic_setup_message(detail: str) -> str:
    return f"Traffic board is unavailable. {detail}"


def _get_traffic_api_keys() -> tuple[str, str]:
    shared_api_key = config.get("traffic", "trafiklab_api_key", fallback="").strip()
    static_api_key = config.get(
        "traffic", "trafiklab_static_api_key", fallback=shared_api_key
    ).strip()
    realtime_api_key = config.get(
        "traffic", "trafiklab_realtime_api_key", fallback=shared_api_key
    ).strip()
    return static_api_key, realtime_api_key


def _get_traffic_page_data() -> dict:
    if not config.has_section("traffic"):
        return {
            "stations": [],
            "error": _traffic_setup_message("Add a [traffic] section in app.config."),
            "attribution": "Data from Trafiklab.se",
        }

    static_api_key, realtime_api_key = _get_traffic_api_keys()
    board_limit = config.getint("traffic", "board_limit", fallback=6)
    stop_lookup_cache_hours = config.getint("traffic", "stop_lookup_cache_hours", fallback=24)
    stops = [
        _get_traffic_stop_config("train", "Train station", "TRAIN"),
        _get_traffic_stop_config("bus", "Bus station", "BUS"),
    ]
    configured_stops = [stop for stop in stops if stop is not None]

    if not realtime_api_key:
        return {
            "stations": [],
            "error": _traffic_setup_message(
                "Add `trafiklab_realtime_api_key` under `[traffic]` in `app.config`, or keep using `trafiklab_api_key` for both."
            ),
            "attribution": "Data from Trafiklab.se",
        }

    if not configured_stops:
        return {
            "stations": [],
            "error": _traffic_setup_message(
                "Add `train_area_id`/`train_query` and/or `bus_area_id`/`bus_query` in `[traffic]`."
            ),
            "attribution": "Data from Trafiklab.se",
        }

    stations = []
    errors = []
    for stop in configured_stops:
        try:
            area_id = stop["area_id"]
            if not area_id:
                matched_stop = resolve_stop_group(
                    api_key=static_api_key or None,
                    search_value=stop["query"],
                    transport_mode=stop["transport_mode"],
                    cache_ttl_hours=stop_lookup_cache_hours,
                )
                area_id = matched_stop["id"]
                if not stop["label"]:
                    stop["label"] = matched_stop["name"]

            stations.append(
                get_station_timetables(
                    api_key=realtime_api_key,
                    label=stop["label"],
                    area_id=area_id,
                    transport_mode=stop["transport_mode"],
                    limit=board_limit,
                )
            )
        except TrafficApiError as exc:
            errors.append(f"{stop['label']}: {exc}")

    return {
        "stations": stations,
        "error": " | ".join(errors) if errors else "",
        "attribution": "Data from Trafiklab.se",
    }


@app.route("/")
def index():
    title = "Home display"

    # get_train_table_zip()

    my_clock = str(datetime.datetime.now().strftime("%H:%M"))
    my_date = str(datetime.datetime.now().strftime("%Y-%m-%d"))
    weather_data = _get_weather_page_data(days=DEFAULT_FORECAST_DAYS)
    lund_temperature = weather_data["temperature"]
    long_term_forecast = weather_data["long_term_forecast"]
    weather_error = weather_data["error"]

    if USE_LOCAL or not ENABLE_POLLEN:
        pollen = {}
        pollen_retrieved_at = None
        # pollen = {"Pollen 1": "A lot", "Pollen 2": "Not so much"}
    else:
        pollen_snapshot = get_pollen_snapshot(config["pollen"]["city"])
        pollen = pollen_snapshot["pollen"]
        retrieved_at = pollen_snapshot["retrieved_at"]
        pollen_retrieved_at = retrieved_at.strftime("%Y-%m-%d %H:%M") if retrieved_at else ""
    print(f"pollen {pollen}")

    weather_icons = get_weather_icons(lund_temperature) if lund_temperature is not None else []

    food_selections = {}
    if ENABLE_FOOD_TRACKING:
        food_selections = load_selections()
    # display_text = [
    #     f"{day}: {food["type"]} {food["food"]}" for day, food in food_selections.items()
    # ]

    data = {
        "use_local": USE_LOCAL,
        "title": title,
        "my_clock": my_clock,
        "my_date": my_date,
        "lund_temperature": lund_temperature,
        "pollen": pollen,
        "pollen_retrieved_at": pollen_retrieved_at,
        "weather_icons": weather_icons,
        "food_display": food_selections,
        "long_term_forecast": long_term_forecast,
        "weather_error": weather_error,
    }

    return render_template("weather.html", **data, **_get_radar_page_data())


@app.route("/weather/long-term")
def weather_long_term():
    weather_data = _get_weather_page_data(days=DEFAULT_FORECAST_DAYS)
    return render_template(
        "long_term_weather.html",
        title="7-day forecast",
        long_term_forecast=weather_data["long_term_forecast"],
        weather_error=weather_data["error"],
    )


@app.route("/weather/radar")
def weather_radar():
    radar_data = _get_radar_page_data()
    return render_template(
        "weather_radar.html",
        title="Rain radar",
        **radar_data,
    )


@app.route("/traffic")
def traffic():
    traffic_data = _get_traffic_page_data()
    return render_template("traffic.html", title="Traffic", **traffic_data)


@app.route("/clock")
def get_clock():
    if cache["clock_seconds"]:
        clock = str(datetime.datetime.now().strftime("%H:%M:%S"))
    else:
        clock = str(datetime.datetime.now().strftime("%H:%M"))
    return str(clock)


@app.route("/toggleclock", methods=["POST"])
def toggle_clock():
    cache["clock_seconds"] = not cache["clock_seconds"]
    print(f"clock_seconds: {cache['clock_seconds']}")
    resp = jsonify(success=True)
    print(resp)
    # return resp


@app.route("/user/")
def hello_user():
    users = ["Xuan", "Jakob", "Alvar"]


def get_foods() -> dict[str, list[str]]:
    return load_foods()


@app.route("/planning/remove_food_type/<food_type>", methods=["POST"])
def remove_food_type(food_type: str):
    require_food_tracking_enabled()
    available_foods = get_foods()
    del available_foods[food_type]
    save_foods(available_foods)
    return redirect(url_for("planning"))


@app.route("/planning/remove_dish/<food_type>/<dish_name>", methods=["POST"])
def remove_dish(food_type: str, dish_name: str):
    require_food_tracking_enabled()
    available_foods = get_foods()
    available_foods[food_type].remove(dish_name)
    save_foods(available_foods)
    return redirect(url_for("planning"))


@app.route("/planning/add_food/<food_type>", methods=["POST"])
def add_food(food_type: str):
    require_food_tracking_enabled()
    dish_name = request.form["dish"]
    available_foods = get_foods()
    available_foods[food_type].append(dish_name)
    save_foods(available_foods)
    return redirect(url_for("planning"))


@app.route("/planning/add_category", methods=["POST"])
def add_category():
    require_food_tracking_enabled()
    print(request.form["textinput"])
    available_foods = get_foods()
    available_foods[request.form["textinput"]] = []
    save_foods(available_foods)
    return redirect(url_for("planning"))


@app.route("/planning", methods=["GET", "POST"])
def planning():
    require_food_tracking_enabled()

    # FIXME: Pass the food selection db entry
    # How to share these with the /eating route?

    available_foods = get_foods()
    return render_template("planning.html", foods=available_foods)


@app.route("/eating/save_week", methods=["POST"])
def save_week():
    require_food_tracking_enabled()
    print("Save week triggered")
    food_selections = load_selections()
    food_weeks = load_food_weeks()
    foods_to_save = [entry["food"] for entry in food_selections.values()]
    current_time = str(datetime.datetime.now())
    food_weeks[current_time] = foods_to_save
    save_food_weeks(food_weeks)
    return redirect(url_for("eating_page"))


@app.route("/eating", methods=["GET", "POST"])
def eating_page():
    require_food_tracking_enabled()

    food_selections = load_selections()
    for day in DAYS:
        if not food_selections.get(day):
            food_selections[day] = {
                "type": "Placeholder type",
                "food": "Placeholder food",
            }

    if request.method == "POST":

        food_selects = {}
        for day in DAYS:
            foodtype_id = f"{day}-foodtype-plan"
            foodtype = request.form.get(foodtype_id) or "C"
            food_id = f"{day}-food-plan"
            food = request.form.get(food_id) or "D"

            print(f"Food type: {foodtype} food: {food}")
            food_selects[day] = {"type": foodtype, "food": food}

        save_selections(food_selects)
        return redirect(url_for("eating_page"))

    food_selections = load_selections()

    weeks = load_food_weeks()
    # food_types = ["&#xf00c; Fisk!", "Ägg", "Kött", "Kyckling", "Tofu"]

    available_foods_grouped = get_foods()

    return render_template(
        "eating_plan.html",
        weeks=weeks,
        available_foods_grouped=available_foods_grouped,
        food_selections=food_selections,
        # selected_food_per_day=selected_food_per_day,
    )


if __name__ == "__main__":
    app.run(debug=DEBUG_MODE, use_reloader=DEV_RELOAD or DEBUG_MODE)
