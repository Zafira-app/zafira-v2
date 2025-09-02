# zafira_core.py

import os
import re
import logging

from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient
from clients.groc_client import GROCClient

# Importa o Agente de Conversa Geral
from agents.agente_conversa_geral import AgenteConversaGeral

logger = logging.getLogger(__name__)


class ZafiraCore:
    def __init__(self):
        # Inicializa os clientes
        self.whatsapp   = WhatsAppClient()
        self.aliexpress = AliExpressClient()
        self.groc       = GROCClient()

        # Agente de small talk
        self.ag_conv = AgenteConversaGeral()

        # Configuração de administrador
        # ADMIN_IDS: CSV de números WhatsApp (sem "+"), ex: "5511983816938"
        self.admin_ids    = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin    = os.getenv("ADMIN_PIN", "").strip()
        self.admin_states = {}  # { sender_id: "aguardando_pin" | "autenticado" }

        # Armazena último resultado de busca para “links”
        self._last_products = []
        self._last_query    = ""

        logger.info("Zafira Core inicializada (modo clássico).")

    def process_message(self, sender_id: str, message: str):
        # Detecta intenção básica
        intent = self._detect_intent(message)
        logger.info(f"[PROCESS] {sender_id} → '{message}'  intent='{intent}'")

        # 1) Small talk: se for conversa geral, tenta responder e encerra
        if intent == "conversa_geral":
            resposta = self.ag_conv.responder(message)
            if resposta:
                return self.whatsapp.send_text_message(sender_id, resposta)

        # 2) Comando para entrar no modo ADM (somente para IDs configurados)
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

        # 3) Tratamento de PIN se estiver aguardando autenticação
        if self.admin_states.get(sender_id) == "aguardando_pin":
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

        # 4) Fluxos principais
        if intent == "saudacao":
            return self._handle_saudacao(sender_id)

        if intent == "produto":
            return self._handle_produto(sender_id, message)

        if intent == "links":
            return self._handle_links(sender_id)

        if intent == "informacao_geral":
            return self._handle_informacao(sender_id)

        if intent == "piada":
            return self._handle_piada(sender_id)

        # 5) Fallback: qualquer outra mensagem entra em small talk padrão
        return self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()
        if any(k in m for k in ["modo adm","entrar no modo adm"]):
            return "modo_admin"
        if any(k in m for k in ["oi","olá","ola","e aí"]):
            return "saudacao"
        if any(k in m for k in ["quero","procuro","comprar","busco"]):
            return "produto"
        if any(k in m for k in ["link","links","url","urls"]):
            return "links"
        if any(k in m for k in ["o que é","defini","quem","quando","onde","por que"]):
            return "informacao_geral"
        if any(k in m for k in ["piada","trocadilho","brincadeira"]):
            return "piada"
        return "conversa_geral"

    def _handle_saudacao(self, sender_id: str):
        lines = [
            "Oi! 😊 Eu sou a Zafira.",
            "– Para buscar produtos: ‘Quero um fone bluetooth’",
            "– Para ver links: ‘Links dos produtos’"
        ]
        if sender_id in self.admin_ids:
            lines.append("– Para modo ADM: ‘Vou entrar no modo ADM’")
        text = "\n".join(lines)
        self.whatsapp.send_text_message(sender_id, text)

    def _handle_produto(self, sender_id: str, message: str):
        # Extrai termos e possíveis limites de preço
        termos, min_price, max_price = self._extract_terms_and_prices(message)

        # Busca bruta na API AliExpress
        raw = (
            self.aliexpress
                .search_products(termos, limit=10, page_no=1)
                .get("aliexpress_affiliate_product_query_response", {})
                .get("resp_result", {})
                .get("result", {})
                .get("products", {})
                .get("product", [])
        ) or []

        # Filtra por preço, se necessário
        def price_val(p):
            return float(p.get("target_sale_price","0").replace(",","."))
        if min_price is not None:
            raw = [p for p in raw if price_val(p) >= min_price]
        if max_price is not None:
            raw = [p for p in raw if price_val(p) <= max_price]

        # Guarda top 3 para links
        top3 = raw[:3]
        self._last_products = top3
        self._last_query    = termos

        # Formata resposta curta
        if not top3:
            text = f"⚠️ Não encontrei '{termos}' com esses critérios."
        else:
            lines = [f"Encontrei estes resultados para '{termos}':"]
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

    def _handle_informacao(self, sender_id: str):
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
        self.whatsapp.send_text_message(
            sender_id,
            "Desculpe, não entendi. 🤔\n"
            "Você pode tentar:\n"
            "- ‘Quero um fone bluetooth’\n"
            "- ‘Links dos produtos’\n"
            "- ‘Vou entrar no modo ADM’\n"
            "- ‘Me conte uma piada’"
        )

    def _extract_terms_and_prices(self, msg: str):
        # Limpa termos de busca
        clean = re.sub(r"[^\w\s]","", msg.lower())
        stop = {"quero","procuro","comprar","fone","celular","busco","até","reais"}
        termos = " ".join(w for w in clean.split() if w not in stop)

        # Extrai limites de preço
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
