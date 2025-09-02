# zafira_core.py

import os
import re
import logging

from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Agentes do enxame
# ----------------------------------------------------------------------------

class AgenteOrquestrador:
    """
    Recebe toda mensagem e decide a qual agente especializar
    encaminhar o fluxo.
    """
    def decidir(self, texto: str) -> str:
        m = texto.lower()
        if any(k in m for k in ["oi","olá","ola","e aí"]):
            return "saudacao"
        if any(k in m for k in ["vou entrar no modo adm","modo adm"]):
            return "modo_admin"
        if any(k in m for k in ["link","links","url"]):
            return "links"
        if any(k in m for k in ["quero","busco","procuro","comprar"]):
            return "produto"
        if any(k in m for k in ["o que é","defini","quem","quando","onde","por que"]):
            return "informacao_geral"
        if any(k in m for k in ["piada","trocadilho","brincadeira"]):
            return "piada"
        return "conversa_geral"


class AgenteInterpretacao:
    """
    Analisa o texto de busca, extrai termos e limites de preço.
    """
    def extrair(self, texto: str) -> dict:
        # Limpeza básica
        termos = re.sub(r"[^\w\s]","", texto.lower())
        termos = " ".join(w for w in termos.split()
                          if w not in {"quero","procuro","comprar","busco","até","reais"})
        # Orçamento
        min_p, max_p = None, None
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:até|-)\s*(\d+(?:[.,]\d+)?)", texto)
        if m:
            min_p = float(m.group(1).replace(",","."))
            max_p = float(m.group(2).replace(",","."))
        else:
            m2 = re.search(r"até\s*(\d+(?:[.,]\d+)?)", texto)
            if m2:
                max_p = float(m2.group(1).replace(",","."))
        return {"termos": termos, "min_price": min_p, "max_price": max_p}


class AgenteCacaProdutos:
    """
    Executa a busca na API do AliExpress.
    """
    def __init__(self):
        self.client = AliExpressClient()

    def buscar(self, termos: str) -> list[dict]:
        data = self.client.search_products(termos, limit=10, page_no=1)
        return (
            data
            .get("aliexpress_affiliate_product_query_response", {})
            .get("resp_result", {})
            .get("result", {})
            .get("products", {})
            .get("product", [])
        ) or []


class AgenteGarimpeiro:
    """
    (Opcional) Enriquecimento de itens via web scraping.
    Aqui passamos direto os dados brutos adiante.
    """
    def enriquecer(self, produtos: list[dict]) -> list[dict]:
        return produtos


class AgenteEditor:
    """
    Filtra, ordena e seleciona os top 3 produtos,
    gerando o texto final de resposta.
    """
    def curar(self, produtos: list[dict], min_p: float|None, max_p: float|None) -> list[dict]:
        def preco(p):
            return float(p.get("target_sale_price","0").replace(",","."))
        if min_p is not None:
            produtos = [p for p in produtos if preco(p) >= min_p]
        if max_p is not None:
            produtos = [p for p in produtos if preco(p) <= max_p]
        produtos.sort(key=preco)
        return produtos[:3]

    def formatar(self, produtos: list[dict], termos: str) -> str:
        if not produtos:
            return f"⚠️ Não achei '{termos}' com esses critérios."
        lines = [f"Encontrei estes resultados para '{termos}':"]
        for p in produtos:
            title = p.get("product_title","-")
            price = p.get("target_sale_price","-")
            lines.append(f"• {title} — R${price}")
        lines.append("🔗 Para ver os links, diga ‘Links dos produtos’.")
        return "\n".join(lines)


class AgenteMensageiro:
    """
    Envia mensagens via WhatsApp.
    """
    def __init__(self):
        self.client = WhatsAppClient()

    def enviar(self, destinatario: str, texto: str):
        self.client.send_text_message(destinatario, texto)


# ----------------------------------------------------------------------------
# ZafiraCore: orquestra os agentes
# ----------------------------------------------------------------------------

class ZafiraCore:
    def __init__(self):
        # instância dos agentes
        self.orquestrador = AgenteOrquestrador()
        self.interpretador = AgenteInterpretacao()
        self.cacador      = AgenteCacaProdutos()
        self.garimpeiro   = AgenteGarimpeiro()
        self.editor       = AgenteEditor()
        self.messenger    = AgenteMensageiro()

        # configuração de admin
        self.admin_ids    = os.getenv("ADMIN_IDS","").split(",")
        self.admin_pin    = os.getenv("ADMIN_PIN","").strip()
        self.admin_states = {}  # { sender_id: "aguardando_pin"|"autenticado" }

        # último resultado de busca
        self._ultimos_produtos = []
        self._ultima_busca     = ""

        logger.info("Zafira Core inicializada com enxame de agentes.")

    def process_message(self, sender_id: str, message: str):
        intent = self.orquestrador.decidir(message)
        logger.info(f"[PROCESS] {sender_id} → '{message}'  intent='{intent}'")

        # Modo administrador
        if intent == "modo_admin":
            return self._modo_admin(sender_id)

        # Resposta ao PIN
        if self.admin_states.get(sender_id) == "aguardando_pin":
            return self._check_pin(sender_id, message)

        # Fluxo normal autenticado ou usuário comum
        if intent == "saudacao":
            return self._saudacao(sender_id)

        if intent == "produto":
            return self._fluxo_compra(sender_id, message)

        if intent == "links":
            return self._fluxo_links(sender_id)

        if intent == "informacao_geral":
            return self._info_geral(sender_id)

        if intent == "piada":
            return self._conta_piada(sender_id)

        # fallback e conversa geral
        return self._fallback(sender_id)

    def _modo_admin(self, sid: str):
        if sid not in self.admin_ids:
            return self.messenger.enviar(sid, "❌ Você não está autorizado ao modo ADM.")
        self.admin_states[sid] = "aguardando_pin"
        return self.messenger.enviar(sid, "🔐 Entre com seu PIN de administrador:")

    def _check_pin(self, sid: str, msg: str):
        if msg.strip() == self.admin_pin:
            self.admin_states[sid] = "autenticado"
            return self.messenger.enviar(sid, "✅ Autenticado como ADMIN.")
        return self.messenger.enviar(sid, "❌ PIN inválido. Tente novamente:")

    def _saudacao(self, sid: str):
        base = [
            "Oi! 😊 Eu sou a Zafira.",
            "– Para compras: diga ‘Quero um fone bluetooth’",
            "– Para links: ‘Links dos produtos’"
        ]
        if sid in self.admin_ids:
            base.append("– Para ADM: ‘Vou entrar no modo ADM’")
        self.messenger.enviar(sid, "\n".join(base))

    def _fluxo_compra(self, sid: str, msg: str):
        ctx = self.interpretador.extrair(msg)
        brutos = self.cacador.buscar(ctx["termos"])
        enric = self.garimpeiro.enriquecer(brutos)
        top3 = self.editor.curar(enric, ctx["min_price"], ctx["max_price"])

        # guarda para links
        self._ultimos_produtos = top3
        self._ultima_busca     = ctx["termos"]

        texto = self.editor.formatar(top3, ctx["termos"])
        return self.messenger.enviar(sid, texto)

    def _fluxo_links(self, sid: str):
        if not self._ultimos_produtos:
            return self.messenger.enviar(
                sid,
                "Nenhuma busca foi feita. Diga ‘Quero um fone bluetooth’."
            )
        lines = [f"Links para '{self._ultima_busca}':"]
        for p in self._ultimos_produtos:
            url = p.get("promotion_link") or p.get("product_detail_url","-")
            lines.append(f"• {url}")
        return self.messenger.enviar(sid, "\n".join(lines))

    def _info_geral(self, sid: str):
        return self.messenger.enviar(
            sid,
            "🤖 Informação geral:\nAPI significa Application Programming Interface."
        )

    def _conta_piada(self, sid: str):
        return self.messenger.enviar(
            sid,
            "🤣 Por que o programador confunde Halloween com Natal?\n"
            "Porque OCT 31 == DEC 25!"
        )

    def _fallback(self, sid: str):
        return self.messenger.enviar(
            sid,
            "Desculpe, não entendi. 🤔\n"
            "Você pode tentar:\n"
            "- ‘Quero um fone bluetooth’\n"
            "- ‘Links dos produtos’\n"
            "- ‘Vou entrar no modo ADM’\n"
            "- ‘Me conte uma piada’"
        )
