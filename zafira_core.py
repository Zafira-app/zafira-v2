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

        # Sessões
        self.sessions = SessionManager(max_len=50)

        # Admin
        self.admin_ids      = os.getenv("ADMIN_IDS", "").split(",")
        self.admin_pin      = os.getenv("ADMIN_PIN", "").strip()
        self.admin_sessions = {}  # "aguardando_pin" ou datetime de expiração

        # Guarda busca para /links
        self._last_products = []
        self._last_query    = ""

        logger.info("ZafiraCore pronta com media support e ADM temporário.")

    def process_message(self, sender_id: str, message: str):
        now = datetime.utcnow()
        # 1) histórico
        self.sessions.push(sender_id, message)

        # 2) PIN pendente?
        if self.admin_sessions.get(sender_id) == "aguardando_pin":
            return self._handle_admin_pin(sender_id, message)

        # 3) Chat livre ADM?
        exp = self.admin_sessions.get(sender_id)
        if isinstance(exp, datetime) and now <= exp:
            # renova 30m
            self.admin_sessions[sender_id] = now + timedelta(minutes=30)
            history = self.sessions.get(sender_id)
            reply   = self.ag_adm_groq.responder(history, message)
            return self.whatsapp.send_text_message(sender_id, reply)

        # 4) intenção normal
        intent = self._detect_intent(message)

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

    def _handle_produto(self, sid: str, message: str):
        # extração de termos e faixa de preço
        clean = re.sub(r"[^\w\s]", "", message.lower())
        stop  = {"quero","procuro","comprar","busco","até","reais"}
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

        # busca bruta no AliExpress
        resp = self.aliexpress.search_products(termos, limit=10, page_no=1)
        raw = (
            resp
            .get("aliexpress_affiliate_product_query_response", {})
            .get("resp_result", {})
            .get("result", {})
            .get("products", {})
            .get("product", [])
        ) or []

        # filtra faixa de preço
        def price_val(p): return float(p.get("target_sale_price","0").replace(",","."))
        if min_p is not None:
            raw = [p for p in raw if price_val(p) >= min_p]
        if max_p is not None:
            raw = [p for p in raw if price_val(p) <= max_p]

        # ordena e pega top3
        raw.sort(key=price_val)
        top3 = raw[:3]
        self._last_products = top3
        self._last_query    = termos

        if not top3:
            return self.whatsapp.send_text_message(sid, f"⚠️ Não encontrei '{termos}'.")

        # envia media+legenda pra cada produto
        for p in top3:
            title = p.get("product_title","Produto")
            price = p.get("target_sale_price","-")
            link  = p.get("promotion_link") or p.get("product_detail_url","")
            # algumas APIs retornam imagem em campos diferentes:
            img   = (
                p.get("product_main_image_url")
                or p.get("image_url")
                or p.get("product_image_thumbnail_url")
            )
            caption = f"{title}\nR${price}\n{link}"
            # envia a imagem + legenda
            self.whatsapp.send_media_message(sid, img, caption)

        # footer de links adicionais
        return self.whatsapp.send_text_message(
            sid,
            "🔗 Caso queira ver todos os links juntos, diga ‘Links dos produtos’."
        )

    def _handle_links(self, sid: str):
        if not self._last_products:
            return self.whatsapp.send_text_message(
                sid,
                "Nenhuma busca recente. Diga ‘Quero um fone bluetooth’ primeiro."
            )
        # envia uma mensagem de texto com os links
        lines = [f"Links para '{self._last_query}':"]
        for p in self._last_products:
            url = p.get("promotion_link") or p.get("product_detail_url","-")
            lines.append(f"• {url}")
        return self.whatsapp.send_text_message(sid, "\n".join(lines))

    # ... demais handlers (_handle_saudacao, _handle_modo_admin, etc.) ...
