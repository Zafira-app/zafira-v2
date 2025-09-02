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
        # Inicializa clientes
        self.whatsapp   = WhatsAppClient()
        self.aliexpress = AliExpressClient()
        self.groc       = GROCClient()

        # Configuração de administrador
        # ADMIN_IDS deve ser uma lista CSV de números WA sem “+” (ex: "5511983816938,5511999999999")
        self.admin_ids    = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin    = os.getenv("ADMIN_PIN", "")
        self.admin_states = {}   # { sender_id: "aguardando_pin" | "autenticado" }

        # Estado de última busca para intent “links”
        self._last_products = []
        self._last_query    = ""

        logger.info("Zafira Core inicializada (modo clássico).")

    def process_message(self, sender_id: str, message: str):
        # 1) Se for administrador e ainda não autenticado, exige PIN
        if sender_id in self.admin_ids:
            state = self.admin_states.get(sender_id)
            # Se já pediu PIN e aguarda resposta
            if state == "aguardando_pin":
                if message.strip() == self.admin_pin:
                    self.admin_states[sender_id] = "autenticado"
                    return self.whatsapp.send_text_message(
                        sender_id,
                        "✅ Autenticado como administrador. Em que posso ajudar?"
                    )
                else:
                    return self.whatsapp.send_text_message(
                        sender_id,
                        "❌ PIN incorreto. Tente novamente."
                    )
            # Primeiro contato do admin: pede PIN
            if state != "autenticado":
                self.admin_states[sender_id] = "aguardando_pin"
                return self.whatsapp.send_text_message(
                    sender_id,
                    "🔐 Por favor, informe seu PIN de administrador:"
                )
            # Se estava "autenticado", cai no fluxo normal abaixo

        # 2) Roteamento normal por intent
        intent = self._detect_intent(message)
        logger.info(f"[PROCESS] Mensagem de {sender_id}: '{message}' → intent: {intent}")

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

        # Fallback genérico
        return self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()
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
        if any(k in m for k in ["piada","brincadeira","machado"]):
            return "piada"
        return "desconhecido"

    def _handle_saudacao(self, sender_id: str):
        text = (
            "Oi! 😊 Eu sou a Zafira.\n"
            "- Para compras: diga ‘Quero um fone bluetooth’\n"
            "- Para ver links: ‘Links dos produtos’\n"
            "- Para conversar: pergunte qualquer coisa!"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_produto(self, sender_id: str, message: str):
        # Extrai termos e orçamento
        terms       = self._clean_terms(message)
        min_price, max_price = self._extract_price_limits(message)
        logger.info(f"[PRODUTO] termos='{terms}', min={min_price}, max={max_price}")

        # Busca na API
        raw = (
            self.aliexpress.search_products(terms, limit=10, page_no=1)
                .get("aliexpress_affiliate_product_query_response", {})
                .get("resp_result", {})
                .get("result", {})
                .get("products", {})
                .get("product", [])
        ) or []

        # Filtra por preço
        def price_val(p):
            v = p.get("target_sale_price","0").replace(",",".")
            try: return float(v)
            except: return 0.0
        if min_price is not None:
            raw = [p for p in raw if price_val(p) >= min_price]
        if max_price is not None:
            raw = [p for p in raw if price_val(p) <= max_price]

        # Guarda para “links”
        top3 = raw[:3]
        self._last_products = top3
        self._last_query    = terms

        # Formata resposta
        if not top3:
            text = f"⚠️ Não achei '{terms}' dentro dos critérios."
        else:
            lines = [f"Encontrei esses resultados para '{terms}':"]
            for p in top3:
                title = p.get("product_title","-")
                price = p.get("target_sale_price","-")
                lines.append(f"• {title} — R${price}")
            lines.append("🔗 Para ver os links completos, diga ‘Links dos produtos’.")
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
        # Exemplo simples de diálogo aberto
        self.whatsapp.send_text_message(
            sender_id,
            "😊 Vamos conversar! Sobre o que você quer falar?"
        )

    def _handle_informacao(self, sender_id: str, message: str):
        # Exemplo estático; idealmente usar um gerador de conhecimento
        self.whatsapp.send_text_message(
            sender_id,
            "🤖 Informação Geral:\n" 
            "API significa Application Programming Interface."
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
            "- Perguntas gerais ou ‘Me conte uma piada’"
        )
        self.whatsapp.send_text_message(sender_id, text)

    def _clean_terms(self, message: str) -> str:
        clean = re.sub(r"[^\w\s]","", message.lower())
        stop = {"quero","procuro","comprar","celular","fone","até","reais","busco"}
        return " ".join(w for w in clean.split() if w not in stop)

    def _extract_price_limits(self, msg: str) -> tuple[float|None, float|None]:
        # De X a Y reais
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:a|até|-)\s*(\d+(?:[.,]\d+)?)", msg)
        if m:
            lo = float(m.group(1).replace(",","."))
            hi = float(m.group(2).replace(",","."))
            return lo, hi
        # Até Y reais
        m2 = re.search(r"até\s*(\d+(?:[.,]\d+)?)", msg)
        if m2:
            hi = float(m2.group(1).replace(",","."))
            return None, hi
        return None, None
