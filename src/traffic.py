#!/usr/bin/env python3

from datetime import datetime, timedelta
from urllib.parse import quote

import requests

from src.db.db import load_traffic_stop_cache, save_traffic_stop_cache


TRAFIKLAB_BASE_URL = "https://realtime-api.trafiklab.se/v1"
DEFAULT_STOP_LOOKUP_CACHE_HOURS = 24


class TrafficApiError(Exception):
    pass


def _raise_clean_api_error(
    exc: requests.RequestException, config_hint: str = "Trafiklab API key"
) -> None:
    response = getattr(exc, "response", None)
    if response is not None and response.status_code in {401, 403}:
        raise TrafficApiError(
            f"Traffic data is unavailable. Add a valid {config_hint} in app.config."
        ) from exc
    if isinstance(exc, requests.Timeout):
        raise TrafficApiError("Traffic data is temporarily unavailable. Trafiklab timed out.") from exc
    raise TrafficApiError("Traffic data is temporarily unavailable.") from exc


def _normalize_stop_name(value: str) -> str:
    return " ".join(value.lower().split())


def _get_stop_lookup_cache_key(search_value: str, transport_mode: str | None) -> str:
    return f"{transport_mode or 'ANY'}::{_normalize_stop_name(search_value)}"


def _get_cached_stop_group(
    search_value: str, transport_mode: str | None, cache_ttl_hours: int
) -> dict | None:
    cache_key = _get_stop_lookup_cache_key(search_value, transport_mode)
    cache_entry = load_traffic_stop_cache().get(cache_key)
    if not isinstance(cache_entry, dict):
        return None

    cached_at = cache_entry.get("cached_at")
    stop_group = cache_entry.get("stop_group")
    if not cached_at or not isinstance(stop_group, dict):
        return None

    try:
        cached_at_dt = datetime.fromisoformat(cached_at)
    except ValueError:
        return None

    if datetime.now() - cached_at_dt > timedelta(hours=cache_ttl_hours):
        return None

    return stop_group


def _cache_stop_group(search_value: str, transport_mode: str | None, stop_group: dict) -> None:
    cache_entries = load_traffic_stop_cache()
    cache_entries[_get_stop_lookup_cache_key(search_value, transport_mode)] = {
        "cached_at": datetime.now().isoformat(),
        "stop_group": stop_group,
    }
    save_traffic_stop_cache(cache_entries)


def lookup_stop_groups(api_key: str, search_value: str) -> list[dict]:
    try:
        response = requests.get(
            f"{TRAFIKLAB_BASE_URL}/stops/name/{quote(search_value)}",
            params={"key": api_key},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        _raise_clean_api_error(
            exc, config_hint="`trafiklab_static_api_key` (or `trafiklab_api_key`)"
        )

    payload = response.json()
    return payload.get("stop_groups", [])


def resolve_stop_group(
    api_key: str | None,
    search_value: str,
    transport_mode: str | None = None,
    cache_ttl_hours: int = DEFAULT_STOP_LOOKUP_CACHE_HOURS,
) -> dict:
    cached_stop_group = _get_cached_stop_group(search_value, transport_mode, cache_ttl_hours)
    if cached_stop_group is not None:
        return cached_stop_group

    if not api_key:
        raise TrafficApiError(
            "Traffic data is unavailable. Add `trafiklab_static_api_key` or configure the exact `*_area_id` values."
        )

    stop_groups = lookup_stop_groups(api_key, search_value)
    if transport_mode:
        stop_groups = [
            stop_group
            for stop_group in stop_groups
            if transport_mode in stop_group.get("transport_modes", [])
        ]

    if not stop_groups:
        raise TrafficApiError(f"No stop group found for '{search_value}'.")

    normalized_search = _normalize_stop_name(search_value)

    def score(stop_group: dict) -> tuple[int, float]:
        normalized_name = _normalize_stop_name(stop_group.get("name", ""))
        exact_match = int(normalized_name == normalized_search)
        contains_match = int(normalized_search in normalized_name)
        return (
            exact_match * 2 + contains_match,
            stop_group.get("average_daily_stop_times", 0),
        )

    matched_stop_group = max(stop_groups, key=score)
    _cache_stop_group(search_value, transport_mode, matched_stop_group)
    return matched_stop_group


def _fetch_timetable(api_key: str, area_id: str, direction: str) -> dict:
    response = requests.get(
        f"{TRAFIKLAB_BASE_URL}/{direction}/{area_id}",
        params={"key": api_key},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _minutes_until(target_time: str) -> int | None:
    if not target_time:
        return None

    try:
        departure_time = datetime.fromisoformat(target_time)
    except ValueError:
        return None

    return round((departure_time - datetime.now()).total_seconds() / 60)


def _format_board_entry(entry: dict, direction: str) -> dict:
    route = entry.get("route", {})
    realtime_time = entry.get("realtime") or entry.get("scheduled", "")
    scheduled_time = entry.get("scheduled", "")
    realtime_platform = entry.get("realtime_platform", {})
    scheduled_platform = entry.get("scheduled_platform", {})
    origin = route.get("origin", {})
    destination = route.get("destination", {})
    minutes_until = _minutes_until(realtime_time)

    if direction == "departures":
        headsign = destination.get("name") or route.get("direction") or "-"
    else:
        headsign = origin.get("name") or route.get("direction") or "-"

    return {
        "time": realtime_time[11:16] if realtime_time else "--:--",
        "scheduled_time": scheduled_time[11:16] if scheduled_time else "--:--",
        "minutes_until": minutes_until,
        "line": route.get("designation") or route.get("name") or "-",
        "headsign": headsign,
        "mode": route.get("transport_mode") or "-",
        "platform": realtime_platform.get("designation")
        or scheduled_platform.get("designation")
        or "-",
        "operator": entry.get("agency", {}).get("name") or "-",
        "delay_minutes": round(entry.get("delay", 0) / 60),
        "is_realtime": entry.get("is_realtime", False),
        "canceled": entry.get("canceled", False),
    }


def _build_board(
    payload: dict, direction: str, transport_mode: str | None, limit: int
) -> list[dict]:
    entries = payload.get(direction, [])
    if transport_mode:
        entries = [
            entry
            for entry in entries
            if entry.get("route", {}).get("transport_mode") == transport_mode
        ]

    formatted_entries = [_format_board_entry(entry, direction) for entry in entries]
    return formatted_entries[:limit]


def get_station_timetables(
    api_key: str,
    label: str,
    area_id: str,
    transport_mode: str | None = None,
    limit: int = 6,
) -> dict:
    try:
        departures_payload = _fetch_timetable(api_key, area_id, "departures")
        arrivals_payload = _fetch_timetable(api_key, area_id, "arrivals")
    except requests.RequestException as exc:
        _raise_clean_api_error(
            exc, config_hint="`trafiklab_realtime_api_key` (or `trafiklab_api_key`)"
        )

    return {
        "label": label,
        "area_id": area_id,
        "transport_mode": transport_mode,
        "updated_at": departures_payload.get("timestamp") or arrivals_payload.get("timestamp"),
        "departures": _build_board(
            departures_payload, "departures", transport_mode=transport_mode, limit=limit
        ),
        "arrivals": _build_board(
            arrivals_payload, "arrivals", transport_mode=transport_mode, limit=limit
        ),
    }
