import os
import requests

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    session
)

app = Flask(__name__)

# ============================================================
# Flask Session Configuration
# ============================================================

app.secret_key = "fleetops-dev-secret-key"

# ============================================================
# Login Credentials
# ============================================================

USERNAME = "admin"
PASSWORD = "admin123"

# ============================================================
# Backend Query Service URL
# ============================================================

QUERY_SERVICE_URL = os.getenv(
    "QUERY_SERVICE_URL",
    "http://telemetry-query-service/api/v1/fleet/telemetry"
)


# ============================================================
# Login
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET" and "username" in session:
        return redirect(url_for("index"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == USERNAME and password == PASSWORD:

            session["username"] = username

            return redirect(url_for("index"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


# ============================================================
# Logout
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ============================================================
# Main Dashboard
# ============================================================

@app.route("/")
def index():

    if "username" not in session:
        return redirect(url_for("login"))

    return render_template("index.html")


# ============================================================
# Telemetry API
# ============================================================

@app.route("/api/telemetry-feed")
def telemetry_feed():

    if "username" not in session:
        return jsonify({
            "status": "unauthorized",
            "message": "Please login first"
        }), 401

    try:

        response = requests.get(
            QUERY_SERVICE_URL,
            timeout=5
        )

        response.raise_for_status()

        return jsonify(response.json())

    except requests.exceptions.RequestException as e:

        print(f"Error fetching telemetry: {e}")

        return jsonify({
            "status": "error",
            "message": "Unable to fetch telemetry data",
            "data": []
        }), 500

    except Exception as e:

        print(f"Unexpected error: {e}")

        return jsonify({
            "status": "error",
            "message": "Unexpected backend error",
            "data": []
        }), 500


# ============================================================
# Devices API
#
# Browser
#     ↓
# /api/devices
#     ↓
# Flask Frontend
#     ↓
# telemetry-query-service
#     ↓
# PostgreSQL
#
# Converts nested telemetry response into flat structure
# expected by the dashboard.
# ============================================================

@app.route("/api/devices")
def api_devices():

    if "username" not in session:
        return jsonify({
            "status": "unauthorized",
            "message": "Please login first"
        }), 401

    try:

        response = requests.get(
            QUERY_SERVICE_URL,
            timeout=5
        )

        response.raise_for_status()

        result = response.json()

        normalized_devices = []

        data = result.get("data", [])

        if not isinstance(data, list):
            data = []

        for item in data:

            if not isinstance(item, dict):
                continue

            payload = item.get("payload", {}) or {}

            if not isinstance(payload, dict):
                payload = {}

            metrics = payload.get("metrics", {}) or {}

            if not isinstance(metrics, dict):
                metrics = {}

            location = metrics.get("location", {}) or {}

            if not isinstance(location, dict):
                location = {}

            normalized_devices.append({
                "id": item.get("id"),

                "device_id": payload.get(
                    "device_id",
                    "Unknown"
                ),

                "speed_kmh": metrics.get(
                    "speed_kmh",
                    0
                ),

                "fuel_level_pct": metrics.get(
                    "fuel_level_pct",
                    0
                ),

                "engine_temp_c": metrics.get(
                    "engine_temp_c",
                    0
                ),

                "latitude": location.get(
                    "latitude"
                ),

                "longitude": location.get(
                    "longitude"
                ),

                "timestamp": payload.get(
                    "timestamp"
                ),

                "created_at": item.get(
                    "created_at"
                )
            })

        return jsonify({
            "status": "success",
            "count": len(normalized_devices),
            "devices": normalized_devices
        })

    except requests.exceptions.RequestException as e:

        print(f"Error fetching devices: {e}")

        return jsonify({
            "status": "error",
            "message": "Unable to fetch device data",
            "devices": []
        }), 500

    except Exception as e:

        print(f"Unexpected devices API error: {e}")

        return jsonify({
            "status": "error",
            "message": "Unexpected backend error",
            "devices": []
        }), 500


# ============================================================
# Health Check
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "healthy",
        "service": "frontend-ui"
    })


# ============================================================
# Application Start
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )