#!/usr/bin/env python3

from datetime import datetime
from urllib.parse import quote

import requests


TRAFIKLAB_BASE_URL = "https://realtime-api.trafiklab.se/v1"


class TrafficApiError(Exception):
    pass


def _normalize_stop_name(value: str) -> str:
    return " ".join(value.lower().split())


def lookup_stop_groups(api_key: str, search_value: str) -> list[dict]:
    response = requests.get(
        f"{TRAFIKLAB_BASE_URL}/stops/name/{quote(search_value)}",
        params={"key": api_key},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("stop_groups", [])


def resolve_stop_group(api_key: str, search_value: str, transport_mode: str | None = None) -> dict:
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

    return max(stop_groups, key=score)


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
        raise TrafficApiError(str(exc)) from exc

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
