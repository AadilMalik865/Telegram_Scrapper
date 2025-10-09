from flask import Flask, render_template, request, send_file, url_for, redirect, session, Response
import os, queue
from scraper import fetch_messages
from auth import auth_bp
from client_manager import run_async

app = Flask(__name__)
app.secret_key = "supersecret"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# register blueprint
app.register_blueprint(auth_bp, url_prefix="/auth")

# Global message queue for logs
log_queue = queue.Queue()

def log_message(msg):
    log_queue.put(msg)

# Root → Login
@app.route("/")
def home():
    return redirect(url_for("auth.login"))

# Index Scraper
@app.route("/index", methods=["GET", "POST"])
def index():
    phone = session.get("phone")
    if not phone:
        return redirect(url_for("auth.login"))

    file_name, file_exists = None, False

    if request.method == "POST":
        # 🧹 Clear old logs before new scraping
        while not log_queue.empty():
            try:
                log_queue.get_nowait()
            except:
                break

        urls_text = request.form.get("channel_urls")
        urls = [u.strip() for u in urls_text.splitlines() if u.strip()]

        log_message("🚀 Scraping started...")
        file_name = run_async(fetch_messages(urls, phone, log_message))  # pass logger
        log_message("✅ Scraping finished.")
        file_exists = True

    return render_template("index.html", file_exists=file_exists, file_name=file_name)


# SSE endpoint for live logs
@app.route("/progress")
def progress():
    def generate():
        while True:
            msg = log_queue.get()  # wait until message available
            yield f"data: {msg}\n\n"
    return Response(generate(), mimetype="text/event-stream")

# Download
@app.route("/download/<file_name>")
def download(file_name):
    full_path = os.path.join(BASE_DIR, file_name)
    if os.path.exists(full_path):
        return send_file(full_path, as_attachment=True)
    else:
        return "File not found!", 404

if __name__ == "__main__":
    app.run(debug=False, threaded=True)
