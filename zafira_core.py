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
        logger.info(f"[PROCESS] Mensagem de {sender_id}: '{message}'")
        intent = self._detect_intent(message)
        logger.info(f"[PROCESS] Intent detectada: {intent}")

        if intent == "mercearia":
            self._handle_grocery(sender_id, message)
        elif intent == "produto":
            self._handle_product(sender_id, message)
        elif intent == "saudacao":
            self._handle_greeting(sender_id)
        else:
            self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()
        if any(k in m for k in ["arroz","feijão","feijao","mercearia"]):
            return "mercearia"
        if any(k in m for k in ["quero","procuro","comprar","busco",
                                "fone","celular","smartwatch","tênis","tenis"]):
            return "produto"
        if any(k in m for k in ["oi","olá","ola","e aí"]):
            return "saudacao"
        return "desconhecido"

    def _handle_greeting(self, sender_id: str):
        text = (
            "Oi! 😊 Sou a Zafira, sua assistente de compras.\n"
            "Eletrônicos ou mercearia – o que você procura hoje?"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_product(self, sender_id: str, message: str):
        terms = self._clean_terms(message)
        if not terms:
            return self._handle_fallback(sender_id)

        data = self.aliexpress.search_products(terms, limit=5, page_no=1)
        reply = self._format_aliexpress(data, terms)
        self.whatsapp.send_text_message(sender_id, reply)

    def _handle_grocery(self, sender_id: str, message: str):
        terms = self._clean_terms(message)
        if not terms:
            return self._handle_fallback(sender_id)

        data = self.groc.search_items(terms, limit=5)
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
            "um","uma","o","a","de","do","da","para","com",
            "reais","quero","procuro","comprar","busco"
        }
        return " ".join(w for w in clean.split() if w not in stop)

    def _format_aliexpress(self, data: dict, query: str) -> str:
        if "error" in data or "error_response" in data:
            return "😔 Erro ao buscar no AliExpress. Tente novamente mais tarde."

        resp     = data.get("aliexpress_affiliate_product_query_response", {})
        resp_res = resp.get("resp_result", {}) or resp.get("resposta", {})
        result   = resp_res.get("result") or resp_res.get("resultado") or {}
        prod_ct  = result.get("products") or result.get("produtos") or {}
        products = prod_ct.get("product") or prod_ct.get("produto") or []

        if not products:
            return f"⚠️ Não achei '{query}' no AliExpress."

        # Lista apenas os 3 primeiros produtos, título e preço
        lines = [f"Encontrei esses resultados para '{query}':"]
        for p in products[:3]:
            title = p.get("product_title") or p.get("titulo_produto") or "-"
            price = p.get("target_sale_price") or p.get("preco_alvo") or "-"
            lines.append(f"• {title} — R${price}")

        lines.append(
            "🔗 Quer ver os links completos? Peça 'Links dos produtos'."
        )
        return "\n".join(lines)

    def _format_groc(self, data: dict, query: str) -> str:
        if "error" in data:
            return "😔 Erro ao buscar na mercearia. Tente novamente mais tarde."

        items = data.get("items") or data.get("itens") or []
        if not items:
            return f"⚠️ Não achei '{query}' na mercearia."

        lines = [f"Encontrei estes itens de mercearia para '{query}':"]
        for it in items[:5]:
            name  = it.get("name")  or it.get("nome")  or "-"
            price = it.get("price") or it.get("preco") or "-"
            lines.append(f"• {name} — R${price}")

        return "\n".join(lines)
