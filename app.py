# app.py

import os
from flask import Flask, request, jsonify
from zafira_core import ZafiraCore

app = Flask(__name__)
zafira = ZafiraCore()

def _get_first(d: dict, *keys):
    """
    Retorna d[keys[0]][0] ou d[keys[1]][0] ou ... sem lançar KeyError.
    """
    for k in keys:
        arr = d.get(k)
        if isinstance(arr, list) and arr:
            return arr[0]
    return None

@app.route("/webhook", methods=["GET"])
def verify():
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == os.getenv("VERIFY_TOKEN"):
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}

    # 1) Pega o elemento de entrada (pt: entrada / en: entry)
    entry = _get_first(data, "entrada", "entry")
    if not entry:
        return jsonify(error="no entry"), 200

    # 2) Pega a mudança (pt: mudanças / en: changes)
    change = _get_first(entry, "mudanças", "changes")
    if not change:
        return jsonify(error="no change"), 200

    # 3) Pega o payload real (pt: valor / en: value)
    value = change.get("valor") or change.get("value") or {}
    contacts = value.get("contatos") or value.get("contacts") or []
    if not contacts:
        return jsonify(error="no contacts"), 200

    sender_id = contacts[0].get("wa_id") or contacts[0].get("waId")
    if not sender_id:
        return jsonify(error="no sender"), 200

    # 4) Se for resposta de lista interativa (pt: interactive / en: interactive)
    interactive = value.get("interactive") or {}
    if interactive.get("type") == "list_reply":
        choice_id = (
            interactive.get("list_reply", {})
                       .get("id")
            or interactive.get("list_reply", {})
                       .get("title")
        )
        zafira.process_message(sender_id, choice_id, interactive=interactive)
        return jsonify(status="ok"), 200

    # 5) Se for mensagem de texto (pt: mensagens / en: messages)
    messages = value.get("mensagens") or value.get("messages") or []
    if messages:
        text_obj = messages[0].get("texto") or messages[0].get("text") or {}
        text = text_obj.get("body") or text_obj.get("preview_url") or ""
        if text:
            zafira.process_message(sender_id, text)
            return jsonify(status="ok"), 200

    # Ignora outros tipos de payload (status, erro, etc.)
    return jsonify(status="ignored"), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
