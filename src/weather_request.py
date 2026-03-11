#!/usr/bin/env python3

from collections import defaultdict
from datetime import datetime

import requests


def _symbol_to_icon(symbol: str) -> str:
    lower_symbol = symbol.lower()
    if "thunder" in lower_symbol:
        return "fa-bolt"
    if "snow" in lower_symbol or "sleet" in lower_symbol:
        return "fa-snowflake"
    if "rain" in lower_symbol or "drizzle" in lower_symbol:
        return "fa-cloud-rain"
    if "fog" in lower_symbol:
        return "fa-smog"
    if "partlycloudy" in lower_symbol:
        return "fa-cloud-sun"
    if "cloudy" in lower_symbol:
        return "fa-cloud"
    if "clearsky" in lower_symbol:
        return "fa-sun"
    return "fa-cloud"


def _fetch_forecast(latitude: float, longitude: float) -> list[dict]:
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={latitude}&lon={longitude}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data["properties"]["timeseries"]


def _get_temperature_from_timeseries(timeseries: list[dict]) -> float:
    current_time = datetime.now().isoformat(timespec="hours")
    for entry in timeseries:
        time = entry["time"]
        if time.startswith(current_time):
            return entry["data"]["instant"]["details"]["air_temperature"]
    raise ValueError(f"Current time not found: {current_time}")


def _build_long_term_forecast(timeseries: list[dict], days: int = 10) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)

    for entry in timeseries:
        date_key = entry["time"][:10]
        grouped[date_key].append(entry)

    forecast = []
    today = datetime.now().date()
    for date_key in sorted(grouped.keys()):
        date_obj = datetime.fromisoformat(date_key).date()
        if date_obj < today:
            continue

        day_entries = grouped[date_key]
        temperatures = [
            item["data"]["instant"]["details"]["air_temperature"] for item in day_entries
        ]

        symbol = "cloudy"
        for item in day_entries:
            next_6 = item["data"].get("next_6_hours", {}).get("summary", {}).get("symbol_code")
            next_1 = item["data"].get("next_1_hours", {}).get("summary", {}).get("symbol_code")
            symbol = next_6 or next_1 or symbol
            if symbol != "cloudy":
                break

        forecast.append(
            {
                "date": date_key,
                "weekday": date_obj.strftime("%a"),
                "min_temp": round(min(temperatures)),
                "max_temp": round(max(temperatures)),
                "symbol": symbol.replace("_", " "),
                "icon": _symbol_to_icon(symbol),
            }
        )

        if len(forecast) >= days:
            break

    return forecast


def get_temperature(latitude: float, longitude: float) -> float:
    timeseries = _fetch_forecast(latitude, longitude)
    return _get_temperature_from_timeseries(timeseries)


def get_long_term_forecast(latitude: float, longitude: float, days: int = 10) -> list[dict]:
    timeseries = _fetch_forecast(latitude, longitude)
    return _build_long_term_forecast(timeseries, days=days)


def get_weather_snapshot(
    latitude: float, longitude: float, days: int = 10
) -> dict[str, float | list[dict]]:
    timeseries = _fetch_forecast(latitude, longitude)
    return {
        "temperature": _get_temperature_from_timeseries(timeseries),
        "long_term_forecast": _build_long_term_forecast(timeseries, days=days),
    }
