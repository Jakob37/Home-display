#!/usr/bin/env python3

from collections import defaultdict
from datetime import date, datetime, timedelta
from threading import Lock

import requests

REQUEST_TIMEOUT_SECONDS = 10
FORECAST_CACHE_TTL = timedelta(minutes=30)
LOCATION_FORECAST = "locationforecast/2.0/compact"
SUBSEASONAL_FORECAST = "subseasonal/1.0/complete"
LOCATION_FORECAST_DAYS = 10
_forecast_cache: dict[tuple[str, float, float], dict[str, datetime | list[dict]]] = {}
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


def _get_cached_forecast(
    cache_key: tuple[str, float, float],
    max_age: timedelta | None = FORECAST_CACHE_TTL,
) -> list[dict] | None:
    with _forecast_cache_lock:
        cached_forecast = _forecast_cache.get(cache_key)

    if cached_forecast is None:
        return None

    if max_age is not None and datetime.now() - cached_forecast["fetched_at"] > max_age:
        return None

    return cached_forecast["timeseries"]


def _store_cached_forecast(
    cache_key: tuple[str, float, float], timeseries: list[dict]
) -> None:
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


def _request_forecast(cache_key: tuple[str, float, float]) -> list[dict]:
    product, latitude, longitude = cache_key
    url = f"https://api.met.no/weatherapi/{product}"
    headers = {"User-Agent": "Home-display/1.0 github.com/Jakob37/Home-display"}
    params = {"lat": latitude, "lon": longitude}
    response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    timeseries = response.json()["properties"]["timeseries"]
    if not isinstance(timeseries, list) or not timeseries:
        raise ValueError("Forecast response contains no timeseries.")
    return timeseries


def _fetch_forecast(
    latitude: float | str, longitude: float | str, product: str = LOCATION_FORECAST
) -> list[dict]:
    cache_key = (product, _normalize_coordinate(latitude), _normalize_coordinate(longitude))
    cached_timeseries = _get_cached_forecast(cache_key)
    if cached_timeseries is not None:
        return cached_timeseries

    try:
        timeseries = _request_forecast(cache_key)
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        stale_timeseries = _get_cached_forecast(cache_key, max_age=None)
        if stale_timeseries is not None:
            return stale_timeseries
        _raise_clean_api_error(exc)

    _store_cached_forecast(cache_key, timeseries)
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


def _build_long_term_forecast(timeseries: list[dict], days: int, today: date) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)

    for entry in timeseries:
        date_key = entry["time"][:10]
        grouped[date_key].append(entry)

    forecast = []
    end = today + timedelta(days=days)
    for date_key in sorted(grouped.keys()):
        date_obj = date.fromisoformat(date_key)
        if not today <= date_obj < end:
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

    return forecast


def _merge_daily_outlook(
    forecast: list[dict], outlook: list[dict], today: date, days: int
) -> list[dict]:
    by_date = {entry["date"]: entry for entry in forecast}
    end = today + timedelta(days=days)
    for entry in outlook:
        date_key = entry["time"][:10]
        day = date.fromisoformat(date_key)
        if not today <= day < end:
            continue

        data = entry.get("data") or {}
        daily = (data.get("next_24_hours") or {}).get("details") or {}
        # Use the same 24-hour probability on dates from either forecast.
        probability = daily.get("probability_of_precipitation")
        chance = (
            round(probability)
            if isinstance(probability, (int, float)) and 0 <= probability <= 100
            else None
        )
        if date_key in by_date:
            by_date[date_key] = {**by_date[date_key], "precipitation_chance": chance}
            continue

        low = daily.get("air_temperature_min")
        high = daily.get("air_temperature_max")
        if low is not None and high is not None:
            by_date[date_key] = {
                "date": date_key,
                "weekday": day.strftime("%a"),
                "min_temp": round(low),
                "max_temp": round(high),
                "precipitation_chance": chance,
                "is_outlook": True,
            }
    return [by_date[date_key] for date_key in sorted(by_date)]


def _get_daily_forecast(
    timeseries: list[dict], latitude: float | str, longitude: float | str, days: int
) -> list[dict]:
    today = datetime.now().date()
    forecast = _build_long_term_forecast(timeseries, min(days, LOCATION_FORECAST_DAYS), today)
    try:
        outlook = _fetch_forecast(latitude, longitude, SUBSEASONAL_FORECAST)
        return _merge_daily_outlook(forecast, outlook, today, days)
    except (WeatherApiError, AttributeError, KeyError, TypeError, ValueError):
        # A separate outlook failure still leaves the Locationforecast days available.
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
        return _get_daily_forecast(timeseries, latitude, longitude, days)
    except (KeyError, TypeError, ValueError) as exc:
        _raise_clean_api_error(exc)


def get_weather_snapshot(
    latitude: float | str, longitude: float | str, days: int = 7
) -> dict[str, float | list[dict]]:
    timeseries = _fetch_forecast(latitude, longitude)
    try:
        return {
            "temperature": _get_temperature_from_timeseries(timeseries),
            "long_term_forecast": _get_daily_forecast(timeseries, latitude, longitude, days),
        }
    except (KeyError, TypeError, ValueError) as exc:
        _raise_clean_api_error(exc)
