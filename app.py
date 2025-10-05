from flask import Flask, render_template, request, send_file, url_for, redirect, session
import os
from scraper import fetch_messages
from auth import auth_bp
from client_manager import run_async

app = Flask(__name__)
app.secret_key = "supersecret"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# register blueprint
app.register_blueprint(auth_bp, url_prefix="/auth")

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
        url = request.form.get("channel_url")
        file_name = run_async(fetch_messages(url, phone))
        file_exists = True

    return render_template("index.html", file_exists=file_exists, file_name=file_name)

# Download
@app.route("/download/<file_name>")
def download(file_name):
    full_path = os.path.join(BASE_DIR, file_name)
    if os.path.exists(full_path):
        return send_file(full_path, as_attachment=True)
    else:
        return "File not found!", 404

if __name__ == "__main__":
    app.run(debug=False)
