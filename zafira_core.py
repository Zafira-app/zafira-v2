import re
import logging

from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient
from clients.groc_client import GROCClient

logger = logging.getLogger(__name__)

class ZafiraCore:
    def __init__(self):
        self.whatsapp       = WhatsAppClient()
        self.aliexpress     = AliExpressClient()
        self.groc           = GROCClient()
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

    def _extract_price_limits(self, msg: str) -> tuple[float|None, float|None]:
        """
        Regex para extrair 'min a max reais' ou 'até max reais'.
        Retorna (min_price, max_price).
        """
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:a|até|-)\s*(\d+(?:[.,]\d+)?)\s*(?:reais|rs)?", msg)
        if m:
            low = float(m.group(1).replace(",","."))
            hi  = float(m.group(2).replace(",","."))
            return low, hi

        m2 = re.search(r"até\s*(\d+(?:[.,]\d+)?)\s*(?:reais|rs)?", msg)
        if m2:
            hi = float(m2.group(1).replace(",","."))
            return None, hi

        return None, None

    def _handle_product(self, sender_id: str, message: str):
        terms = self._clean_terms(message)
        if not terms:
            return self._handle_fallback(sender_id)

        # extrai orçamento
        min_price, max_price = self._extract_price_limits(message)
        logger.info(f"[PRODUCT] Termos: '{terms}', min_price={min_price}, max_price={max_price}")

        # busca sempre page_no=1
        data = self.aliexpress.search_products(terms, limit=10, page_no=1)
        products = (
            data.get("aliexpress_affiliate_product_query_response", {})
                .get("resp_result", {})
                .get("result", {})
                .get("products", {})
                .get("product", [])
        ) or []

        # filtra por preço, se extraído
        def price_val(p):
            v = p.get("target_sale_price", p.get("preco_alvo","0"))
            return float(v.replace(",",".").replace("R$","").strip() or 0)
        if min_price is not None:
            products = [p for p in products if price_val(p) >= min_price]
        if max_price is not None:
            products = [p for p in products if price_val(p) <= max_price]

        # guarda os 3 primeiros para 'links'
        self._last_products = products[:3]
        self._last_query    = terms

        # formata mensagem curta
        if not self._last_products:
            text = f"⚠️ Não achei '{terms}' dentro do orçamento."
        else:
            lines = [f"Encontrei estes resultados para '{terms}':"]
            for p in self._last_products:
                title = p.get("product_title","-")
                price = p.get("target_sale_price","-")
                lines.append(f"• {title} — R${price}")
            lines.append("🔗 Para ver os links completos, peça 'Links dos produtos'.")
            text = "\n".join(lines)

        self.whatsapp.send_text_message(sender_id, text)

    def _handle_links(self, sender_id: str):
        if not self._last_products:
            return self.whatsapp.send_text_message(
                sender_id,
                "Ainda não fiz nenhuma busca de produtos. Tente 'Quero um fone bluetooth' primeiro."
            )

        lines = [f"Links para '{self._last_query}':"]
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
            lines = [f"Itens de mercearia para '{terms}':"]
            for it in items[:5]:
                name  = it.get("name") or it.get("nome","-")
                price = it.get("price") or it.get("preco","-")
                lines.append(f"• {name} — R${price}")
            text = "\n".join(lines)

        self.whatsapp.send_text_message(sender_id, text)

    def _handle_greeting(self, sender_id: str):
        text = (
            "Oi! 😊 Sou a Zafira, sua assistente de compras.\n"
            "Eletrônicos ou mercearia – o que você procura hoje?\n"
            "Você pode definir um orçamento: 'celular até 3000 reais'."
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_fallback(self, sender_id: str):
        text = (
            "Desculpe, não entendi. 🤔\n"
            "Tente:\n"
            "- 'Quero um fone bluetooth'\n"
            "- 'Quero um celular até 3000 reais'\n"
            "- 'Preciso de arroz e feijão'\n"
            "- 'Links dos produtos'"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _clean_terms(self, message: str) -> str:
        clean = re.sub(r"[^\w\s]", "", message.lower())
        stop = {
            "um","uma","o","a","de","do","da","para","com",
            "reais","quero","procuro","comprar","busco","até"
        }
        return " ".join(w for w in clean.split() if w not in stop)
