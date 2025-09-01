# app.py - VERSÃO COM BUSCA APRIMORADA (STOPWORDS + ORDENAÇÃO)

import os
import json
import logging
import re
import time
import hashlib
import random
import requests
from urllib.parse import quote_plus

from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ==============================================================================
# CARREGA VARIÁVEIS DE AMBIENTE E CONFIGURA LOG
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
        self.api_url         = "https://graph.facebook.com/v20.0/"
        self.token           = os.getenv("WHATSAPP_TOKEN", "" )
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        if not (self.token and self.phone_number_id):
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
# CLIENTE ALIEXPRESS (com busca aprimorada)
# ==============================================================================
class AliExpressClient:
    def __init__(self):
        self.api_url     = os.getenv("AE_PROXY_URL", "https://api-sg.aliexpress.com/sync" )
        self.app_key     = os.getenv("ALIEXPRESS_APP_KEY", "")
        self.app_secret  = os.getenv("ALIEXPRESS_APP_SECRET", "")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID", "")

        if not (self.app_key and self.app_secret and self.tracking_id):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress inicializado.")

    def _generate_signature(self, params: dict) -> str:
        items   = sorted(params.items())
        encoded = [(k, quote_plus(str(v))) for k, v in items]
        concat  = "".join(f"{k}{v}" for k, v in encoded)
        raw     = f"{self.app_secret}{concat}{self.app_secret}".encode("utf-8")
        return hashlib.md5(raw).hexdigest().upper()

    def search_products(self, keywords: str, limit: int = 3) -> dict:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        page_no   = random.randint(1, 3) # Reduzido para focar nas páginas mais relevantes

        params = {
            "app_key":          self.app_key,
            "method":           "aliexpress.affiliate.product.query",
            "sign_method":      "md5",
            "timestamp":        timestamp,
            "keywords":         keywords,
            "tracking_id":      self.tracking_id,
            "page_size":        str(limit),
            "page_no":          str(page_no),
            "target_language":  "pt",
            "target_currency":  "BRL",
            "ship_to_country":  "BR",
            # MELHORIA: Ordena pelos mais vendidos para aumentar a relevância
            "sort":             "LAST_VOLUME_DESC"
        }
        params["sign"] = self._generate_signature(params)

        prepared = requests.Request("GET", self.api_url, params=params).prepare()
        logger.info("AliExpress QUERY URL: %s", prepared.url)

        try:
            resp = requests.get(self.api_url, params=params, timeout=40)
            logger.info("AliExpress STATUS: %s", resp.status_code)
            logger.debug("AliExpress BODY: %s", resp.text)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Erro na API AliExpress: {e}")
            return {"error": str(e)}

# ==============================================================================
# NÚCLEO DA ZAFIRA (com extração de termos aprimorada)
# ==============================================================================
class ZafiraCore:
    def __init__(self):
        self.whatsapp   = WhatsAppClient()
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
        # Lista de palavras-chave expandida para melhor detecção
        product_keywords = [
            "quero", "procuro", "comprar", "encontrar", "achar", "tem", "vende", 
            "preço", "valor", "quanto custa", "preciso", "fone", "celular", 
            "smartwatch", "vestido", "tenis", "tênis", "mochila", "câmera", "drone"
        ]
        greeting_keywords = ["oi", "olá", "ola", "e aí", "bom dia", "boa tarde", "boa noite"]
        
        if any(k in m for k in product_keywords):
            return "produto"
        if any(k in m for k in greeting_keywords):
            return "saudacao"
        return "desconhecido"

    def _handle_greeting(self, sender_id: str):
        text = "Oi! 😊 Sou a Zafira, sua assistente de compras. O que você procura hoje?"
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_product(self, sender_id: str, message: str):
        # MELHORIA: A extração de termos agora é mais agressiva
        search_terms = self._extract_search_terms(message)
        
        if not search_terms:
            logger.warning("Nenhum termo de busca válido extraído da mensagem: '%s'", message)
            return self._handle_fallback(sender_id)

        logger.info("Termos de busca extraídos: '%s'", search_terms)
        data  = self.aliexpress.search_products(search_terms, limit=5) # Aumentei para 5 para ter mais chance de filtrar
        reply = self._format_response(data, search_terms)
        self.whatsapp.send_text_message(sender_id, reply)

    def _handle_fallback(self, sender_id: str):
        txt = ("Desculpe, não entendi. 🤔\n"
               "Tente: 'Quero um fone bluetooth' ou 'Procuro um smartwatch'.")
        self.whatsapp.send_text_message(sender_id, txt)

    def _extract_search_terms(self, message: str) -> str:
        """
        Limpa a mensagem, remove stopwords e retorna os termos de busca puros.
        """
        clean_message = re.sub(r"[^\w\s]", "", message.lower())
        
        # Lista de stopwords expandida para melhorar a qualidade da busca
        stopwords = {
            "quero", "gostaria", "procuro", "encontrar", "achar", "tem", "vende", 
            "preço", "valor", "quanto", "custa", "comprar", "preciso", "me", "veja",
            "um", "uma", "uns", "umas", "o", "a", "os", "as", "de", "do", "da", "dos", 
            "das", "para", "com", "sem", "em", "no", "na", "nos", "nas", "por", "e", "ou"
        }
        
        words = clean_message.split()
        meaningful_words = [word for word in words if word not in stopwords and not word.isdigit()]
        
        return " ".join(meaningful_words)

    def _format_response(self, data: dict, query: str) -> str:
        if "error_response" in data or "error" in data:
            logger.error("Erro recebido da API AliExpress: %s", data)
            return "😔 Tive um problema para buscar no AliExpress. Por favor, tente novamente mais tarde."
        
        products = (data.get("aliexpress_affiliate_product_query_response", {})
                        .get("resp_result", {})
                        .get("result", {})
                        .get("products", {})
                        .get("product", []))
        
        if not products:
            return f"⚠️ Não encontrei resultados para '{query}'. Que tal tentar um termo diferente?"

        # Filtra produtos com pouca informação ou sem link
        valid_products = [p for p in products if p.get("product_title") and (p.get("promotion_link") or p.get("product_detail_url"))]
        
        if not valid_products:
            return f"⚠️ Encontrei alguns itens para '{query}', mas não parecem ser boas opções. Pode tentar ser mais específico?"

        lines = [f"Aqui estão os melhores resultados para '{query}' que encontrei! 🚀"]
        # Mostra até 3 produtos para não poluir a conversa
        for p in valid_products[:3]:
            title = p.get("product_title", "-")
            price = p.get("target_sale_price", "Preço indisponível")
            link  = p.get("promotion_link") or p.get("product_detail_url", "")
            
            # Limita o tamanho do título para melhor visualização
            if len(title) > 70:
                title = title[:67] + "..."

            lines.append(f"🛒 *{title}*\n💰 Preço: {price}\n🔗 Link: {link}")
        
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
        msg    = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = msg["from"]
        text   = msg["text"]["body"]
        zafira.process_message(sender, text)
    except (KeyError, IndexError):
        logger.info("Ignorado: webhook sem texto de mensagem de usuário.")
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
