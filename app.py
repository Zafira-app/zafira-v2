# app.py

import os
from flask import Flask, request, jsonify
from zafira_core import ZafiraCore

app = Flask(__name__)
zafira = ZafiraCore()

def _get_first(arrays_dict: dict, *keys):
    """
    Retorna o primeiro item de data[key] para as chaves listadas,
    suportando português ('entrada','mudanças') e inglês ('entry','changes').
    """
    for k in keys:
        val = arrays_dict.get(k)
        if isinstance(val, list) and val:
            return val[0]
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

    # 1) captura "entrada" ou "entry"
    entry = _get_first(data, "entrada", "entry")
    if not entry:
        return jsonify(error="sem entrada"), 200

    # 2) captura "mudanças" ou "changes"
    change = _get_first(entry, "mudanças", "changes")
    if not change:
        return jsonify(error="sem mudança"), 200

    # 3) captura payload real "valor" ou "value"
    value = change.get("valor") or change.get("value") or {}
    contacts = value.get("contatos") or value.get("contacts") or []
    if not contacts:
        return jsonify(error="sem contatos"), 200

    sender_id = contacts[0].get("wa_id") or contacts[0].get("waId")
    if not sender_id:
        return jsonify(error="sem remetente"), 200

    # 4) resposta de lista interativa
    interactive = value.get("interactive") or {}
    if interactive.get("type") == "list_reply":
        choice_id = (interactive.get("list_reply") or {}).get("id") or ""
        zafira.process_message(sender_id, choice_id, interactive=interactive)
        return jsonify(status="ok"), 200

    # 5) mensagem de texto normal
    messages = value.get("mensagens") or value.get("messages") or []
    if messages:
        text_obj = messages[0].get("texto") or messages[0].get("text") or {}
        body = text_obj.get("body") or ""
        if body:
            zafira.process_message(sender_id, body)
            return jsonify(status="ok"), 200

    # ignora outros eventos
    return jsonify(status="ignored"), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
