#!/usr/bin/env python3

from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock

import requests

REQUEST_TIMEOUT_SECONDS = 10
FORECAST_CACHE_TTL = timedelta(minutes=30)
_forecast_cache: dict[tuple[float, float], dict[str, datetime | list[dict]]] = {}
_forecast_cache_lock = Lock()


class WeatherApiError(Exception):
    pass


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


def _normalize_coordinate(value: float | str) -> float:
    return round(float(value), 4)


def _get_cache_key(latitude: float | str, longitude: float | str) -> tuple[float, float]:
    return (_normalize_coordinate(latitude), _normalize_coordinate(longitude))


def _get_cached_forecast(
    latitude: float | str,
    longitude: float | str,
    max_age: timedelta | None = FORECAST_CACHE_TTL,
) -> list[dict] | None:
    cache_key = _get_cache_key(latitude, longitude)
    with _forecast_cache_lock:
        cached_forecast = _forecast_cache.get(cache_key)

    if cached_forecast is None:
        return None

    if max_age is not None and datetime.now() - cached_forecast["fetched_at"] > max_age:
        return None

    return cached_forecast["timeseries"]


def _store_cached_forecast(
    latitude: float | str, longitude: float | str, timeseries: list[dict]
) -> None:
    cache_key = _get_cache_key(latitude, longitude)
    with _forecast_cache_lock:
        _forecast_cache[cache_key] = {
            "fetched_at": datetime.now(),
            "timeseries": timeseries,
        }


def _raise_clean_api_error(exc: Exception) -> None:
    if isinstance(exc, requests.Timeout):
        raise WeatherApiError("Weather data is temporarily unavailable. The forecast timed out.") from exc
    if isinstance(exc, requests.RequestException):
        raise WeatherApiError("Weather data is temporarily unavailable.") from exc
    raise WeatherApiError("Weather data could not be parsed.") from exc


def _request_forecast(latitude: float | str, longitude: float | str) -> list[dict]:
    normalized_latitude = _normalize_coordinate(latitude)
    normalized_longitude = _normalize_coordinate(longitude)
    url = (
        "https://api.met.no/weatherapi/locationforecast/2.0/compact"
        f"?lat={normalized_latitude}&lon={normalized_longitude}"
    )
    headers = {"User-Agent": "Home-display/1.0"}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    return data["properties"]["timeseries"]


def _fetch_forecast(latitude: float | str, longitude: float | str) -> list[dict]:
    cached_timeseries = _get_cached_forecast(latitude, longitude)
    if cached_timeseries is not None:
        return cached_timeseries

    try:
        timeseries = _request_forecast(latitude, longitude)
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        stale_timeseries = _get_cached_forecast(latitude, longitude, max_age=None)
        if stale_timeseries is not None:
            return stale_timeseries
        _raise_clean_api_error(exc)

    _store_cached_forecast(latitude, longitude, timeseries)
    return timeseries


def _get_temperature_from_timeseries(timeseries: list[dict]) -> float:
    for entry in timeseries:
        temperature = (
            entry.get("data", {})
            .get("instant", {})
            .get("details", {})
            .get("air_temperature")
        )
        if temperature is not None:
            return temperature
    raise ValueError("Current temperature not found in forecast response.")


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
    try:
        return _get_temperature_from_timeseries(timeseries)
    except (KeyError, TypeError, ValueError) as exc:
        _raise_clean_api_error(exc)


def get_long_term_forecast(
    latitude: float | str, longitude: float | str, days: int = 7
) -> list[dict]:
    timeseries = _fetch_forecast(latitude, longitude)
    try:
        return _build_long_term_forecast(timeseries, days=days)
    except (KeyError, TypeError, ValueError) as exc:
        _raise_clean_api_error(exc)


def get_weather_snapshot(
    latitude: float | str, longitude: float | str, days: int = 7
) -> dict[str, float | list[dict]]:
    timeseries = _fetch_forecast(latitude, longitude)
    try:
        return {
            "temperature": _get_temperature_from_timeseries(timeseries),
            "long_term_forecast": _build_long_term_forecast(timeseries, days=days),
        }
    except (KeyError, TypeError, ValueError) as exc:
        _raise_clean_api_error(exc)
