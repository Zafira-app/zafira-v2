# app.py - A CAMADA DE SERVIÇO WEB

import os
import json
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Importa o coração da nossa aplicação
from zafira_core import ZafiraCore

# Carrega variáveis de ambiente e configura o log
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Inicializa o Flask e a Zafira
app = Flask(__name__)
zafira = ZafiraCore()

# ==============================================================================
# ROTAS
# ==============================================================================
@app.route("/health", methods=["GET"])
def health():
    """Verifica a saúde do serviço."""
    return "OK", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """Webhook principal para receber mensagens do WhatsApp."""
    if request.method == "GET":
        # Processo de verificação do WhatsApp
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN"):
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    # Processamento de mensagens recebidas via POST
    try:
        payload = request.get_json()
        logger.info("Webhook recebido: %s", json.dumps(payload, indent=2))
        
        change = payload["entry"][0]["changes"][0]
        if change["field"] == "messages":
            message_data = change["value"]["messages"][0]
            sender_id = message_data["from"]
            user_message = message_data["text"]["body"]
            
            # Delega o processamento para o ZafiraCore
            zafira.process_message(sender_id, user_message)

    except (KeyError, IndexError, TypeError) as e:
        logger.info("Ignorado: webhook sem texto de mensagem de usuário ou formato inesperado. Erro: %s", e)
    except Exception as e:
        logger.error("Erro inesperado no webhook: %s", e, exc_info=True)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
