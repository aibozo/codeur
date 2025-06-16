
"""Main application module."""
from flask import Flask
from database import Database

app = Flask(__name__)
db = Database()

@app.route("/")
def index():
    return {"message": "Hello World"}
