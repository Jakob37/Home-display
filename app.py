#!/usr/bin/env python3

from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
def hello():
    title = "Test title"
    users = ["Xuan", "Jakob", "Alvar"]
    return render_template("app.html", **locals())

@app.route("/user/")
def hello_user():
    users = ["Xuan", "Jakob", "Alvar"]


if __name__ == "__main__":
    app.run()

