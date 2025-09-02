import re
import logging

from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient
from clients.groc_client import GROCClient

logger = logging.getLogger(__name__)

class ZafiraCore:
    def __init__(self):
        self.whatsapp   = WhatsAppClient()
        self.aliexpress = AliExpressClient()
        self.groc       = GROCClient()
        logger.info("Zafira Core inicializada (modo clássico).")

    def process_message(self, sender_id: str, message: str):
        logger.info(f"Recebido de {sender_id}: {message}")
        lower = message.lower()

        if any(k in lower for k in ["arroz", "feijão", "feijao", "mercearia"]):
            self._handle_grocery(sender_id, message)

        elif any(k in lower for k in ["quero", "procuro", "comprar",
                                      "fone", "celular", "smartwatch",
                                      "tênis", "tenis"]):
            self._handle_product(sender_id, message)

        elif any(k in lower for k in ["oi", "olá", "ola", "e aí"]):
            self._handle_greeting(sender_id)

        else:
            self._handle_fallback(sender_id)

    def _handle_greeting(self, sender_id: str):
        text = (
            "Oi! 😊 Sou a Zafira, sua assistente de compras.\n"
            "Posso ajudar com eletrônicos ou itens de mercearia.\n"
            "O que você procura hoje?"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_product(self, sender_id: str, message: str):
        terms = self._clean_terms(message)
        if not terms:
            return self._handle_fallback(sender_id)

        data  = self.aliexpress.search_products(terms, limit=5)
        reply = self._format_aliexpress(data, terms)
        self.whatsapp.send_text_message(sender_id, reply)

    def _handle_grocery(self, sender_id: str, message: str):
        terms = self._clean_terms(message)
        if not terms:
            return self._handle_fallback(sender_id)

        data  = self.groc.search_items(terms, limit=5)
        reply = self._format_groc(data, terms)
        self.whatsapp.send_text_message(sender_id, reply)

    def _handle_fallback(self, sender_id: str):
        text = (
            "Desculpe, não entendi. 🤔\n"
            "Tente:\n"
            "- 'Quero um fone bluetooth'\n"
            "- 'Procuro um smartwatch'\n"
            "- 'Preciso de arroz e feijão'"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _clean_terms(self, message: str) -> str:
        clean = re.sub(r"[^\w\s]", "", message.lower())
        stop = {
            "um", "uma", "o", "a", "de", "do", "da", "para", "com",
            "reais", "quero", "procuro", "comprar"
        }
        return " ".join(w for w in clean.split() if w not in stop)

    def _format_aliexpress(self, data: dict, query: str) -> str:
        if "error" in data or "error_response" in data:
            return "😔 Erro ao buscar no AliExpress. Tente novamente mais tarde."

        products = (
            data.get("aliexpress_affiliate_product_query_response", {})
                .get("resp_result", {})
                .get("result", {})
                .get("products", {})
                .get("product", [])
        )
        if not products:
            return f"⚠️ Não achei '{query}' no AliExpress."

        lines = [f"Aqui estão opções para '{query}':"]
        for p in products:
            title = p.get("product_title", "-")
            price = p.get("target_sale_price", "-")
            link  = p.get("promotion_link") or p.get("product_detail_url", "")
            lines.append(f"🛒 {title}\n💰 {price}\n🔗 {link}")
        return "\n\n".join(lines)

    def _format_groc(self, data: dict, query: str) -> str:
        if "error" in data:
            return "😔 Erro ao buscar na mercearia. Tente novamente mais tarde."

        items = data.get("items", [])
        if not items:
            return f"⚠️ Não achei '{query}' na mercearia."

        lines = [f"Encontrei estes itens na mercearia para '{query}':"]
        for it in items:
            name  = it.get("name", "-")
            price = it.get("price", "-")
            lines.append(f"• {name} — R${price}")
        return "\n".join(lines)
