#!/usr/bin/env python3

from flask import Flask, render_template
app = Flask(__name__)
import datetime

@app.route("/")
def hello():
    title = "Test title"
    users = ["Xuan", "Jakob", "Alvar"]
    now = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    return render_template("app.html", **locals())

@app.route("/user/")
def hello_user():
    users = ["Xuan", "Jakob", "Alvar"]


if __name__ == "__main__":
    app.run()

