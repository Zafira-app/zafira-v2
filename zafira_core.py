# zafira_core.py

import os
import re
import logging

from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient
from clients.groc_client import GROCClient

logger = logging.getLogger(__name__)

class ZafiraCore:
    def __init__(self):
        # inicializa clientes
        self.whatsapp   = WhatsAppClient()
        self.aliexpress = AliExpressClient()
        self.groc       = GROCClient()

        # configurações de administrador
        self.admin_ids    = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin    = os.getenv("ADMIN_PIN", "").strip()
        # estados: "aguardando_pin" ou "autenticado"
        self.admin_states = {}

        # armazena última busca para "links"
        self._last_products = []
        self._last_query    = ""

        logger.info("Zafira Core inicializada (modo clássico).")

    def process_message(self, sender_id: str, message: str):
        intent = self._detect_intent(message)
        logger.info(f"[PROCESS] {sender_id} → '{message}'  intent='{intent}'")

        # 1) iniciar modo admin mediante comando explícito
        if intent == "modo_admin":
            if sender_id in self.admin_ids:
                self.admin_states[sender_id] = "aguardando_pin"
                return self.whatsapp.send_text_message(
                    sender_id,
                    "🔐 Você entrou no modo ADM. Por favor, informe seu PIN:"
                )
            else:
                return self.whatsapp.send_text_message(
                    sender_id,
                    "❌ Você não está autorizado a entrar no modo ADM."
                )

        # 2) tratar resposta de PIN se estiver aguardando
        state = self.admin_states.get(sender_id)
        if state == "aguardando_pin":
            if message.strip() == self.admin_pin:
                self.admin_states[sender_id] = "autenticado"
                return self.whatsapp.send_text_message(
                    sender_id,
                    "✅ PIN correto. Você agora está autenticado como ADMIN."
                )
            else:
                return self.whatsapp.send_text_message(
                    sender_id,
                    "❌ PIN incorreto. Tente novamente:"
                )

        # 3) continuar fluxo normal (ou modo admin autenticado)
        #    comandos avançados podem checar self.admin_states[sender_id] == "autenticado"

        if intent == "saudacao":
            return self._handle_saudacao(sender_id)

        if intent == "links":
            return self._handle_links(sender_id)

        if intent == "produto":
            return self._handle_produto(sender_id, message)

        if intent == "conversa_geral":
            return self._handle_conversa(sender_id, message)

        if intent == "informacao_geral":
            return self._handle_informacao(sender_id, message)

        if intent == "piada":
            return self._handle_piada(sender_id)

        # intenção desconhecida
        return self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()
        if any(k in m for k in ["modo adm","modo admin","entrar no modo adm"]):
            return "modo_admin"
        if any(k in m for k in ["oi","olá","ola","e aí"]):
            return "saudacao"
        if any(k in m for k in ["link","links","url","urls"]):
            return "links"
        if any(k in m for k in ["quero","procuro","comprar","busco"]):
            return "produto"
        if any(k in m for k in ["conte-me","fale","como","tempo","como vai"]):
            return "conversa_geral"
        if any(k in m for k in ["o que é","defini","quem","quando","onde","por que"]):
            return "informacao_geral"
        if any(k in m for k in ["piada","brincadeira","trocadilho"]):
            return "piada"
        return "desconhecido"

    def _handle_saudacao(self, sender_id: str):
        text = (
            "Oi! 😊 Eu sou a Zafira.\n"
            "– Para compras: diga ‘Quero um fone bluetooth’\n"
            "– Para links: ‘Links dos produtos’\n"
            "– Para autenticar no modo ADM: ‘Vou entrar no modo ADM’\n"
            "– Pergunte qualquer outra coisa!"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_produto(self, sender_id: str, message: str):
        # extrai termos e limites de preço
        terms             = self._clean_terms(message)
        min_price, max_price = self._extract_price_limits(message)

        # busca bruta
        raw = (
            self.aliexpress.search_products(terms, limit=10, page_no=1)
                .get("aliexpress_affiliate_product_query_response", {})
                .get("resp_result", {})
                .get("result", {})
                .get("products", {})
                .get("product", [])
        ) or []

        # filtra por preço, se informado
        def price_val(p):
            return float(p.get("target_sale_price","0").replace(",","."))
        if min_price is not None:
            raw = [p for p in raw if price_val(p) >= min_price]
        if max_price is not None:
            raw = [p for p in raw if price_val(p) <= max_price]

        # guarda para links
        top3 = raw[:3]
        self._last_products = top3
        self._last_query    = terms

        # prepara resposta
        if not top3:
            text = f"⚠️ Não achei '{terms}' com esses critérios."
        else:
            lines = [f"Resultados para '{terms}':"]
            for p in top3:
                title = p.get("product_title","-")
                price = p.get("target_sale_price","-")
                lines.append(f"• {title} — R${price}")
            lines.append("🔗 Para os links completos, diga ‘Links dos produtos’.")
            text = "\n".join(lines)

        self.whatsapp.send_text_message(sender_id, text)

    def _handle_links(self, sender_id: str):
        if not self._last_products:
            return self.whatsapp.send_text_message(
                sender_id,
                "Nenhuma busca recente. Diga ‘Quero um fone bluetooth’ primeiro."
            )

        lines = [f"Links para '{self._last_query}':"]
        for p in self._last_products:
            url = p.get("promotion_link") or p.get("product_detail_url","-")
            lines.append(f"• {url}")
        self.whatsapp.send_text_message(sender_id, "\n".join(lines))

    def _handle_conversa(self, sender_id: str, message: str):
        self.whatsapp.send_text_message(
            sender_id,
            "😊 Vamos conversar! Sobre o que você quer falar?"
        )

    def _handle_informacao(self, sender_id: str, message: str):
        self.whatsapp.send_text_message(
            sender_id,
            "🤖 Informação Geral:\nAPI significa Application Programming Interface."
        )

    def _handle_piada(self, sender_id: str):
        self.whatsapp.send_text_message(
            sender_id,
            "🤣 Por que o programador confunde Halloween com Natal?\n"
            "Porque OCT 31 == DEC 25!"
        )

    def _handle_fallback(self, sender_id: str):
        text = (
            "Desculpe, não entendi. 🤔\n"
            "Você pode tentar:\n"
            "- ‘Quero um fone bluetooth’\n"
            "- ‘Celular até 3000 reais’\n"
            "- ‘Links dos produtos’\n"
            "- ‘Vou entrar no modo ADM’\n"
            "- ‘Me conte uma piada’"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _clean_terms(self, message: str) -> str:
        clean = re.sub(r"[^\w\s]","", message.lower())
        stop = {"quero","procuro","comprar","fone","celular","até","reais","busco"}
        return " ".join(w for w in clean.split() if w not in stop)

    def _extract_price_limits(self, msg: str) -> tuple[float|None, float|None]:
        # de X a Y reais
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:a|até|-)\s*(\d+(?:[.,]\d+)?)", msg)
        if m:
            lo = float(m.group(1).replace(",","."))
            hi = float(m.group(2).replace(",","."))
            return lo, hi
        # até Y reais
        m2 = re.search(r"até\s*(\d+(?:[.,]\d+)?)", msg)
        if m2:
            hi = float(m2.group(1).replace(",","."))
            return None, hi
        return None, None
