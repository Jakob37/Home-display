#!/usr/bin/env python3

import requests
from datetime import datetime

def get_temperature(latitude: float, longitude: float) -> float:

    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={latitude}&lon={longitude}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    current_time = datetime.now().isoformat(timespec='hours')
    for data in data['properties']['timeseries']:
        time = data['time']
        if time.startswith(current_time):
            return data['data']['instant']['details']['air_temperature']
    raise ValueError(f"Current time not found: {current_time}")

