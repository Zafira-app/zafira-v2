# zafira_core.py

import os
import re
import logging
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient
from clients.mercado_livre_client import MercadoLivreClient
from clients.groc_client import GROCClient

from agents.agente_conversa_geral import AgenteConversaGeral
from agents.agente_conhecimento import AgenteConhecimento
from agents.agente_humor import AgenteHumor
from agents.agente_conversa_adm_groq import AgenteConversaADMGroq
from agents.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ZafiraCore:
    def __init__(self):
        self.whatsapp    = WhatsAppClient()
        self.aliexpress  = AliExpressClient()
        self.mercado     = MercadoLivreClient()
        self.groc        = GROCClient()

        self.ag_conv     = AgenteConversaGeral()
        self.ag_conh     = AgenteConhecimento()
        self.ag_humor    = AgenteHumor()
        self.ag_adm_groq = AgenteConversaADMGroq()

        self.sessions        = SessionManager(max_len=50)
        self.admin_ids       = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin       = os.getenv("ADMIN_PIN", "").strip()
        self.admin_sessions  = {}

        self._last_products  = []
        self._last_query     = ""

        logger.info("ZafiraCore iniciada com listas interativas e ADM temporário.")

    def process_message(self, sender_id: str, message: str, interactive: dict = None):
        now = datetime.utcnow()
        self.sessions.push(sender_id, message)

        # 1) Seleção de lista interativa
        if interactive and interactive.get("type") == "list_reply":
            choice_id = interactive["list_reply"]["id"]
            return self._handle_product_selection(sender_id, choice_id)

        # 2) PIN pendente?
        if self.admin_sessions.get(sender_id) == "aguardando_pin":
            return self._handle_admin_pin(sender_id, message)

        # 3) Chat livre ADM
        exp = self.admin_sessions.get(sender_id)
        if isinstance(exp, datetime) and now <= exp:
            self.admin_sessions[sender_id] = now + timedelta(minutes=30)
            history = self.sessions.get(sender_id)
            reply   = self.ag_adm_groq.responder(history, message)
            return self.whatsapp.send_text_message(sender_id, reply)

        # 4) Intenção
        intent = self._detect_intent(message)
        logger.info(f"[INTENT] {sender_id} → '{message}' => {intent}")

        # 5) Roteamento
        if intent == "saudacao":
            return self._handle_saudacao(sender_id)
        if intent == "modo_admin":
            return self._handle_modo_admin(sender_id)
        if intent == "relatorio":
            return self._handle_relatorio(sender_id, message)
        if intent == "conversa_geral":
            resp = self.ag_conv.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)
        if intent == "informacao_geral":
            resp = self.ag_conh.responder(message)
            if resp:
                return self.whatsapp.send_text_message(sender_id, resp)
        if intent == "produto":
            return self._handle_produto(sender_id, message)
        if intent == "links":
            return self._handle_links(sender_id)
        if intent == "piada":
            joke = self.ag_humor.responder(message)
            return self.whatsapp.send_text_message(sender_id, joke)

        return self._handle_fallback(sender_id)

    def _detect_intent(self, msg: str) -> str:
        m = msg.lower()
        if any(g in m for g in ["oi","olá","ola","oiee","e aí","tudo bem"]):
            return "saudacao"
        if "modo adm" in m:
            return "modo_admin"
        if any(r in m for r in ["relatorio","pesquisa","planilha"]):
            return "relatorio"
        if any(i in m for i in ["o que é","quem","onde","por que"]):
            return "informacao_geral"
        if any(b in m for b in ["quero","procuro","comprar","busco"]):
            return "produto"
        if any(k in m for k in ["link","links","url"]):
            return "links"
        if any(p in m for p in ["piada","trocadilho"]):
            return "piada"
        return "conversa_geral"

    def _handle_saudacao(self, sid: str):
        if sid in self.admin_ids:
            text = "E aí chefe, tudo bem? O que manda hoje?"
        else:
            text = (
                "Oi! Que alegria te ver por aqui 😊\n"
                "Posso ajudar a encontrar os melhores produtos.\n"
                "Por onde começamos hoje?"
            )
        return self.whatsapp.send_text_message(sid, text)

    def _handle_modo_admin(self, sid: str):
        if sid not in self.admin_ids:
            return self.whatsapp.send_text_message(sid, "❌ Sem permissão ao modo ADM.")
        self.admin_sessions[sid] = "aguardando_pin"
        return self.whatsapp.send_text_message(sid, "🔐 Modo ADM ativado. Envie seu PIN:")

    def _handle_admin_pin(self, sid: str, msg: str):
        if msg.strip() == self.admin_pin:
            self.admin_sessions[sid] = datetime.utcnow() + timedelta(minutes=30)
            return self.whatsapp.send_text_message(sid, "✅ PIN correto! Acesso ADM por 30 min.")
        self.admin_sessions[sid] = "aguardando_pin"
        return self.whatsapp.send_text_message(sid, "❌ PIN incorreto. Tente novamente:")

    def _handle_relatorio(self, sid: str, msg: str):
        exp = self.admin_sessions.get(sid)
        if not (isinstance(exp, datetime) and datetime.utcnow() <= exp):
            return self.whatsapp.send_text_message(sid, "❌ Autentique-se no modo ADM.")
        total = len(self.sessions.sessions)
        return self.whatsapp.send_text_message(sid, f"👥 Usuários hoje: {total}")

    def _fix_image_url(self, url: str) -> str:
        if url.lower().endswith(".webp"):
            path = quote_plus(url.replace("https://", "").replace("http://", ""))
            return f"https://images.weserv.nl/?url={path}&output=jpeg"
        return url

    def _handle_produto(self, sid: str, message: str):
        # Extrai termos e preços
        clean = re.sub(r"[^\w\s]", "", message.lower())
        stop  = {"quero","procuro","comprar","busco","até","reais"}
        termos = " ".join(w for w in clean.split() if w not in stop)

        min_p = max_p = None
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:até|-)\s*(\d+(?:[.,]\d+)?)", message)
        if m:
            min_p = float(m.group(1).replace(",", "."))
            max_p = float(m.group(2).replace(",", "."))
        else:
            m2 = re.search(r"até\s*(\d+(?:[.,]\d+)?)", message)
            if m2:
                max_p = float(m2.group(1).replace(",", "."))

        # Busca em AliExpress e MercadoLivre
        ali = self.aliexpress.search_products(termos, limit=10, page_no=1)
        ml  = self.mercado.search_products(termos, limit=10)
        combined = ali + ml

        # Filtra por preço
        def price_val(p):
            return float(p.get("target_sale_price", "0").replace(",", "."))
        if min_p is not None:
            combined = [p for p in combined if price_val(p) >= min_p]
        if max_p is not None:
            combined = [p for p in combined if price_val(p) <= max_p]

        # Ordena e top-3
        combined.sort(key=price_val)
        top3 = combined[:3]
        self._last_products = top3
        self._last_query    = termos

        if not top3:
            return self.whatsapp.send_text_message(sid, f"⚠️ Não encontrei '{termos}'.")

        # Monta a lista interativa (cada título truncado em 24 chars)
        rows = []
        for idx, p in enumerate(top3, start=1):
            source    = p.get("source", "AliExpress")
            raw_title = f"{p['product_title']} — R${p['target_sale_price']} ({source})"
            title     = raw_title if len(raw_title) <= 24 else raw_title[:21] + "..."
            rows.append({
                "id": f"prod_{idx}",
                "title": title,
                "description": ""
            })
        sections = [{"title": termos[:24], "rows": rows}]

        return self.whatsapp.send_list_message(
            sid,
            header=f"Resultados p/ '{termos[:24]}'",
            body="Toque no item p/ ver detalhes.",
            footer="Zafira – assistente de compras",
            button="Ver opções",
            sections=sections
        )

    def _handle_product_selection(self, sid: str, choice_id: str):
        idx = int(choice_id.split("_")[1]) - 1
        if idx < 0 or idx >= len(self._last_products):
            return self.whatsapp.send_text_message(sid, "Opção inválida.")
        p = self._last_products[idx]
        title = p.get("product_title", "Produto")
        price = p.get("target_sale_price", "-")
        link  = p.get("promotion_link") or p.get("product_detail_url", "")
        img   = p.get("product_main_image_url") or p.get("image_url") or ""
        img   = self._fix_image_url(img)
        caption = f"{title}\nR${price}\n{link}"
        self.whatsapp.send_media_message(sid, img, caption)
        return None

    def _handle_links(self, sid: str):
        if not self._last_products:
            return self.whatsapp.send_text_message(sid, "Nenhuma busca recente.")
        lines = [f"Links para '{self._last_query}'"]
        for p in self._last_products:
            lines.append(p.get("promotion_link") or p.get("product_detail_url", "-"))
        return self.whatsapp.send_text_message(sid, "\n".join(lines))

    def _handle_fallback(self, sid: str):
        return self.whatsapp.send_text_message(
            sid,
            "Desculpe, não entendi. 🤔\n"
            "Tente:\n"
            "- 'Quero um fone bluetooth'\n"
            "- 'Links dos produtos'\n"
            "- 'Me conte uma piada'"
        )
