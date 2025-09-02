# tests/test_agents.py

import re
import pytest

from agents.agente_conversa_geral import AgenteConversaGeral
from agents.agente_conhecimento import AgenteConhecimento
from agents.agente_humor import AgenteHumor
from agents.session_manager import SessionManager

# -----------------------------------------------------------------------------
# Testes para AgenteConversaGeral
# -----------------------------------------------------------------------------

@pytest.fixture
def agente_conv():
    return AgenteConversaGeral()

@pytest.mark.parametrize("entrada,esperado", [
    ("Oi", "Oi! 😊 Em que posso ajudar hoje?"),
    ("olá Zafira", "Oi! 😊 Em que posso ajudar hoje?"),
    ("Bom dia", "Bom dia! Como você está?"),
    ("boa tarde tudo bem?", "Boa tarde! Como você está?"),
    ("Como vai você?", "Estou bem, obrigado! E você?"),
    ("Qual seu nome?", "Eu sou a Zafira, sua assistente de compras e conversa!"),
    ("O que você faz?", "Posso ajudar a buscar produtos, responder perguntas e bater papo!"),
    ("Como está o clima?", "Por aqui está um dia agradável ☀️. Quer ver produtos ou saber algo mais?")
])
def test_conversa_geral(agente_conv, entrada, esperado):
    resp = agente_conv.responder(entrada)
    assert resp == esperado

def test_conversa_geral_sem_padrao(agente_conv):
    assert agente_conv.responder("Essa não é small talk") is None

# -----------------------------------------------------------------------------
# Testes para AgenteConhecimento
# -----------------------------------------------------------------------------

@pytest.fixture
def agente_conh():
    return AgenteConhecimento()

@pytest.mark.parametrize("pergunta,esperado", [
    ("Qual a capital da França?", "Paris"),
    ("capital do brasil", "Brasília"),
    ("Quem descobriu o Brasil?", "Pedro Álvares Cabral"),
    ("O que é API?", (
        "API significa Application Programming Interface. "
        "É um conjunto de rotinas e padrões de programação que permitem "
        "a comunicação entre diferentes sistemas de software."
    )),
    ("Quem foi Albert Einstein?", (
        "Albert Einstein foi um físico teórico nascido na Alemanha, "
        "conhecido pela teoria da relatividade."
    )),
])
def test_conhecimento(pergunta, esperado):
    agente = AgenteConhecimento()
    resp = agente.responder(pergunta)
    assert resp == esperado

def test_conhecimento_desconhecido():
    agente = AgenteConhecimento()
    assert agente.responder("Qual é a cor do céu?") is None

# -----------------------------------------------------------------------------
# Testes para AgenteHumor
# -----------------------------------------------------------------------------

def test_humor_variability():
    agente = AgenteHumor()
    piadas = set(agente.piadas)
    # Deve retornar uma piada do conjunto
    for _ in range(10):
        resp = agente.responder("Conte uma piada")
        assert resp in piadas

# -----------------------------------------------------------------------------
# Testes para SessionManager
# -----------------------------------------------------------------------------

def test_session_manager_push_and_get():
    sm = SessionManager(max_len=3)
    sid = "user123"
    assert sm.get(sid) == []

    sm.push(sid, "m1")
    sm.push(sid, "m2")
    assert sm.get(sid) == ["m1","m2"]

    sm.push(sid, "m3")
    sm.push(sid, "m4")
    # max_len = 3, deve descartar a mais antiga
    assert sm.get(sid) == ["m2","m3","m4"]

# -----------------------------------------------------------------------------
# Teste integração ZafiraCore (fluxo de sessão)
# -----------------------------------------------------------------------------

from zafira_core import ZafiraCore

class DummyWhatsAppClient:
    def __init__(self):
        self.sent = []

    def send_text_message(self, to, text):
        self.sent.append((to, text))

# Mock de AliExpressClient
class DummyAE:
    def search_products(self, terms, limit, page_no):
        return {
            "aliexpress_affiliate_product_query_response": {
                "resp_result": {
                    "result": {
                        "products": {
                            "product": [
                                {"product_title": "Prod1", "target_sale_price": "10.00", "promotion_link": "url1"},
                                {"product_title": "Prod2", "target_sale_price": "20.00", "promotion_link": "url2"},
                                {"product_title": "Prod3", "target_sale_price": "30.00", "promotion_link": "url3"},
                                {"product_title": "Prod4", "target_sale_price": "40.00", "promotion_link": "url4"},
                            ]
                        }
                    }
                }
            }
        }

def test_zafira_core_basic_flow(monkeypatch):
    z = ZafiraCore()
    # Injeta clientes dummy
    z.whatsapp = DummyWhatsAppClient()
    z.aliexpress = DummyAE()
    z.groc = DummyAE()  # não usado aqui

    # Saudação
    z.process_message("userA", "Oi Zafira")
    assert ("userA", "Oi! 😊 Eu sou a Zafira.") in z.whatsapp.sent[0]

    # Busca de produto
    z.process_message("userA", "Quero um produto")
    # Deve ter enviado top3 e sugestão de links
    sent = z.whatsapp.sent[-1][1]
    assert "Prod1" in sent and "Prod2" in sent and "Prod3" in sent

    # Links
    z.process_message("userA", "Links dos produtos")
    sent = z.whatsapp.sent[-1][1]
    assert "url1" in sent and "url2" in sent and "url3" in sent

    # Piada
    z.process_message("userA", "Conte uma piada")
    assert len(z.whatsapp.sent[-1][1]) > 0

    # Conhecimento
    z.process_message("userA", "Qual a capital da França?")
    assert "Paris" in z.whatsapp.sent[-1][1]
