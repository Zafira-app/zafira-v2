import os
import json
import logging
import re
import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ==============================================================================
# CONFIGURAÇÃO BÁSICA
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()

# ==============================================================================
# CLASSE DO CLIENTE WHATSAPP
# ==============================================================================
class WhatsAppClient:
    def __init__(self):
        self.api_url = "https://graph.facebook.com/v20.0/"
        self.token = os.getenv("WHATSAPP_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        if not all([self.token, self.phone_number_id]):
            logger.error("Credenciais do WhatsApp não configuradas!")
        else:
            logger.info("Cliente WhatsApp inicializado com sucesso.")

    def send_text_message(self, recipient_id: str, message: str) -> bool:
        if not all([self.token, self.phone_number_id]):
            logger.error("Não é possível enviar mensagem, credenciais ausentes.")
            return False

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
            logger.info(f"Mensagem enviada para {recipient_id}.")
            return True
        except requests.RequestException as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False

# ==============================================================================
# CLASSE DO CLIENTE ALIEXPRESS (COM ASSINATURA CORRIGIDA)
# ==============================================================================
class AliExpressClient:
    def __init__(self, app_key: str, app_secret: str, tracking_id: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.tracking_id = tracking_id
        self.api_url = "https://api-sg.aliexpress.com/sync"
        logger.info("Cliente AliExpress inicializado.")

    def _generate_signature(self, params: dict) -> str:
        """
        Gera assinatura HMAC-SHA256 no formato exigido pelo AliExpress
        (concatenação ordenada dos parâmetros, chave = app_secret).
        """
        sorted_items = sorted(params.items())
        concat = "".join(f"{k}{v}" for k, v in sorted_items)
        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            concat.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        return signature

    def search_products(self, keywords: str, limit: int = 3) -> dict:
        """
        Chama aliexpress.affiliate.product.query e retorna o JSON bruto.
        """
        params = {
            "app_key": self.app_key,
            "method": "aliexpress.affiliate.product.query",
            "sign_method": "hmac",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "keywords": keywords,
            "tracking_id": self.tracking_id,
            "page_size": str(limit),
            "target_language": "pt",
            "target_currency": "BRL",
            "ship_to_country": "BR"
        }
        params["sign"] = self._generate_signature(params)

        try:
            resp = requests.get(self.api_url, params=params, timeout=40)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Erro na chamada AliExpress: {e}")
            return {"error": str(e)}

# ==============================================================================
# CLASSE DO NÚCLEO DA ZAFIRA
# ==============================================================================
class ZafiraCore:
    def __init__(self):
        self.whatsapp = WhatsAppClient()
        self.aliexpress = AliExpressClient
