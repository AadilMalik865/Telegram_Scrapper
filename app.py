from flask import Flask, render_template, request, send_file, url_for
import asyncio, os
from scraper import fetch_messages
import nest_asyncio

nest_asyncio.apply()  # ✅ patch event loop

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/", methods=["GET", "POST"])
def index():
    file_name = None
    file_exists = False

    if request.method == "POST":
        url = request.form.get("channel_url")
        loop = asyncio.get_event_loop()
        file_name = loop.run_until_complete(fetch_messages(url))  # ✅ filename only
        file_exists = True

    return render_template("index.html", file_exists=file_exists, file_name=file_name)

@app.route("/download/<file_name>")
def download(file_name):
    full_path = os.path.join(BASE_DIR, file_name)
    if os.path.exists(full_path):
        return send_file(full_path, as_attachment=True)
    else:
        return "File not found!", 404

if __name__ == "__main__":
    app.run(debug=True)
