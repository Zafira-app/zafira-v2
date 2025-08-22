# zafira_core.py - VERSÃO FINALÍSSIMA COM CORREÇÃO DO NameError

import logging
from typing import Dict, Optional
from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient
import re

logger = logging.getLogger(__name__)

class ZafiraCore:
    def __init__(self):
        self.whatsapp_client = WhatsAppClient()
        self.aliexpress_client = AliExpressClient()
        logger.info("Zafira Core inicializada com sucesso")

    def process_message(self, sender_id: str, message: str) -> bool:
        logger.info(f"Processando mensagem de {sender_id}: '{message}'")
        try:
            intent = self._detect_intent(message)
            logger.info(f"Intenção detectada: {intent}")

            if intent == "saudacao":
                return self._handle_greeting(sender_id)
            elif intent == "produto":
                return self._handle_product_intent(sender_id, message)
            else:
                return self._handle_fallback(sender_id)
        except Exception as e:
            logger.error(f"Exceção não tratada ao processar mensagem: {e}", exc_info=True)
            self.whatsapp_client.send_error_message(sender_id)
            return False

    def _detect_intent(self, message: str) -> str:
        message_lower = message.lower()
        greeting_keywords = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e aí", "eae", "tudo bem", "zafira"]
        product_keywords = ["quero", "gostaria", "procuro", "encontrar", "achar", "tem", "vende", "preço", "valor", "quanto custa", "comprar", "preciso de"]

        if any(keyword in message_lower for keyword in greeting_keywords):
            if message_lower.strip() == "zafira":
                return "saudacao"
            if any(prod_keyword in message_lower for prod_keyword in product_keywords):
                return "produto"
            return "saudacao"

        # FIX: Corrigido o erro de digitação de 'keyword' para 'prod_keyword'
        if any(prod_keyword in message_lower for prod_keyword in product_keywords):
            return "produto"
            
        return "desconhecido"

    def _handle_greeting(self, sender_id: str) -> bool:
        response_text = "Oi! 😊 Sou a Zafira, sua assistente de compras! \n\nPosso te ajudar a encontrar as melhores ofertas no AliExpress. O que você está procurando hoje?"
        return self.whatsapp_client.send_text_message(sender_id, response_text)

    def _handle_product_intent(self, sender_id: str, message: str) -> bool:
        search_terms = self._extract_search_terms(message)
        logger.info(f"Termos de busca extraídos: '{search_terms}'")

        if not search_terms:
            return self._handle_fallback(sender_id)

        # Assumindo que você já adicionou o IP 54.188.71.94 na whitelist
        products = self.aliexpress_client.search_products(search_terms)

        if products and isinstance(products, list):
            logger.info(f"Encontrados {len(products)} produtos para '{search_terms}'")
            response_text = self._format_product_response(products, search_terms)
            return self.whatsapp_client.send_text_message(sender_id, response_text)
        else:
            logger.warning(f"Nenhum produto encontrado ou falha na API para '{search_terms}'")
            response_text = f"Não encontrei produtos para '{search_terms}' no momento 😔. Tente descrever o produto de outra forma!"
            return self.whatsapp_client.send_text_message(sender_id, response_text)

    def _handle_fallback(self, sender_id: str) -> bool:
        response_text = "Desculpe, não entendi o que você quis dizer. 🤔\n\nTente me dizer o que você quer comprar, por exemplo: 'Quero um fone bluetooth' ou 'Procuro um vestido de festa'."
        return self.whatsapp_client.send_text_message(sender_id, response_text)

    def _extract_search_terms(self, message: str) -> str:
        stopwords = ["quero", "gostaria", "procuro", "encontrar", "achar", "tem", "vende", "preço", "valor", "quanto custa", "comprar", "um", "uma", "o", "a", "de", "do", "da", "para", "com", "preciso"]
        message_clean = re.sub(r'[^\w\s]', '', message)
        words = message_clean.lower().split()
        search_terms = [word for word in words if word not in stopwords]
        return " ".join(search_terms)

    def _format_product_response(self, products: list, query: str) -> str:
        if not products:
            return f"Não encontrei produtos para '{query}' no momento 😔. Tente descrever o produto de outra forma!"

        header = f"Aqui estão os 3 melhores resultados para '{query}' que encontrei no AliExpress! 🚀\n\n"
        
        product_lines = []
        for i, product in enumerate(products[:3]):
            title = product.get('product_title', 'Produto sem título')
            price_info = product.get('target_sale_price', {})
            price = price_info.get('sale_price', 'Preço indisponível')
            rating = product.get('evaluate_rate', 'Sem avaliação')
            link = product.get('promotion_link', '')

            if len(title) > 60:
                title = title[:57] + "..."

            line = f"*{i+1}. {title}*\n" \
                   f"💰 *Preço:* R$ {price}\n" \
                   f"⭐ *Avaliação:* {rating}\n" \
                   f"🔗 *Link:* {link}\n"
            product_lines.append(line)
        
        return header + "\n".join(product_lines)
