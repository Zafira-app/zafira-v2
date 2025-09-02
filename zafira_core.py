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
        # Guarda resultados da última busca de produto
        self._last_products = []
        self._last_query    = ""
        logger.info("Zafira Core inicializada (modo clássico).")

    def process_message(self, sender_id: str, message: str):
        logger.info(f"[PROCESS] Mensagem de {sender_id}: '{message}'")
        intent = self._detect_intent(message)
        logger.info(f"[PROCESS] Intent detectada: {intent}")

        if intent == "saudacao":
            self._handle_greeting(sender_id)

        elif intent == "produto":
            self._handle_product(sender_id, message)

        elif intent == "links":
            self._handle_links(sender_id)

        elif intent == "mercearia":
            self._handle_grocery(sender_id, message)

        else:
            self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()
        if any(k in m for k in ["oi","olá","ola","e aí"]):
            return "saudacao"
        if any(k in m for k in ["link","links","url","urls"]):
            return "links"
        if any(k in m for k in ["quero","procuro","comprar","busco",
                                "fone","celular","smartwatch","tênis","tenis"]):
            return "produto"
        if any(k in m for k in ["arroz","feijão","feijao","mercearia"]):
            return "mercearia"
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

        # Extrai e armazena para links
        products = (
            data.get("aliexpress_affiliate_product_query_response", {})
                .get("resp_result", {})
                .get("result", {})
                .get("products", {})
                .get("product", [])
        ) or []
        self._last_products = products[:3]
        self._last_query    = terms

        # Responde só título/preço
        if not self._last_products:
            text = f"⚠️ Não achei '{terms}' no AliExpress."
        else:
            lines = [f"Encontrei esses resultados para '{terms}':"]
            for p in self._last_products:
                title = p.get("product_title", "-")
                price = p.get("target_sale_price", "-")
                lines.append(f"• {title} — R${price}")
            lines.append("🔗 Quer ver os links completos? Peça 'Links dos produtos'.")
            text = "\n".join(lines)

        self.whatsapp.send_text_message(sender_id, text)

    def _handle_links(self, sender_id: str):
        if not self._last_products:
            return self.whatsapp.send_text_message(
                sender_id,
                "Não tenho links armazenados. Faça antes uma busca, ex.: 'Quero um fone bluetooth'."
            )

        lines = [f"Aqui estão os links para '{self._last_query}':"]
        for p in self._last_products:
            url = p.get("promotion_link") or p.get("product_detail_url") or "-"
            lines.append(f"• {url}")
        text = "\n".join(lines)
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_grocery(self, sender_id: str, message: str):
        terms = self._clean_terms(message)
        if not terms:
            return self._handle_fallback(sender_id)

        data = self.groc.search_items(terms, limit=5)
        items = data.get("items") or data.get("itens") or []
        if not items:
            text = f"⚠️ Não achei '{terms}' na mercearia."
        else:
            lines = [f"Encontrei estes itens de mercearia para '{terms}':"]
            for it in items[:5]:
                name  = it.get("name") or it.get("nome") or "-"
                price = it.get("price") or it.get("preco") or "-"
                lines.append(f"• {name} — R${price}")
            text = "\n".join(lines)

        self.whatsapp.send_text_message(sender_id, text)

    def _handle_fallback(self, sender_id: str):
        text = (
            "Desculpe, não entendi. 🤔\n"
            "Tente:\n"
            "- 'Quero um fone bluetooth'\n"
            "- 'Procuro um smartwatch'\n"
            "- 'Preciso de arroz e feijão'\n"
            "- 'Links dos produtos' para ver URLs após buscar"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _clean_terms(self, message: str) -> str:
        clean = re.sub(r"[^\w\s]", "", message.lower())
        stop = {
            "um","uma","o","a","de","do","da","para","com",
            "reais","quero","procuro","comprar","busco"
        }
        return " ".join(w for w in clean.split() if w not in stop)
