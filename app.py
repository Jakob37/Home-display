#!/usr/bin/env python3

from flask import Flask, redirect, render_template, jsonify, request, url_for
from src.constants import COLORS, DAYS, ICONS
from src.db.db import (
    load_food_weeks,
    load_foods,
    load_selections,
    save_food_weeks,
    save_foods,
    save_selections,
)
from src.weather_request import get_temperature
from src.pollen import get_pollen
import datetime

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
        "weather_icons": weather_icons,
        "food_display": food_selections,
    }

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


def get_foods() -> dict[str, list[str]]:
    return load_foods()


@app.route("/planning/remove_food_type/<food_type>", methods=["POST"])
def remove_food_type(food_type: str):
    available_foods = get_foods()
    del available_foods[food_type]
    save_foods(available_foods)
    return redirect(url_for("planning"))


@app.route("/planning/remove_dish/<food_type>/<dish_name>", methods=["POST"])
def remove_dish(food_type: str, dish_name: str):
    available_foods = get_foods()
    available_foods[food_type].remove(dish_name)
    save_foods(available_foods)
    return redirect(url_for("planning"))


@app.route("/planning/add_food/<food_type>", methods=["POST"])
def add_food(food_type: str):
    dish_name = request.form["dish"]
    available_foods = get_foods()
    available_foods[food_type].append(dish_name)
    save_foods(available_foods)
    return redirect(url_for("planning"))


@app.route("/planning/add_category", methods=["POST"])
def add_category():
    print(request.form["textinput"])
    available_foods = get_foods()
    available_foods[request.form["textinput"]] = []
    save_foods(available_foods)
    return redirect(url_for("planning"))


@app.route("/planning", methods=["GET", "POST"])
def planning():

    # FIXME: Pass the food selection db entry
    # How to share these with the /eating route?

    available_foods = get_foods()
    return render_template("planning.html", foods=available_foods)


@app.route("/eating/save_week", methods=["POST"])
def save_week():
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
    app.run(debug=DEBUG_MODE)
