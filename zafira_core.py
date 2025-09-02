import re
import logging

from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client  import AliExpressClient
from clients.groc_client       import GROCClient

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
        logger.info("[GREETING] Enviando saudação")
        text = (
            "Oi! 😊 Sou a Zafira, sua assistente de compras.\n"
            "Eletrônicos ou mercearia – o que você procura hoje?"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_product(self, sender_id: str, message: str):
        terms = self._clean_terms(message)
        logger.info(f"[PRODUCT] Termos extraídos: '{terms}'")
        if not terms:
            return self._handle_fallback(sender_id)

        logger.info("[PRODUCT] Chamando AliExpressClient.search_products")
        # força sempre page_no=1
        data = self.aliexpress.search_products(terms, limit=5, page_no=1)

        logger.info("[PRODUCT] Dados recebidos do AliExpress: %s", data)
        reply = self._format_aliexpress(data, terms)
        logger.info("[PRODUCT] Resposta formatada, enviando mensagem")
        self.whatsapp.send_text_message(sender_id, reply)

    def _handle_grocery(self, sender_id: str, message: str):
        terms = self._clean_terms(message)
        logger.info(f"[GROCERY] Termos extraídos: '{terms}'")
        if not terms:
            return self._handle_fallback(sender_id)

        logger.info("[GROCERY] Chamando GROCClient.search_items")
        data = self.groc.search_items(terms, limit=5)
        logger.info("[GROCERY] Dados recebidos do GROC: %s", data)
        reply = self._format_groc(data, terms)
        logger.info("[GROCERY] Resposta formatada, enviando mensagem")
        self.whatsapp.send_text_message(sender_id, reply)

    def _handle_fallback(self, sender_id: str):
        logger.info("[FALLBACK] Nenhuma intent reconhecida")
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

        lines = [f"Aqui estão opções para '{query}':"]
        for p in products:
            title = p.get("product_title")      or p.get("titulo_produto")         or "-"
            price = p.get("target_sale_price")  or p.get("preco_alvo")             or "-"
            link  = p.get("promotion_link")     or p.get("product_detail_url")     or p.get("url_detalhe_produto") or "-"
            lines.append(f"🛒 {title}\n💰 {price}\n🔗 {link}")

        return "\n\n".join(lines)

    def _format_groc(self, data: dict, query: str) -> str:
        if "error" in data:
            return "😔 Erro ao buscar na mercearia. Tente novamente mais tarde."

        items = data.get("items") or data.get("itens") or []
        if not items:
            return f"⚠️ Não achei '{query}' na mercearia."

        lines = [f"Encontrei estes itens na mercearia para '{query}':"]
        for it in items:
            name  = it.get("name")  or it.get("nome")  or "-"
            price = it.get("price") or it.get("preco") or "-"
            lines.append(f"• {name} — R${price}")

        return "\n".join(lines)
