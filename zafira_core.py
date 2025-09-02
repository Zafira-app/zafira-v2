# zafira_core.py

import os
import re
import logging

from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient
from clients.groc_client import GROCClient

from agents.agente_conversa_geral import AgenteConversaGeral
from agents.agente_conhecimento import AgenteConhecimento
from agents.agente_humor import AgenteHumor

logger = logging.getLogger(__name__)


class ZafiraCore:
    def __init__(self):
        # Inicializa clientes
        self.whatsapp    = WhatsAppClient()
        self.aliexpress  = AliExpressClient()
        self.groc        = GROCClient()

        # Instancia agentes especializados
        self.ag_conv         = AgenteConversaGeral()
        self.ag_conhecimento = AgenteConhecimento()
        self.ag_humor        = AgenteHumor()

        # Configuração de administrador
        self.admin_ids    = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin    = os.getenv("ADMIN_PIN", "").strip()
        self.admin_states = {}   # { sender_id: "aguardando_pin"|"autenticado" }

        # Armazena resultados da última busca para 'links'
        self._last_products = []
        self._last_query    = ""

        logger.info("Zafira Core inicializada com enxame de agentes.")

    def process_message(self, sender_id: str, message: str):
        intent = self._detect_intent(message)
        logger.info(f"[PROCESS] {sender_id} → '{message}'  intent='{intent}'")

        # 1) Small talk
        if intent == "conversa_geral":
            resposta = self.ag_conv.responder(message)
            if resposta:
                return self.whatsapp.send_text_message(sender_id, resposta)

        # 2) Entrar no modo ADM
        if intent == "modo_admin":
            if sender_id in self.admin_ids:
                self.admin_states[sender_id] = "aguardando_pin"
                return self.whatsapp.send_text_message(
                    sender_id,
                    "🔐 Você entrou no modo ADM. Informe seu PIN:"
                )
            else:
                return self.whatsapp.send_text_message(
                    sender_id,
                    "❌ Você não tem permissão para o modo ADM."
                )

        # 3) Verificar PIN
        if self.admin_states.get(sender_id) == "aguardando_pin":
            if message.strip() == self.admin_pin:
                self.admin_states[sender_id] = "autenticado"
                return self.whatsapp.send_text_message(
                    sender_id,
                    "✅ Autenticado como ADMIN."
                )
            else:
                return self.whatsapp.send_text_message(
                    sender_id,
                    "❌ PIN incorreto. Tente novamente:"
                )

        # 4) Conhecimento geral
        if intent == "informacao_geral":
            resposta = self.ag_conhecimento.responder(message)
            if resposta:
                return self.whatsapp.send_text_message(sender_id, resposta)
            # não achou → cair no fallback

        # 5) Busca de produto
        if intent == "produto":
            return self._handle_produto(sender_id, message)

        # 6) Links de produtos
        if intent == "links":
            return self._handle_links(sender_id)

        # 7) Humor / Piadas
        if intent == "piada":
            joke = self.ag_humor.responder(message)
            return self.whatsapp.send_text_message(sender_id, joke)

        # 8) Saudação
        if intent == "saudacao":
            return self._handle_saudacao(sender_id)

        # 9) Fallback
        return self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()
        if any(k in m for k in ["modo adm","entrar no modo adm"]):
            return "modo_admin"
        if any(k in m for k in ["o que é","defini","quem","quando","onde","por que"]):
            return "informacao_geral"
        if any(k in m for k in ["quero","procuro","comprar","busco"]):
            return "produto"
        if any(k in m for k in ["link","links","url","urls"]):
            return "links"
        if any(k in m for k in ["piada","trocadilho","brincadeira"]):
            return "piada"
        if any(k in m for k in ["oi","olá","ola","e aí","bom dia","boa tarde","boa noite","como vai","tudo bem"]):
            return "saudacao"
        return "conversa_geral"

    def _handle_saudacao(self, sender_id: str):
        linhas = [
            "Oi! 😊 Eu sou a Zafira.",
            "– Para buscar produtos: ‘Quero um fone bluetooth’",
            "– Para links dos produtos: ‘Links dos produtos’",
            "– Para perguntas gerais: ‘O que é API?’",
            "– Para piadas: ‘Conte uma piada’"
        ]
        if sender_id in self.admin_ids:
            linhas.append("– Para modo ADM: ‘Vou entrar no modo ADM’")
        texto = "\n".join(linhas)
        self.whatsapp.send_text_message(sender_id, texto)

    def _handle_produto(self, sender_id: str, message: str):
        # Analisa termos e preço
        termos, min_p, max_p = self._extract_terms_and_prices(message)

        # Busca na API AliExpress
        raw = (
            self.aliexpress
                .search_products(termos, limit=10, page_no=1)
                .get("aliexpress_affiliate_product_query_response", {})
                .get("resp_result", {})
                .get("result", {})
                .get("products", {})
                .get("product", [])
        ) or []

        # Filtra por preço
        def price_val(p): return float(p.get("target_sale_price","0").replace(",","."))
        if min_p is not None:
            raw = [p for p in raw if price_val(p) >= min_p]
        if max_p is not None:
            raw = [p for p in raw if price_val(p) <= max_p]

        # Guarda top3 para links
        top3 = raw[:3]
        self._last_products = top3
        self._last_query    = termos

        if not top3:
            texto = f"⚠️ Não encontrei '{termos}' com esses critérios."
        else:
            linhas = [f"Resultados para '{termos}':"]
            for p in top3:
                title = p.get("product_title","-")
                price = p.get("target_sale_price","-")
                linhas.append(f"• {title} — R${price}")
            linhas.append("🔗 Para ver links completos, diga ‘Links dos produtos’.")
            texto = "\n".join(linhas)

        self.whatsapp.send_text_message(sender_id, texto)

    def _handle_links(self, sender_id: str):
        if not self._last_products:
            return self.whatsapp.send_text_message(
                sender_id,
                "Nenhuma busca recente. Diga ‘Quero um fone bluetooth’ primeiro."
            )
        linhas = [f"Links para '{self._last_query}':"]
        for p in self._last_products:
            url = p.get("promotion_link") or p.get("product_detail_url","-")
            linhas.append(f"• {url}")
        self.whatsapp.send_text_message(sender_id, "\n".join(linhas))

    def _handle_fallback(self, sender_id: str):
        texto = (
            "Desculpe, não entendi. 🤔\n"
            "Tente:\n"
            "- ‘Quero um fone bluetooth’\n"
            "- ‘Links dos produtos’\n"
            "- ‘O que é API?’\n"
            "- ‘Conte uma piada’"
        )
        self.whatsapp.send_text_message(sender_id, texto)

    def _extract_terms_and_prices(self, msg: str):
        clean = re.sub(r"[^\w\s]","", msg.lower())
        stop  = {"quero","procuro","comprar","fone","celular","busco","até","reais"}
        termos = " ".join(w for w in clean.split() if w not in stop)

        min_p, max_p = None, None
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:até|-)\s*(\d+(?:[.,]\d+)?)", msg)
        if m:
            min_p = float(m.group(1).replace(",","."))
            max_p = float(m.group(2).replace(",","."))
        else:
            m2 = re.search(r"até\s*(\d+(?:[.,]\d+)?)", msg)
            if m2:
                max_p = float(m2.group(1).replace(",","."))
        return termos, min_p, max_p
