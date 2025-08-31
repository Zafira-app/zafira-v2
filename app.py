import os
import json
import logging
import re
import time
import hashlib
import requests

from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ==============================================================================
# CONFIGURAÇÃO BÁSICA
# ==============================================================================
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==============================================================================
# CLIENTE WHATSAPP
# ==============================================================================
class WhatsAppClient:
    def __init__(self):
        self.api_url = "https://graph.facebook.com/v20.0/"
        self.token = os.getenv("WHATSAPP_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        if not self.token or not self.phone_number_id:
            logger.error("Credenciais do WhatsApp não configuradas!")
        else:
            logger.info("Cliente WhatsApp inicializado.")

    def send_text_message(self, recipient_id: str, message: str) -> bool:
        url = f"{self.api_url}{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message}
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info(f"Mensagem enviada para {recipient_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Falha ao enviar WhatsApp: {e}")
            return False

# ==============================================================================
# CLIENTE ALIEXPRESS (com logs de request/response)
# ==============================================================================
class AliExpressClient:
    def __init__(self):
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY", "")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET", "")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID", "")
        self.api_url = "https://api-sg.aliexpress.com/sync"
        if not (self.app_key and self.app_secret and self.tracking_id):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress inicializado.")

    def _generate_signature(self, params: dict) -> str:
        sorted_items = sorted(params.items())
        msg = "".join(f"{k}{v}" for k, v in sorted_items)
        # MD5 padrão: app_secret + concat + app_secret
        raw = f"{self.app_secret}{msg}{self.app_secret}".encode("utf-8")
        return hashlib.md5(raw).hexdigest().upper()

    def search_products(self, keywords: str, limit: int = 3) -> dict:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        params = {
            "app_key": self.app_key,
            "method": "aliexpress.affiliate.product.query",
            "sign_method": "md5",
            "timestamp": timestamp,
            "keywords": keywords,
            "tracking_id": self.tracking_id,
            "page_size": str(limit),
            "target_language": "pt",
            "target_currency": "BRL",
            "ship_to_country": "BR"
        }
        params["sign"] = self._generate_signature(params)

        # Log de diagnóstico
        logger.info("AliExpress QUERY URL: %s", requests.Request("GET", self.api_url, params=params).prepare().url)
        try:
            resp = requests.get(self.api_url, params=params, timeout=40)
            logger.info("AliExpress RESPONSE STATUS: %s", resp.status_code)
            logger.info("AliExpress RESPONSE BODY: %s", resp.text[:1000])
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error("Erro na API AliExpress: %s", e)
            return {"error": str(e)}

# ==============================================================================
# NÚCLEO DA ZAFIRA
# ==============================================================================
class ZafiraCore:
    def __init__(self):
        self.whatsapp = WhatsAppClient()
        self.aliexpress = AliExpressClient()
        logger.info("Zafira Core inicializada.")

    def process_message(self, sender_id: str, message: str):
        logger.info(f"Recebido de {sender_id}: {message}")
        intent = self._detect_intent(message)
        if intent == "produto":
            self._handle_product(sender_id, message)
        elif intent == "saudacao":
            self._handle_greeting(sender_id)
        else:
            self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()
        if any(k in m for k in ["quero", "procuro", "comprar", "fone", "celular", "smartwatch"]):
            return "produto"
        if any(k in m for k in ["oi", "olá", "ola", "e aí"]):
            return "saudacao"
        return "desconhecido"

    def _handle_greeting(self, sender_id: str):
        text = "Oi! 😊 Sou a Zafira, sua assistente de compras. O que você procura hoje?"
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_product(self, sender_id: str, message: str):
        clean = re.sub(r"[^\w\s]", "", message.lower())
        stop = {"um", "uma", "o", "a", "de", "do", "da", "para", "com", "reais"}
        terms = " ".join(w for w in clean.split() if w not in stop)
        if not terms:
            return self._handle_fallback(sender_id)

        data = self.aliexpress.search_products(terms, limit=3)
        reply = self._format_response(data, terms)
        self.whatsapp.send_text_message(sender_id, reply)

    def _handle_fallback(self, sender_id: str):
        txt = ("Desculpe, não entendi. 🤔\n"
               "Tente: 'Quero um fone bluetooth' ou 'Procuro um smartwatch'.")
        self.whatsapp.send_text_message(sender_id, txt)

    def _format_response(self, data: dict, query: str) -> str:
        if "error_response" in data:
            return "😔 Erro ao buscar no AliExpress. Tente novamente mais tarde."
        prods = (data.get("aliexpress_affiliate_product_query_response", {})
                     .get("resp_result", {})
                     .get("result", {})
                     .get("products", {})
                     .get("product", []))
        if not prods:
            return f"⚠️ Não achei '{query}'. Tente outro termo."

        lines = [f"Aqui estão opções para '{query}':"]
        for p in prods:
            title = p.get("product_title", "-")
            price = p.get("target_sale_price", "-")
            link = p.get("promotion_link") or p.get("product_detail_url", "")
            lines.append(f"🛒 {title}\n💰 {price}\n🔗 {link}")
        return "\n\n".join(lines)

# ==============================================================================
# FLASK & ROTAS
# ==============================================================================
app = Flask(__name__)
zafira = ZafiraCore()
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if (request.args.get("hub.mode") == "subscribe" and
            request.args.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN):
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    payload = request.get_json(force=True)
    logger.info("Webhook recebido: %s", json.dumps(payload, indent=2, ensure_ascii=False))
    try:
        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = msg["from"]
        text = msg["text"]["body"]
        zafira.process_message(sender, text)
    except Exception:
        logger.info("Ignorado: webhook sem texto.")
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
