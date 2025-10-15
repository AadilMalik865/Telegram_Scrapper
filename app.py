from flask import Flask, render_template, request, send_file, url_for, redirect, session, Response, jsonify
import os, queue, threading, tempfile
from scraper import fetch_messages
from auth import auth_bp
from client_manager import run_async

app = Flask(__name__)
app.secret_key = "supersecret"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = tempfile.gettempdir()

# Register Blueprint
app.register_blueprint(auth_bp, url_prefix="/auth")

# Global message queue and control
log_queue = queue.Queue()
stop_event = threading.Event()  # Stop scraper
scraped_file = None             # Track completed CSV

def log_message(msg):
    log_queue.put(msg)

@app.route("/")
def home():
    return redirect(url_for("auth.login"))

@app.route("/index", methods=["GET", "POST"])
def index():
    global scraped_file
    phone = session.get("phone")
    if not phone:
        return redirect(url_for("auth.login"))

    file_exists = scraped_file and os.path.exists(scraped_file)

    if request.method == "POST":
        # Clear old logs
        while not log_queue.empty():
            log_queue.get_nowait()

        urls_text = request.form.get("channel_urls")
        urls = [u.strip() for u in urls_text.splitlines() if u.strip()]

        stop_event.clear()  # reset stop flag
        scraped_file = None # reset file tracker

        # Background scraping
        def background_scrape():
            global scraped_file
            log_message("🚀 Scraping started in background...")
            try:
                file_name = run_async(fetch_messages(urls, phone, log_message, stop_event))
                scraped_file = file_name  # always assign so partial CSV exists
                if not stop_event.is_set():
                    log_message("✅ Scraping completed successfully.")
                else:
                    log_message("🛑 Scraping stopped by user.")
            except Exception as e:
                log_message(f"❌ Error during scraping: {e}")

        threading.Thread(target=background_scrape, daemon=True).start()
        log_message("⏳ Please wait... scraping is running in background.")
        return render_template("index.html", file_exists=False)

    return render_template("index.html", file_exists=file_exists, file_name=scraped_file)

# SSE endpoint for live logs
@app.route("/progress")
def progress():
    def generate():
        while True:
            msg = log_queue.get()
            yield f"data: {msg}\n\n"
    return Response(generate(), mimetype="text/event-stream")

# Stop scraping
@app.route("/stop", methods=["POST"])
def stop_scraping():
    stop_event.set()
    log_message("🛑 Stop signal received — scraper will stop soon.")
    return jsonify({"status": "stopping"})

# Download CSV
@app.route("/download/<file_name>")
def download(file_name):
    full_path = os.path.join(BASE_DIR, file_name)
    if os.path.exists(full_path):
        return send_file(full_path, as_attachment=True)
    else:
        return "File not found!", 404

# Check if file exists (used by frontend)
@app.route("/check_file")
def check_file():
    global scraped_file
    if scraped_file and os.path.exists(scraped_file):
        return jsonify({"exists": True, "file_name": scraped_file})
    return jsonify({"exists": False})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
