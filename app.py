# app.py - VERSÃO FINAL E VITORIOSA

import os
import json
import logging
import re
import requests
import hashlib
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ==============================================================================
# CONFIGURAÇÃO BÁSICA
# ==============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

# ==============================================================================
# CLASSE DO CLIENTE WHATSAPP
# ==============================================================================
class WhatsAppClient:
    def __init__(self):
        self.api_url = "https://graph.facebook.com/v20.0/"
        self.token = os.getenv("WHATSAPP_TOKEN" )
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
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": recipient_id, "type": "text", "text": {"body": message}}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            logger.info(f"Mensagem enviada com sucesso para {recipient_id}.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Exceção ao enviar mensagem para {recipient_id}: {e}")
            return False

# ==============================================================================
# CLASSE DO CLIENTE ALIEXPRESS
# ==============================================================================
class AliExpressClient:
    def __init__(self):
        self.api_url = "https://api-sg.aliexpress.com/sync"
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY" )
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais críticas do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress (API Affiliate com Assinatura Oficial) inicializado.")

    def _generate_signature(self, params: dict) -> str:
        sorted_params = sorted(params.items())
        concatenated_string = "".join([f"{k}{v}" for k, v in sorted_params])
        string_to_sign = self.app_secret + concatenated_string
        signature = hashlib.sha256(string_to_sign.encode('utf-8')).hexdigest().upper()
        logger.info(f"String para assinar (ocultando secret): app_secret+{concatenated_string}")
        logger.info(f"Assinatura gerada: {signature}")
        return signature

    def search_products(self, keywords: str, limit: int = 3) -> list | bool:
        params = {
            'app_key': self.app_key,
            'method': 'aliexpress.affiliate.product.query',
            'sign_method': 'sha256',
            'timestamp': str(int(time.time() * 1000)),
            'keywords': keywords,
            'tracking_id': self.tracking_id,
            'page_size': str(limit),
            'target_language': 'pt',
            'target_currency': 'BRL',
            'ship_to_country': 'BR'
        }
        params['sign'] = self._generate_signature(params)
        
        try:
            response = requests.post(self.api_url, params=params, timeout=40)
            logger.info(f"Resposta da API - Status: {response.status_code}, Texto: {response.text[:1000]}") # Log aumentado
            response.raise_for_status()
            data = response.json()
            if 'error_response' in data:
                error_info = data['error_response']
                logger.error(f"Erro da API AliExpress: Código {error_info.get('code')}, Mensagem: {error_info.get('msg')}")
                return False
            
            # A resposta de sucesso está aqui
            result = data.get('aliexpress_affiliate_product_query_response', {}).get('resp_result', {}).get('result', {})
            products = result.get('products', {}).get('product', [])
            return products
        except Exception as e:
            logger.error(f"Exceção na busca de produtos: {e}", exc_info=True)
            return False

# ==============================================================================
# CLASSE DO NÚCLEO DA ZAFIRA (COM A CORREÇÃO)
# ==============================================================================
class ZafiraCore:
    def __init__(self):
        self.whatsapp_client = WhatsAppClient()
        self.aliexpress_client = AliExpressClient()
        logger.info("Zafira Core inicializada com sucesso.")

    def process_message(self, sender_id: str, message: str):
        logger.info(f"Processando mensagem de {sender_id}: '{message}'")
        try:
            intent = self._detect_intent(message)
            if intent == "produto":
                self._handle_product_intent(sender_id, message)
            elif intent == "saudacao":
                self._handle_greeting(sender_id)
            else:
                self._handle_fallback(sender_id)
        except Exception as e:
            logger.error(f"Exceção não tratada ao processar mensagem: {e}", exc_info=True)
            self.whatsapp_client.send_text_message(sender_id, "Ops! 😅 Tive um probleminha técnico aqui dentro. Minha equipe já foi notificada. Por favor, tente novamente em um instante!")

    def _detect_intent(self, message: str) -> str:
        message_lower = message.lower().strip()
        product_keywords = ["quero", "gostaria", "procuro", "encontrar", "achar", "tem", "vende", "preço", "valor", "quanto custa", "comprar", "preciso", "fone", "celular", "smartwatch", "vestido", "tenis", "mochila", "câmera", "drone", "caneca", "tablet"]
        greeting_keywords = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e aí", "eae", "tudo bem", "zafira"]
        if any(keyword in message_lower for keyword in product_keywords): return "produto"
        if any(keyword in message_lower for keyword in greeting_keywords): return "saudacao"
        return "desconhecido"

    def _handle_greeting(self, sender_id: str):
        response_text = "Oi! 😊 Sou a Zafira, sua assistente de compras! \n\nPosso te ajudar a encontrar as melhores ofertas no AliExpress. O que você está procurando hoje?"
        self.whatsapp_client.send_text_message(sender_id, response_text)

    def _handle_product_intent(self, sender_id: str, message: str):
        search_terms = self._extract_search_terms(message)
        if not search_terms:
            self._handle_fallback(sender_id)
            return
        
        products = self.aliexpress_client.search_products(search_terms)
        
        # CORREÇÃO FINAL: Verifica se a lista de produtos existe e não está vazia
        if products and isinstance(products, list) and len(products) > 0:
            response_text = self._format_product_response(products, search_terms)
        else:
            response_text = f"Não encontrei produtos para '{search_terms}' no momento 😔. Tente descrever o produto de outra forma!"
        
        self.whatsapp_client.send_text_message(sender_id, response_text)

    def _handle_fallback(self, sender_id: str):
        response_text = "Desculpe, não entendi o que você quis dizer. 🤔\n\nTente me dizer o que você quer comprar, por exemplo: 'Quero um fone bluetooth' ou 'Procuro um vestido de festa'."
        self.whatsapp_client.send_text_message(sender_id, response_text)

    def _extract_search_terms(self, message: str) -> str:
        stopwords = ["quero", "gostaria", "procuro", "encontrar", "achar", "tem", "vende", "preço", "valor", "quanto custa", "comprar", "um", "uma", "o", "a", "de", "do", "da", "para", "com", "preciso", "reais", "até"]
        message_clean = re.sub(r'[^\w\s]', '', message)
        words = message_clean.lower().split()
        return " ".join([word for word in words if word not in stopwords and not word.isdigit()])

    def _format_product_response(self, products: list, query: str) -> str:
        header = f"Aqui estão os melhores resultados para '{query}' que encontrei no AliExpress! 🚀\n\n"
        product_lines = []
        for i, product in enumerate(products[:3]):
            title = product.get('product_title', 'Produto sem título')
            price = product.get('target_sale_price', 'Preço indisponível')
            rating = product.get('evaluate_rate', 'Sem avaliação')
            link = product.get('promotion_link', '')
            if len(title) > 60: title = title[:57] + "..."
            line = f"*{i+1}. {title}*\n💰 *Preço:* {price}\n⭐ *Avaliação:* {rating}\n🔗 *Link:* {link}\n"
            product_lines.append(line)
        return header + "\n".join(product_lines)

# ==============================================================================
# INICIALIZAÇÃO DO SERVIDOR FLASK
# ==============================================================================
app = Flask(__name__)
zafira = ZafiraCore()
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

@app.route('/health', methods=['GET'])
def health_check():
    return "OK", 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == WHATSAPP_VERIFY_TOKEN:
            return request.args.get('hub.challenge'), 200
        return "Forbidden", 403
    if request.method == 'POST':
        data = request.get_json()
        logger.info(f"Webhook recebido: {json.dumps(data, indent=2)}")
        try:
            message_data = data['entry'][0]['changes'][0]['value']['messages'][0]
            sender_id = message_data['from']
            message_text = message_data['text']['body']
            zafira.process_message(sender_id, message_text)
        except (IndexError, KeyError):
            logger.info("Notificação de webhook ignorada (não é uma mensagem de texto).")
        return jsonify({"status": "ok"}), 200
