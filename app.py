#!/usr/bin/env python3

from flask import Flask, render_template, jsonify
from src.weather_request import get_temperature
from src.traffic import get_train_table_zip
app = Flask(__name__)
import datetime
import configparser

config = configparser.ConfigParser()
config.read('app.config')

cache = dict()
cache['clock_seconds'] = False

@app.route("/")
def index():
    title = "Home display"

    #get_train_table_zip()

    my_clock = str(datetime.datetime.now().strftime("%H:%M"))
    my_date = str(datetime.datetime.now().strftime("%Y-%m-%d"))
    lund_lat = config['weather']['lat']
    lund_long = config['weather']['long']
    lund_temperature = round(get_temperature(lund_lat, lund_long))
    return render_template("app.html", **locals())

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


if __name__ == "__main__":
    app.run()

