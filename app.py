from flask import Flask, request, jsonify
from zafira_core import ZafiraCore
import os

app = Flask(__name__)
zafira = ZafiraCore()

@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == os.getenv("VERIFY_TOKEN"):
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    entry = data["entrada"][0]["mudanças"][0]["valor"]
    sender_id = entry["contatos"][0]["wa_id"]

    # Mensagem interativa (List Reply)
    interactive = entry.get("interactive")
    if interactive and interactive.get("type") == "list_reply":
        zafira.process_message(sender_id, interactive["list_reply"]["id"], interactive=interactive)
        return jsonify(status="ok"), 200

    # Texto normal
    msgs = entry.get("mensagens")
    if msgs:
        text = msgs[0]["texto"]["body"]
        zafira.process_message(sender_id, text)
        return jsonify(status="ok"), 200

    return jsonify(status="ignored"), 200

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
