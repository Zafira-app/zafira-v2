# zafira_core.py

import os
import re
import logging
from datetime import datetime, timedelta

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

        # Agentes
        self.ag_conv     = AgenteConversaGeral()
        self.ag_conh     = AgenteConhecimento()
        self.ag_humor    = AgenteHumor()
        self.ag_adm_groq = AgenteConversaADMGroq()

        # Histórico de mensagens
        self.sessions = SessionManager(max_len=50)

        # Configuração de administradores
        self.admin_ids      = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin      = os.getenv("ADMIN_PIN", "").strip()
        # Valor: "aguardando_pin" ou datetime de expiração
        self.admin_sessions = {}

        # Armazena último resultado de busca
        self._last_products = []
        self._last_query    = ""

        logger.info("ZafiraCore iniciada com sessões e autenticação ADM temporária.")

    def process_message(self, sender_id: str, message: str):
        now = datetime.utcnow()

        # 1) Guarda histórico
        self.sessions.push(sender_id, message)
        logger.debug(f"Session[{sender_id}]: {self.sessions.get(sender_id)}")

        # 2) Se estiver aguardando PIN, trate antes de tudo
        if self.admin_sessions.get(sender_id) == "aguardando_pin":
            return self._handle_admin_pin(sender_id, message)

        # 3) Se já autenticado e dentro do prazo, chat livre ADM
        exp = self.admin_sessions.get(sender_id)
        if isinstance(exp, datetime) and now <= exp:
            # Estende mais 30min a cada nova mensagem
            self.admin_sessions[sender_id] = now + timedelta(minutes=30)
            history = self.sessions.get(sender_id)
            reply = self.ag_adm_groq.responder(history, message)
            return self.whatsapp.send_text_message(sender_id, reply)

        # 4) Detecta intenção
        intent = self._detect_intent(message)
        logger.info(f"[INTENT] {sender_id} → '{message}' => {intent}")

        # 5) Saudação
        if intent == "saudacao":
            return self._handle_saudacao(sender_id)

        # 6) Entrar no modo ADM
        if intent == "modo_admin":
            return self._handle_modo_admin(sender_id)

        # 7) Relatórios (exige autenticação)
        if intent == "relatorio":
            return self._handle_relatorio(sender_id, message)

        # 8) Small talk geral
        if intent == "conversa_geral":
            resp = self.ag_conv.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)

        # 9) Conhecimento geral
        if intent == "informacao_geral":
            resp = self.ag_conh.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)

        # 10) Busca de produto
        if intent == "produto":
            return self._handle_produto(sender_id, message)

        # 11) Links de produto
        if intent == "links":
            return self._handle_links(sender_id)

        # 12) Humor / piada
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

    def _handle_saudacao(self, sid: str):
        if sid in self.admin_ids:
            texto = "E aí chefe, tudo bem? O que manda hoje?"
        else:
            texto = (
                "Oi! Que alegria te ver por aqui 😊\n"
                "Posso te ajudar a encontrar os melhores produtos.\n"
                "Por onde começamos hoje?"
            )
        return self.whatsapp.send_text_message(sid, texto)

    def _handle_modo_admin(self, sid: str):
        if sid not in self.admin_ids:
            return self.whatsapp.send_text_message(sid, "❌ Você não está autorizado ao modo ADM.")
        self.admin_sessions[sid] = "aguardando_pin"
        return self.whatsapp.send_text_message(sid, "🔐 Modo ADM ativado. Informe seu PIN:")

    def _handle_admin_pin(self, sid: str, message: str):
        if message.strip() == self.admin_pin:
            self.admin_sessions[sid] = datetime.utcnow() + timedelta(minutes=30)
            return self.whatsapp.send_text_message(sid, "✅ PIN correto. Acesso ADM liberado por 30 min.")
        # se incorreto, continua aguardando PIN
        self.admin_sessions[sid] = "aguardando_pin"
        return self.whatsapp.send_text_message(sid, "❌ PIN incorreto. Tente novamente:")

    def _handle_relatorio(self, sid: str, message: str):
        exp = self.admin_sessions.get(sid)
        if not (isinstance(exp, datetime) and datetime.utcnow() <= exp):
            return self.whatsapp.send_text_message(sid, "❌ Autentique-se no modo ADM para ver relatórios.")
        parts = message.lower().strip().split(maxsplit=1)
        if len(parts) == 2:
            tipo = parts[1]
            if tipo in ("interacoes","pesquisas"):
                buscas = []
                for hist in self.sessions.sessions.values():
                    buscas += [
                        m for m in hist
                        if m.lower().split()[0] in ("quero","procuro","comprar","busco")
                    ]
                texto = "📊 Relatório de pesquisas:\n" + "\n".join(f"- {b}" for b in buscas) \
                        or "Nenhuma pesquisa registrada."
                return self.whatsapp.send_text_message(sid, texto)
            if tipo == "usuarios":
                total = len(self.sessions.sessions)
                texto = f"👥 Total de usuários distintos: {total}"
                return self.whatsapp.send_text_message(sid, texto)
            return self.whatsapp.send_text_message(
                sid,
                f"❓ Tipo '{tipo}' não reconhecido.\n"
                "Use 'Relatório interacoes' ou 'Relatório usuarios'."
            )
        total = len(self.sessions.sessions)
        last_q = self._last_query or "nenhuma"
        last_n = len(self._last_products)
        texto = (
            "📋 Relatório geral:\n"
            f"- Usuários únicos hoje: {total}\n"
            f"- Última busca: '{last_q}' ({last_n} itens)\n"
            "Para detalhes: 'Relatório interacoes' ou 'Relatório usuarios'."
        )
        return self.whatsapp.send_text_message(sid, texto)

    def _handle_produto(self, sid: str, message: str):
        # 1) Extrai termos e faixa de preço
        clean = re.sub(r"[^\w\s]", "", message.lower())
        stop  = {"quero","procuro","comprar","fone","celular","busco","até","reais"}
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

        # 2) Busca bruta na API do AliExpress
        resp = self.aliexpress.search_products(termos, limit=10, page_no=1)
        raw = (
            resp
            .get("aliexpress_affiliate_product_query_response", {})
            .get("resp_result", {})
            .get("result", {})
            .get("products", {})
            .get("product", [])
        ) or []

        # 3) Filtra pela faixa de preço, se houver
        def price_val(p):
            return float(p.get("target_sale_price","0").replace(",","."))
        if min_p is not None:
            raw = [p for p in raw if price_val(p) >= min_p]
        if max_p is not None:
            raw = [p for p in raw if price_val(p) <= max_p]

        # 4) Ordena e seleciona top 3
        raw.sort(key=price_val)
        top3 = raw[:3]
        self._last_products = top3
        self._last_query    = termos

        # 5) Formata a resposta
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

        return self.whatsapp.send_text_message(sid, text)

    def _handle_links(self, sid: str):
        if not self._last_products:
            return self.whatsapp.send_text_message(
                sid,
                "Nenhuma busca recente. Diga ‘Quero um fone bluetooth’ primeiro."
            )
        lines = [f"Links para '{self._last_query}':"]
        for p in self._last_products:
            url = p.get("promotion_link") or p.get("product_detail_url","-")
            lines.append(f"• {url}")
        return self.whatsapp.send_text_message(sid, "\n".join(lines))

    def _handle_fallback(self, sid: str):
        texto = (
            "Desculpe, não entendi. 🤔\n"
            "Você pode tentar:\n"
            "- ‘Quero um fone bluetooth’\n"
            "- ‘Links dos produtos’\n"
            "- ‘Me conte uma piada’"
        )
        return self.whatsapp.send_text_message(sid, texto)
