"""Self-hosted fuel price API exposing the collector's Mumbai petrol price scraper."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify

from collector.atf import fetch_mumbai_petrol_price, ATF_ANCHOR

app = Flask(__name__)


@app.route("/fuelprice/v1.0/petrol/<city_name>")
def petrol_price(city_name):
    if city_name.lower() != ATF_ANCHOR.lower():
        return jsonify({"error": "Not found"}), 404
    price, _ = fetch_mumbai_petrol_price()
    if not price:
        return jsonify({"error": "Unavailable"}), 502
    return jsonify({ATF_ANCHOR: price})


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)