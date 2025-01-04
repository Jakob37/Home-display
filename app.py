#!/usr/bin/env python3

from flask import Flask, render_template, jsonify
from src.weather_request import get_temperature
from src.traffic import get_train_table_zip
from src.pollen import get_pollen

app = Flask(__name__)
import datetime
import configparser

config = configparser.ConfigParser()
config.read("app.config")

cache = dict()
cache["clock_seconds"] = False

USE_LOCAL = True
DEBUG_MODE = True
DEBUG_TEMP = 3


class WeatherIcon:
    def __init__(self, icon: str, color: str):
        self.icon = icon
        self.color = color


def get_weather_icons(temperature: int) -> str:

    blue = "steelblue"

    deepblue = "blue"
    lightblue = "lightblue"
    yellow = "yellow"
    orange = "orange"
    red = "red"

    weather_icons = []
    if temperature <= 0:
        weather_icons.append(WeatherIcon("fa-snowflake", blue))
    if temperature <= 7:
        weather_icons.append(WeatherIcon("fa-mitten", blue))
        weather_icons.append(WeatherIcon("fa-mitten", blue))
    if temperature <= 12:
        weather_icons.append(WeatherIcon("fa-hat-wizard", blue))

    if temperature <= 0:
        weather_icons.append(WeatherIcon("fa-temperature-empty", deepblue))
    elif temperature <= 7:
        weather_icons.append(WeatherIcon("fa-temperature-low", lightblue))
    elif temperature <= 12:
        weather_icons.append(WeatherIcon("fa-temperature-half", yellow))
    elif temperature <= 20:
        weather_icons.append(WeatherIcon("fa-temperature-full", orange))
    else:
        weather_icons.append(WeatherIcon("fa-temperature-high", red))

    return weather_icons


@app.route("/")
def index():
    title = "Home display"

    # get_train_table_zip()

    my_clock = str(datetime.datetime.now().strftime("%H:%M"))
    my_date = str(datetime.datetime.now().strftime("%Y-%m-%d"))
    lund_lat = config["weather"]["lat"]
    lund_long = config["weather"]["long"]

    if USE_LOCAL:
        lund_temperature = DEBUG_TEMP
    else:
        lund_temperature = round(get_temperature(lund_lat, lund_long))

    if USE_LOCAL:
        pollen = {}
        # pollen = {"Pollen 1": "A lot", "Pollen 2": "Not so much"}
    else:
        pollen = get_pollen(config["pollen"]["city"])
    print(f"pollen {pollen}")

    weather_icons = get_weather_icons(lund_temperature)

    data = {
        "use_local": USE_LOCAL,
        "title": title,
        "my_clock": my_clock,
        "my_date": my_date,
        "lund_temperature": lund_temperature,
        "pollen": pollen,
        "weather_icons": weather_icons,
        "display_text": ["ALVAR", "PAPPA", "MAMMA"],
    }

    # data = {
    #     use_local = USE_LOCAL,
    #     title,
    #     my_clock,
    #     my_date,
    #     lund_temperature,
    #     pollen
    # }

    return render_template("weather.html", **data)


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


@app.route("/eating")
def eating_page():

    weeks = {
        "12": {
            "Monday": "Pizza",
            "Tuesday": "Salad",
            "Wednesday": "Pasta",
            "Thursday": "Fish",
            "Friday": "Steak",
        },
        "13": {
            "Monday": "Pizza",
            "Tuesday": "Salad",
            "Wednesday": "Pasta",
            "Thursday": "Fish",
            "Friday": "Steak",
        },
        "14": {
            "Monday": "Pizza",
            "Tuesday": "Salad",
            "Wednesday": "Pasta",
            "Thursday": "Fish",
            "Friday": "Steak",
        },
    }
    available_foods = [
        "Pizza",
        "Salad",
        "Pasta",
        "Fish",
        "Steak",
        "Soup",
        "Sushi",
        "Curry",
        "Burger",
        "Tacos",
        "Ramen",
        "Chicken",
        "BBQ",
        "Paella",
    ]
    # food_types = ["&#xf00c; Fisk!", "Ägg", "Kött", "Kyckling", "Tofu"]

    available_foods_grouped = {
        "Fisk": ["Fiskpinnar", "Flundra"],
        "Ägg": ["Omelett", "Pannkakor"],
        "Kött": ["Köttbullar", "Prinskorv"],
        "Kyckling": ["Kyckling i ugn"],
        "Tofu": ["Stekt med paprika"],
    }

    selected_food_type_per_day = {
        "Mo": "Fisk",
        "Tu": "Ägg",
        "We": "Kött",
        "Th": "Kyckling",
        "Fr": "Tofu",
    }

    selected_food_per_day = {
        "Mo": "Fiskpinnar",
        "Tu": "Fiskpinnar",
        "We": "Fiskpinnar",
        "Th": "Fiskpinnar",
        "Fr": "Flundra",
    }

    # data = {
    #     "weeks": weeks,
    #     "available_foods": available_foods
    # }
    return render_template(
        "eating_plan.html",
        weeks=weeks,
        available_foods=available_foods,
        available_foods_grouped=available_foods_grouped,
        selected_food_type_per_day=selected_food_type_per_day,
        # selected_food_per_day=selected_food_per_day,
    )


if __name__ == "__main__":
    app.run(debug=DEBUG_MODE)
