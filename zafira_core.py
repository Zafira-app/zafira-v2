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
from agents.agente_conversa_adm_groq import AgenteConversaADMGroq
from agents.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ZafiraCore:
    def __init__(self):
        # Clientes
        self.whatsapp   = WhatsAppClient()
        self.aliexpress = AliExpressClient()
        self.groc       = GROCClient()

        # Agentes especializados
        self.ag_conv         = AgenteConversaGeral()
        self.ag_conhecimento = AgenteConhecimento()
        self.ag_humor        = AgenteHumor()
        self.ag_adm_groq     = AgenteConversaADMGroq()

        # Histórico de sessão
        self.sessions = SessionManager(max_len=50)

        # Configuração de Administradores
        # ADMIN_IDS="5511988163988" no .env
        self.admin_ids    = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin    = os.getenv("ADMIN_PIN", "").strip()
        self.admin_states = {}   # { sender_id: "aguardando_pin" | "autenticado" }

        # Últimos produtos para 'links'
        self._last_products = []
        self._last_query    = ""

        logger.info("ZafiraCore iniciada com agentes, sessão e Groq-ADM.")

    def process_message(self, sender_id: str, message: str):
        # 1) Armazena na sessão
        self.sessions.push(sender_id, message)
        logger.debug(f"Session[{sender_id}]: {self.sessions.get(sender_id)}")

        # 2) Detecta intenção
        intent = self._detect_intent(message)
        logger.info(f"[INTENT] {sender_id} → '{message}' => {intent}")

        # 3) Saudação
        if intent == "saudacao":
            return self._handle_saudacao(sender_id)

        # 4) Entrar no modo ADM
        if intent == "modo_admin":
            return self._handle_modo_admin(sender_id)

        # 5) Resposta ao PIN
        if self.admin_states.get(sender_id) == "aguardando_pin":
            return self._handle_admin_pin(sender_id, message)

        # 6) Chat livre para Admin autenticado via Groq
        if sender_id in self.admin_ids and self.admin_states.get(sender_id) == "autenticado":
            history = self.sessions.get(sender_id)
            reply   = self.ag_adm_groq.responder(history, message)
            return self.whatsapp.send_text_message(sender_id, reply)

        # 7) Relatórios (genérico ou específico)
        if intent == "relatorio":
            return self._handle_relatorio(sender_id, message)

        # 8) Small talk comum
        if intent == "conversa_geral":
            resp = self.ag_conv.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)

        # 9) Conhecimento geral
        if intent == "informacao_geral":
            resp = self.ag_conhecimento.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)

        # 10) Fluxo de produto
        if intent == "produto":
            return self._handle_produto(sender_id, message)

        # 11) Links de produtos
        if intent == "links":
            return self._handle_links(sender_id)

        # 12) Piada / humor
        if intent == "piada":
            joke = self.ag_humor.responder(message)
            return self.whatsapp.send_text_message(sender_id, joke)

        # 13) Fallback
        return self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()
        if any(g in m for g in ["oi","olá","ola","oiee","e aí","e ai","eae","tudo bem","tudo bom"]):
            return "saudacao"
        if "modo adm" in m or "modo admin" in m or "vou entrar no modo adm" in m:
            return "modo_admin"
        if any(r in m for r in ["relatorio","planilha","interacao","interações","pesquisa","pesquisas"]):
            return "relatorio"
        if any(i in m for i in ["o que é","defini","quem","quando","onde","por que"]):
            return "informacao_geral"
        if any(b in m for b in ["quero","procuro","comprar","busco"]):
            return "produto"
        if any(k in m for k in ["link","links","url"]):
            return "links"
        if any(p in m for p in ["piada","trocadilho","brincadeira"]):
            return "piada"
        return "conversa_geral"

    def _handle_saudacao(self, sender_id: str):
        if sender_id in self.admin_ids:
            texto = "E aí chefe, tudo bem? O que manda hoje?"
        else:
            texto = (
                "Oi! Que alegria te ver por aqui 😊\n"
                "Se quiser buscar algo, posso te ajudar a encontrar os melhores produtos.\n"
                "Por onde começamos: fones bluetooth, smartphones ou algo diferente?"
            )
        return self.whatsapp.send_text_message(sender_id, texto)

    def _handle_modo_admin(self, sender_id: str):
        if sender_id not in self.admin_ids:
            return self.whatsapp.send_text_message(
                sender_id, "❌ Você não tem permissão para o modo ADM."
            )
        self.admin_states[sender_id] = "aguardando_pin"
        return self.whatsapp.send_text_message(
            sender_id, "🔐 Modo ADM ativado. Informe seu PIN de acesso:"
        )

    def _handle_admin_pin(self, sender_id: str, message: str):
        if message.strip() == self.admin_pin:
            self.admin_states[sender_id] = "autenticado"
            return self.whatsapp.send_text_message(
                sender_id, "✅ PIN correto. Acesso ADM liberado."
            )
        return self.whatsapp.send_text_message(
            sender_id, "❌ PIN incorreto. Tente novamente:"
        )

    def _handle_relatorio(self, sender_id: str, message: str):
        if self.admin_states.get(sender_id) != "autenticado":
            return self.whatsapp.send_text_message(
                sender_id, "❌ É necessário autenticar no modo ADM."
            )

        parts = message.lower().strip().split(maxsplit=1)
        # Relatório específico: "Relatório interacoes" ou "Relatório usuarios"
        if len(parts) == 2:
            tipo = parts[1]
            if tipo in ("interacoes", "pesquisas"):
                buscas = []
                for hist in self.sessions.sessions.values():
                    buscas += [
                        m for m in hist
                        if m.lower().split()[0] in ("quero", "procuro", "comprar", "busco")
                    ]
                texto = "📊 Relatório de pesquisas:\n"
                texto += "\n".join(f"- {b}" for b in buscas) or "Nenhuma pesquisa registrada."
                return self.whatsapp.send_text_message(sender_id, texto)
            if tipo == "usuarios":
                total = len(self.sessions.sessions)
                texto = f"👥 Total de usuários distintos hoje: {total}"
                return self.whatsapp.send_text_message(sender_id, texto)
            return self.whatsapp.send_text_message(
                sender_id,
                f"❓ Tipo '{tipo}' não reconhecido. Use:\n"
                "- Relatório interacoes\n"
                "- Relatório usuarios"
            )

        # Relatório geral
        total_users = len(self.sessions.sessions)
        last_q      = self._last_query or "nenhuma"
        last_n      = len(self._last_products)
        texto = (
            "📋 Relatório geral:\n"
            f"- Usuários únicos hoje: {total_users}\n"
            f"- Última busca: '{last_q}' ({last_n} itens)\n"
            "Para detalhes: 'Relatório interacoes' ou 'Relatório usuarios'."
        )
        return self.whatsapp.send_text_message(sender_id, texto)

    def _handle_produto(self, sender_id: str, message: str):
        # ... (seu código de busca, filtragem e formatação)
        pass

    def _handle_links(self, sender_id: str):
        # ... (seu código atual de links)
        pass

    def _handle_fallback(self, sender_id: str):
        return self.whatsapp.send_text_message(
            sender_id,
            "Desculpe, não entendi. 🤔\n"
            "Tente:\n"
            "- ‘Quero um fone bluetooth’\n"
            "- ‘Links dos produtos’\n"
            "- ‘Me conte uma piada’"
        )
