#!/usr/bin/env python3

from flask import Flask, render_template
from src.weather_request import get_temperature
app = Flask(__name__)
import datetime

@app.route("/")
def index():
    title = "Home display"
    my_clock = str(datetime.datetime.now().strftime("%H:%M"))
    my_date = str(datetime.datetime.now().strftime("%Y-%m-%d"))
    lund_lat = 55.7047
    lund_long = 13.1910
    lund_temperature = round(get_temperature(lund_lat, lund_long))
    return render_template("app.html", **locals())

@app.route("/user/")
def hello_user():
    users = ["Xuan", "Jakob", "Alvar"]


if __name__ == "__main__":
    app.run()

