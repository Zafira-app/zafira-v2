import os
import json
import logging

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from zafira_core import ZafiraCore

# Carrega .env e configura logger
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Instancia Flask e ZafiraCore
app = Flask(__name__)
zafira = ZafiraCore()

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Verificação do token do WhatsApp
        if (request.args.get("hub.mode") == "subscribe" and
            request.args.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN")):
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    # Recebe POST com mensagem de usuário
    try:
        payload = request.get_json()
        logger.info("Webhook recebido: %s", json.dumps(payload, indent=2))
        change = payload["entry"][0]["changes"][0]
        if change.get("field") == "messages":
            msg = change["value"]["messages"][0]
            sender_id    = msg["from"]
            user_message = msg["text"]["body"]
            zafira.process_message(sender_id, user_message)
    except Exception as e:
        logger.info("Ignorado: payload inesperado ou sem texto (%s)", e)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
