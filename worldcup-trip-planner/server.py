import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from agent_runner import run_worldcup_agent

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)


@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def call_agent(user_message: str) -> str:
    return run_worldcup_agent(user_message)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    try:
        reply = call_agent(message)
        return jsonify({"reply": reply})
    except Exception as error:
        return jsonify({"error": str(error)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
