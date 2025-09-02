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
        # Infraestrutura
        self.whatsapp   = WhatsAppClient()
        self.aliexpress = AliExpressClient()
        self.groc       = GROCClient()

        # Agentes especializados
        self.ag_conv        = AgenteConversaGeral()
        self.ag_conhecimento = AgenteConhecimento()
        self.ag_humor       = AgenteHumor()

        # Sessões por usuário
        self.sessions = SessionManager(max_len=50)

        # Configuração de administradores
        # Defina no .env: ADMIN_IDS="5511983816938,55XXXXXXXXXXX"
        self.admin_ids    = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin    = os.getenv("ADMIN_PIN", "").strip()
        self.admin_states = {}   # { sender_id: "aguardando_pin" | "autenticado" }

        # Para fluxo de “links”
        self._last_products = []
        self._last_query    = ""

        logger.info("ZafiraCore inicializada com agentes e sessão.")

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

        # 4) Modo ADM
        if intent == "modo_admin":
            return self._handle_modo_admin(sender_id)

        # 5) Verificação de PIN
        if self.admin_states.get(sender_id) == "aguardando_pin":
            return self._handle_admin_pin(sender_id, message)

        # 6) Relatórios (genérico ou específico)
        if intent == "relatorio":
            return self._handle_relatorio(sender_id, message)

        # 7) Conversa geral (small talk)
        if intent == "conversa_geral":
            resp = self.ag_conv.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)

        # 8) Conhecimento geral
        if intent == "informacao_geral":
            resp = self.ag_conhecimento.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)

        # 9) Fluxo de compras
        if intent == "produto":
            return self._handle_produto(sender_id, message)

        # 10) Links de produtos
        if intent == "links":
            return self._handle_links(sender_id)

        # 11) Humor / piada
        if intent == "piada":
            joke = self.ag_humor.responder(message)
            return self.whatsapp.send_text_message(sender_id, joke)

        # 12) Fallback
        return self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()

        # Saudação
        greetings = ["oi", "olá", "ola", "oiee", "e aí", "e ai", "eae", "tudo bem", "tudo bom"]
        if any(g in m for g in greetings):
            return "saudacao"

        # Modo admin
        if "modo adm" in m or "modo admin" in m or "vou entrar no modo adm" in m:
            return "modo_admin"

        # Relatórios
        reports = ["relatorio", "planilha", "interacao", "interações", "pesquisa", "pesquisas"]
        if any(r in m for r in reports):
            return "relatorio"

        # Informações gerais
        info = ["o que é", "defini", "quem", "quando", "onde", "por que"]
        if any(i in m for i in info):
            return "informacao_geral"

        # Busca de produto
        buy = ["quero", "procuro", "comprar", "busco"]
        if any(b in m for b in buy):
            return "produto"

        # Links
        if any(k in m for k in ["link", "links", "url"]):
            return "links"

        # Piada
        if any(p in m for p in ["piada", "trocadilho", "brincadeira"]):
            return "piada"

        # Padrão
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
                sender_id,
                "❌ Você não tem permissão para o modo ADM."
            )
        self.admin_states[sender_id] = "aguardando_pin"
        return self.whatsapp.send_text_message(
            sender_id,
            "🔐 Modo ADM ativado. Informe seu PIN de acesso:"
        )

    def _handle_admin_pin(self, sender_id: str, message: str):
        if message.strip() == self.admin_pin:
            self.admin_states[sender_id] = "autenticado"
            return self.whatsapp.send_text_message(
                sender_id,
                "✅ PIN correto. Acesso ADM liberado."
            )
        return self.whatsapp.send_text_message(
            sender_id,
            "❌ PIN incorreto. Tente novamente:"
        )

    def _handle_relatorio(self, sender_id: str, message: str):
        """
        Se a mensagem for apenas 'Relatório', retorna um resumo geral.
        Se vier 'Relatório <tipo>', tenta gerar relatório específico.
        Tipos suportados: interacoes/pesquisas, usuarios.
        """
        if self.admin_states.get(sender_id) != "autenticado":
            return self.whatsapp.send_text_message(
                sender_id,
                "❌ Autentique-se no modo ADM para ver relatórios."
            )

        parts = message.lower().strip().split(maxsplit=1)

        # Relatório específico
        if len(parts) == 2:
            tipo = parts[1]
            # Interações/pesquisas
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

            # Usuários
            if tipo == "usuarios":
                total = len(self.sessions.sessions)
                texto = f"👥 Total de usuários distintos hoje: {total}"
                return self.whatsapp.send_text_message(sender_id, texto)

            # Tipo desconhecido
            return self.whatsapp.send_text_message(
                sender_id,
                f"❓ Tipo '{tipo}' não reconhecido.\n"
                "Use:\n"
                "- Relatório interacoes\n"
                "- Relatório usuarios"
            )

        # Relatório geral
        total_users = len(self.sessions.sessions)
        last_q = self._last_query or "nenhuma"
        last_n = len(self._last_products)
        texto = (
            "📋 Relatório geral:\n"
            f"- Usuários únicos hoje: {total_users}\n"
            f"- Última busca: '{last_q}' ({last_n} itens)\n"
            "Para detalhes: 'Relatório interacoes' ou 'Relatório usuarios'."
        )
        return self.whatsapp.send_text_message(sender_id, texto)

    def _handle_produto(self, sender_id: str, message: str):
        # ...
        # (mesmo código de busca, filtro e formatação que você já tem)
        pass

    def _handle_links(self, sender_id: str):
        # ...
        pass

    def _handle_fallback(self, sender_id: str):
        texto = (
            "Desculpe, não entendi. 🤔\n"
            "Tente:\n"
            "- ‘Quero um fone bluetooth’\n"
            "- ‘Links dos produtos’\n"
            "- ‘Me conte uma piada’"
        )
        return self.whatsapp.send_text_message(sender_id, texto)
