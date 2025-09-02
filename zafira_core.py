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
from agents.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ZafiraCore:
    def __init__(self):
        # Clientes de infraestrutura
        self.whatsapp   = WhatsAppClient()
        self.aliexpress = AliExpressClient()
        self.groc       = GROCClient()

        # Agentes especializados
        self.ag_conv         = AgenteConversaGeral()
        self.ag_conhecimento = AgenteConhecimento()
        self.ag_humor        = AgenteHumor()

        # Histórico de sessão (por usuário)
        self.sessions = SessionManager(max_len=50)

        # Configuração de Administradores
        # ADMIN_IDS = "5511983816938,55XXXXXXXXXXX"
        self.admin_ids    = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin    = os.getenv("ADMIN_PIN", "").strip()
        self.admin_states = {}   # { sender_id: "aguardando_pin" | "autenticado" }

        # Para o fluxo de links
        self._last_products = []
        self._last_query    = ""

        logger.info("ZafiraCore iniciada com agentes e sessão.")

    def process_message(self, sender_id: str, message: str):
        # 1) Guarda histórico
        self.sessions.push(sender_id, message)
        logger.debug(f"Session[{sender_id}]: {self.sessions.get(sender_id)}")

        # 2) Detecta intenção
        intent = self._detect_intent(message)
        logger.info(f"[INTENT] {sender_id} → '{message}' => {intent}")

        # 3) Fluxos prioritários

        # Saudação personalizada
        if intent == "saudacao":
            return self._handle_saudacao(sender_id)

        # Entro no modo ADM (comando explícito)
        if intent == "modo_admin":
            return self._handle_modo_admin(sender_id)

        # Resposta ao PIN (se admin pediu)
        if self.admin_states.get(sender_id) == "aguardando_pin":
            return self._handle_admin_pin(sender_id, message)

        # Relatórios (somente admin autenticado)
        if intent == "relatorio":
            return self._handle_relatorio(sender_id)

        # Small talk genérico
        if intent == "conversa_geral":
            resp = self.ag_conv.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)

        # Conhecimento geral
        if intent == "informacao_geral":
            resp = self.ag_conhecimento.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)

        # Compra de produto
        if intent == "produto":
            return self._handle_produto(sender_id, message)

        # Links de produto
        if intent == "links":
            return self._handle_links(sender_id)

        # Piadas / humor
        if intent == "piada":
            joke = self.ag_humor.responder(message)
            return self.whatsapp.send_text_message(sender_id, joke)

        # Fallback final
        return self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()

        # 1) Saudações
        greetings = ["oi", "olá", "ola", "oiee", "e aí", "e ai", "eae", "tudo bem", "tudo bom"]
        if any(g in m for g in greetings):
            return "saudacao"

        # 2) Comando de modo admin
        if "modo adm" in m or "modo admin" in m or "vou entrar no modo adm" in m:
            return "modo_admin"

        # 3) Comando de relatório (admin)
        reports = ["relatorio", "planilha", "interacao", "interações", "pesquisa", "pesquisas"]
        if any(r in m for r in reports):
            return "relatorio"

        # 4) Informações gerais
        info = ["o que é", "defini", "quem", "quando", "onde", "por que"]
        if any(i in m for i in info):
            return "informacao_geral"

        # 5) Busca de produto
        buy = ["quero", "procuro", "comprar", "busco"]
        if any(b in m for b in buy):
            return "produto"

        # 6) Links
        if any(k in m for k in ["link", "links", "url"]):
            return "links"

        # 7) Piada
        if any(p in m for p in ["piada", "trocadilho", "brincadeira"]):
            return "piada"

        # 8) Qualquer outra → conversa geral
        return "conversa_geral"

    def _handle_saudacao(self, sender_id: str):
        if sender_id in self.admin_ids:
            texto = "E aí chefe, tudo bem? O que manda hoje?"
        else:
            texto = (
                "Oi! Que alegria te ver por aqui 😊\n"
                "Se quiser buscar algo, posso te ajudar a encontrar os melhores produtos.\n"
                "Por onde começamos: fones bluetooth, smartphones ou outra coisa?"
            )
        return self.whatsapp.send_text_message(sender_id, texto)

    def _handle_modo_admin(self, sender_id: str):
        if sender_id not in self.admin_ids:
            return self.whatsapp.send_text_message(
                sender_id,
                "❌ Desculpe, você não está autorizado ao modo ADM."
            )
        self.admin_states[sender_id] = "aguardando_pin"
        return self.whatsapp.send_text_message(
            sender_id,
            "🔐 Você entrou no modo ADM. Por favor, informe seu PIN de acesso:"
        )

    def _handle_admin_pin(self, sender_id: str, message: str):
        if message.strip() == self.admin_pin:
            self.admin_states[sender_id] = "autenticado"
            return self.whatsapp.send_text_message(
                sender_id,
                "✅ PIN correto. Acesso ADM liberado. Em que posso ajudar?"
            )
        return self.whatsapp.send_text_message(
            sender_id,
            "❌ PIN incorreto. Por favor, tente novamente:"
        )

    def _handle_relatorio(self, sender_id: str):
        if self.admin_states.get(sender_id) != "autenticado":
            return self.whatsapp.send_text_message(
                sender_id,
                "❌ Você precisa estar autenticado no modo ADM para ver relatórios."
            )
        # Placeholder de relatório – personalize como quiser
        texto = (
            "📋 Relatório resumido:\n"
            f"- Usuários ativos hoje: {len(self.sessions.sessions)}\n"
            f"- Última busca de '{sender_id}': '{self._last_query}'\n"
            f"- Produtos entregues na última busca: {len(self._last_products)}\n"
            "Para exportar em planilha, implemente aqui a integração desejada."
        )
        return self.whatsapp.send_text_message(sender_id, texto)

    def _handle_produto(self, sender_id: str, message: str):
        # Extrai termos e preço
        clean = re.sub(r"[^\w\s]", "", message.lower())
        stop = {"quero","procuro","comprar","fone","celular","busco","até","reais"}
        termos = " ".join(w for w in clean.split() if w not in stop)

        min_p, max_p = None, None
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:até|-)\s*(\d+(?:[.,]\d+)?)", message)
        if m:
            min_p = float(m.group(1).replace(",","."))
            max_p = float(m.group(2).replace(",","."))
        else:
            m2 = re.search(r"até\s*(\d+(?:[.,]\d+)?)", message)
            if m2:
                max_p = float(m2.group(1).replace(",","."))

        # Chama API AliExpress
        resp = self.aliexpress.search_products(termos, limit=10, page_no=1)
        raw = (
            resp
            .get("aliexpress_affiliate_product_query_response", {})
            .get("resp_result", {})
            .get("result", {})
            .get("products", {})
            .get("product", [])
        ) or []

        # Filtra preço
        def price_val(p): return float(p.get("target_sale_price","0").replace(",","."))
        if min_p is not None:
            raw = [p for p in raw if price_val(p) >= min_p]
        if max_p is not None:
            raw = [p for p in raw if price_val(p) <= max_p]

        top3 = raw[:3]
        self._last_products = top3
        self._last_query    = termos

        if not top3:
            texto = f"⚠️ Não encontrei '{termos}' com esses critérios."
        else:
            lines = [f"Encontrei estes resultados para '{termos}':"]
            for p in top3:
                title = p.get("product_title","-")
                price = p.get("target_sale_price","-")
                lines.append(f"• {title} — R${price}")
            lines.append("🔗 Para ver os links completos, diga ‘Links dos produtos’.")
            texto = "\n".join(lines)

        return self.whatsapp.send_text_message(sender_id, texto)

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
        return self.whatsapp.send_text_message(sender_id, "\n".join(lines))

    def _handle_fallback(self, sender_id: str):
        return self.whatsapp.send_text_message(
            sender_id,
            "Desculpe, não entendi. 🤔\n"
            "Pergunte algo como:\n"
            "- ‘Quero um fone bluetooth’\n"
            "- ‘Links dos produtos’\n"
            "- ‘Me conte uma piada’"
        )
