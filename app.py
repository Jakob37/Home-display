#!/usr/bin/env python3

from flask import Flask, render_template, jsonify
from src.weather_request import get_temperature
from src.traffic import get_train_table_zip
from src.pollen import get_pollen
app = Flask(__name__)
import datetime
import configparser

config = configparser.ConfigParser()
config.read('app.config')

cache = dict()
cache['clock_seconds'] = False

USE_LOCAL = True

@app.route("/")
def index():
    title = "Home display"

    #get_train_table_zip()

    my_clock = str(datetime.datetime.now().strftime("%H:%M"))
    my_date = str(datetime.datetime.now().strftime("%Y-%m-%d"))
    lund_lat = config['weather']['lat']
    lund_long = config['weather']['long']

    if USE_LOCAL:
        lund_temperature = -37
    else:
        lund_temperature = round(get_temperature(lund_lat, lund_long))

    if USE_LOCAL:
        pollen = {"placeholder": "test"}
    else:
        pollen = get_pollen(config['pollen']['city'])
    print(f"pollen {pollen}")

    data = {
        "use_local": USE_LOCAL,
        "title": title,
        "my_clock": my_clock,
        "my_date": my_date,
        "lund_temperature": lund_temperature,
        "pollen": pollen
    }

    # data = {
    #     use_local = USE_LOCAL,
    #     title,
    #     my_clock,
    #     my_date,
    #     lund_temperature,
    #     pollen
    # }

    return render_template("app.html", **data)

@app.route("/clock")
def get_clock():
    if cache['clock_seconds']:
        clock = str(datetime.datetime.now().strftime("%H:%M:%S"))
    else:
        clock = str(datetime.datetime.now().strftime("%H:%M"))
    return str(clock)

@app.route("/toggleclock", methods=['POST'])
def toggle_clock():
    cache['clock_seconds'] = not cache['clock_seconds']
    print(f"clock_seconds: {cache['clock_seconds']}")
    resp = jsonify(success=True)
    print(resp)
    #return resp

@app.route("/user/")
def hello_user():
    users = ["Xuan", "Jakob", "Alvar"]


@app.route("/second")
def second_page():
    return render_template("second_page.html")


if __name__ == "__main__":
    app.run()

