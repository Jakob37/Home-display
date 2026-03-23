from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from src.db.db import load_pollen_cache, save_pollen_cache

POLLEN_LEVEL_KEYWORDS = (
    (5, ("mycket hoga", "mycket höga", "very high", "extrem")),
    (4, ("hoga", "höga", "high")),
    (3, ("mattliga", "måttliga", "moderate", "medel")),
    (1, ("mycket laga", "mycket låga", "very low")),
    (2, ("laga", "låga", "low")),
    (0, ("ingen", "none")),
)
REQUEST_TIMEOUT_SECONDS = 10
POLLEN_CACHE_TTL = timedelta(hours=24)


def parse_pollen_level(amount: str) -> int:
    normalized_amount = amount.strip().lower()

    if not normalized_amount:
        return 0

    for level, keywords in POLLEN_LEVEL_KEYWORDS:
        if any(keyword in normalized_amount for keyword in keywords):
            return level

    digits = "".join(char for char in normalized_amount if char.isdigit())
    if digits:
        return max(0, min(int(digits), 5))

    return 0


def _get_cache_key(city: str) -> str:
    return city.strip().lower()


def _read_cached_snapshot(city: str, max_age: timedelta | None = POLLEN_CACHE_TTL) -> dict | None:
    cache_entry = load_pollen_cache().get(_get_cache_key(city))
    if not isinstance(cache_entry, dict):
        return None

    cached_at = cache_entry.get("cached_at")
    pollen = cache_entry.get("pollen")
    if not isinstance(cached_at, str) or not isinstance(pollen, dict):
        return None

    try:
        cached_at_dt = datetime.fromisoformat(cached_at)
    except ValueError:
        return None

    if max_age is not None and datetime.now() - cached_at_dt > max_age:
        return None

    return {
        "pollen": pollen,
        "retrieved_at": cached_at_dt,
    }


def _store_cached_snapshot(city: str, pollen: dict[str, dict[str, str | int]], retrieved_at: datetime) -> None:
    cache_entries = load_pollen_cache()
    cache_entries[_get_cache_key(city)] = {
        "cached_at": retrieved_at.isoformat(timespec="seconds"),
        "pollen": pollen,
    }
    save_pollen_cache(cache_entries)


def _fetch_pollen(city: str) -> dict[str, dict[str, str | int]]:
    url = f"https://pollenkoll.se/pollenprognos/{city}"
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    pollen_items = soup.find_all(class_="pollen-city__item")
    pollen_dict: dict[str, dict[str, str | int]] = {}

    for pollen_item in pollen_items:
        plant_node = pollen_item.find("div", class_="pollen-city__item-name")
        level_node = pollen_item.find("div", class_="pollen-city__item-desc")
        if plant_node is None or level_node is None:
            continue

        plant = plant_node.get_text(strip=True)
        pollen_amount = level_node.get_text(strip=True)
        pollen_dict[plant] = {
            "raw_level": pollen_amount,
            "level": parse_pollen_level(pollen_amount),
        }

    if not pollen_dict:
        raise ValueError("No pollen data found in source response.")

    return pollen_dict


def get_pollen_snapshot(city: str) -> dict[str, object]:
    cached_snapshot = _read_cached_snapshot(city)
    if cached_snapshot is not None:
        return cached_snapshot

    try:
        pollen = _fetch_pollen(city)
        retrieved_at = datetime.now()
        _store_cached_snapshot(city, pollen, retrieved_at)
        return {
            "pollen": pollen,
            "retrieved_at": retrieved_at,
        }
    except (requests.RequestException, ValueError):
        stale_snapshot = _read_cached_snapshot(city, max_age=None)
        if stale_snapshot is not None:
            return stale_snapshot
        return {"pollen": {}, "retrieved_at": None}


def get_pollen(city: str) -> dict[str, dict[str, str | int]]:
    return get_pollen_snapshot(city)["pollen"]
