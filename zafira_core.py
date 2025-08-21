# zafira_core_fixed.py

import logging
from typing import Dict, Optional
from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient
import re

logger = logging.getLogger(__name__)

class ZafiraCore:
    """
    Núcleo de inteligência da Zafira.
    Processa mensagens, detecta intenções e coordena as ações.
    VERSÃO COM CORREÇÃO DE BUG ('bool' object is not subscriptable)
    """
    def __init__(self):
        self.whatsapp_client = WhatsAppClient()
        self.aliexpress_client = AliExpressClient()
        logger.info("Zafira Core inicializada com sucesso")

    def process_message(self, sender_id: str, message: str) -> bool:
        """Processa uma mensagem recebida."""
        logger.info(f"Processando mensagem de {sender_id}: {message}")
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
            logger.error(f"Erro ao processar mensagem: {e}")
            self.whatsapp_client.send_error_message(sender_id)
            return False

    def _detect_intent(self, message: str) -> str:
        """Detecta a intenção do usuário com base na mensagem."""
        message_lower = message.lower()
        
        # Palavras-chave para saudação
        greeting_keywords = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e aí", "eae", "tudo bem", "zafira"]
        # Palavras-chave para intenção de produto
        product_keywords = ["quero", "gostaria", "procuro", "encontrar", "achar", "tem", "vende", "preço", "valor", "quanto custa", "comprar"]

        if any(keyword in message_lower for keyword in greeting_keywords):
            # Se for apenas "zafira", também é uma saudação
            if message_lower.strip() == "zafira":
                return "saudacao"
            # Se tiver palavras de produto, prioriza a busca
            if any(prod_keyword in message_lower for prod_keyword in product_keywords):
                return "produto"
            return "saudacao"

        if any(keyword in message_lower for keyword in product_keywords):
            return "produto"
            
        return "desconhecido"

    def _handle_greeting(self, sender_id: str) -> bool:
        """Lida com a intenção de saudação."""
        response_text = "Oi! 😊 Sou a Zafira, sua assistente de compras! \n\nPosso te ajudar a encontrar as melhores ofertas no AliExpress. O que você está procurando hoje?"
        success = self.whatsapp_client.send_text_message(sender_id, response_text)
        if success:
            logger.info(f"Resposta de saudação enviada com sucesso para {sender_id}")
        return success

    def _handle_product_intent(self, sender_id: str, message: str) -> bool:
        """Lida com a intenção de buscar um produto."""
        search_terms = self._extract_search_terms(message)
        logger.info(f"Termos de busca extraídos: {search_terms}")

        if not search_terms:
            return self._handle_fallback(sender_id)

        products = self.aliexpress_client.search_products(search_terms)

        # FIX: Adicionada verificação para garantir que 'products' é uma lista antes de prosseguir
        if products and isinstance(products, list):
            logger.info(f"Encontrados {len(products)} produtos para '{search_terms}'")
            response_text = self._format_product_response(products, search_terms)
            success = self.whatsapp_client.send_text_message(sender_id, response_text)
        else:
            logger.warning(f"Nenhum produto encontrado para '{search_terms}'")
            response_text = f"Não encontrei produtos para '{search_terms}' no momento 😔. Tente descrever o produto de outra forma!"
            success = self.whatsapp_client.send_text_message(sender_id, response_text)
        
        if success:
            logger.info(f"Resposta de produto enviada com sucesso para {sender_id}")
        return success

    def _handle_fallback(self, sender_id: str) -> bool:
        """Lida com mensagens não compreendidas."""
        response_text = "Desculpe, não entendi o que você quis dizer. 🤔\n\nTente me dizer o que você quer comprar, por exemplo: 'Quero um fone bluetooth' ou 'Procuro um vestido de festa'."
        success = self.whatsapp_client.send_text_message(sender_id, response_text)
        if success:
            logger.info(f"Resposta de fallback enviada com sucesso para {sender_id}")
        return success

    def _extract_search_terms(self, message: str) -> str:
        """Extrai os termos de busca da mensagem do usuário."""
        # Remove palavras-chave comuns e artigos para limpar a busca
        stopwords = ["quero", "gostaria", "procuro", "encontrar", "achar", "tem", "vende", "preço", "valor", "quanto custa", "comprar", "um", "uma", "o", "a", "de", "do", "da", "para", "com"]
        
        # Remove pontuação
        message_clean = re.sub(r'[^\w\s]', '', message)
        
        words = message_clean.lower().split()
        search_terms = [word for word in words if word not in stopwords]
        
        return " ".join(search_terms)

    def _format_product_response(self, products: list, query: str) -> str:
        """Formata a lista de produtos em uma única mensagem de texto."""
        if not products:
            return f"Não encontrei produtos para '{query}' no momento 😔. Tente descrever o produto de outra forma!"

        header = f"Aqui estão os 3 melhores resultados para '{query}' que encontrei no AliExpress! 🚀\n\n"
        
        product_lines = []
        for i, product in enumerate(products[:3]):
            title = product.get('product_title', 'Produto sem título')
            price = product.get('target_sale_price', 'Preço indisponível')
            rating = product.get('evaluate_rate', 'Sem avaliação')
            link = product.get('promotion_link', '')

            # Limita o título para não ficar muito longo
            if len(title) > 60:
                title = title[:57] + "..."

            line = f"*{i+1}. {title}*\n" \
                   f"💰 *Preço:* {price}\n" \
                   f"⭐ *Avaliação:* {rating}\n" \
                   f"🔗 *Link:* {link}\n"
            product_lines.append(line)
        
        return header + "\n".join(product_lines)

