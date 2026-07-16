import os
import json
import threading
import time
from flask import Flask, jsonify, render_template, request, send_from_directory
from scraper import run_scraper, DATA_FILE

app = Flask(__name__, static_folder='static', template_folder='templates')

# Global state
scrape_status = {
    "is_running": False,
    "last_run": "Never",
    "status_message": "Idle",
    "stage": "idle",
    "listings_found": 0
}
status_lock = threading.Lock()

def bg_scrape_task():
    global scrape_status
    with status_lock:
        scrape_status["is_running"] = True
        scrape_status["stage"] = "starting"
        scrape_status["status_message"] = "Initializing Playwright browser..."
    
    def progress_update(stage_name, message):
        with status_lock:
            scrape_status["stage"] = stage_name
            scrape_status["status_message"] = message
            
    try:
        listings = run_scraper(progress_callback=progress_update)
        with status_lock:
            scrape_status["listings_found"] = len(listings)
            scrape_status["stage"] = "completed"
            scrape_status["status_message"] = "Scan completed successfully."
            scrape_status["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        with status_lock:
            scrape_status["stage"] = "failed"
            scrape_status["status_message"] = f"Error during scan: {str(e)}"
    finally:
        with status_lock:
            scrape_status["is_running"] = False

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/flats", methods=["GET"])
def get_flats():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": f"Failed to read data file: {str(e)}"}), 500
    return jsonify([])

@app.route("/api/scrape", methods=["POST"])
def trigger_scrape():
    global scrape_status
    with status_lock:
        if scrape_status["is_running"]:
            return jsonify({"status": "already_running", "message": "Scraper is already running."}), 400
            
    # Start background thread
    t = threading.Thread(target=bg_scrape_task)
    t.daemon = True
    t.start()
    
    return jsonify({"status": "started", "message": "Scraper started in background."})

@app.route("/api/status", methods=["GET"])
def get_status():
    global scrape_status
    with status_lock:
        return jsonify(scrape_status)

# Serve log file if needed for debugging
@app.route("/api/logs", methods=["GET"])
def get_logs():
    if os.path.exists("scraper.log"):
        try:
            with open("scraper.log", "r", encoding="utf-8") as f:
                # Get last 100 lines of logs
                lines = f.readlines()
                return jsonify({"logs": "".join(lines[-100:])})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"logs": "No log file found yet."})

# API endpoints to fetch/save configurations
@app.route("/api/config", methods=["GET", "POST"])
def manage_config():
    config_file = "config.json"
    if request.method == "POST":
        data = request.get_json() or {}
        max_budget = data.get("max_budget")
        if max_budget is not None:
            try:
                max_budget = int(max_budget)
                config_data = {}
                if os.path.exists(config_file):
                    with open(config_file, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                config_data["max_budget"] = max_budget
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, indent=4)
                return jsonify({"success": True, "max_budget": max_budget})
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        return jsonify({"error": "Missing max_budget parameter"}), 400
    else:
        config_data = {"max_budget": 50000}
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            except Exception:
                pass
        return jsonify(config_data)

if __name__ == "__main__":
    # Ensure templates and static directories exist
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    print("Starting Karachi Flat Finder Server on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
