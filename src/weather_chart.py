from datetime import date
from math import ceil


SWEDISH_WEEKDAYS = ("mån", "tis", "ons", "tors", "fre", "lör", "sön")
SWEDISH_MONTHS = (
    "jan", "feb", "mars", "apr", "maj", "juni", "juli", "aug", "sep", "okt", "nov", "dec",
)


def build_temperature_chart(forecast: list[dict]) -> dict | None:
    if not forecast:
        return None

    lowest = min(0, min(entry["min_temp"] for entry in forecast))
    highest = max(0, max(entry["max_temp"] for entry in forecast))
    target_step = max(1, ceil((highest - lowest) / 5))
    step = next((interval for interval in (1, 2, 5, 10, 20, 50) if interval >= target_step), target_step)
    lower = lowest // step * step
    upper = max(lower + step, ceil(highest / step) * step)
    percent_per_degree = 100 / (upper - lower)

    def position(temperature: int) -> str:
        return f"{(temperature - lower) * percent_per_degree:.3f}%"

    ticks = [
        {"value": tick, "position": position(tick)}
        for tick in range(lower, upper + 1, step)
    ]
    days = []
    for entry in forecast:
        day = date.fromisoformat(entry["date"])
        bars = [
            {
                "series": series,
                "value": temperature,
                "bottom": position(min(0, temperature)),
                "height": f"{abs(temperature) * percent_per_degree:.3f}%",
            }
            for series, temperature in (("min", entry["min_temp"]), ("max", entry["max_temp"]))
        ]
        days.append(
            {
                "date": entry["date"],
                "weekday": SWEDISH_WEEKDAYS[day.weekday()],
                "date_label": f"{day.day} {SWEDISH_MONTHS[day.month - 1]}",
                "icon": entry.get("icon"),
                "symbol": entry.get("symbol"),
                "precipitation_chance": entry.get("precipitation_chance"),
                "is_outlook": entry.get("is_outlook", False),
                "bars": bars,
            }
        )
    return {
        "days": days,
        "ticks": ticks,
        "has_outlook": any(day["is_outlook"] for day in days),
    }
