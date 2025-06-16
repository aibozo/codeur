"""API server module."""
import flask

app = flask.Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok"}
