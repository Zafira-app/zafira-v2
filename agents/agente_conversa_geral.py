# agents/agente_conversa_geral.py

import re

class AgenteConversaGeral:
    """
    Reconhece e responde small talk via expressões regulares.
    """
    def __init__(self):
        self.padroes = [
            (r"\b(oi|olá|ola|e aí)\b",
             "Oi! 😊 Em que posso ajudar hoje?"),
            (r"\b(bom dia|boa tarde|boa noite)\b",
             lambda m: f"{m.group(1).capitalize()}! Como você está?"),
            (r"\b(como vai|tudo bem|tudo bom)\b",
             "Estou bem, obrigado! E você?"),
            (r"\b(qual seu nome|quem é você)\b",
             "Eu sou a Zafira, sua assistente de compras e conversa!"),
            (r"\b(o que você faz|para que você serve)\b",
             "Posso ajudar a buscar produtos, responder perguntas e bater papo!"),
            (r"\b(clima|tempo)\b",
             "Por aqui está um dia agradável ☀️. Quer ver produtos ou saber algo mais?"),
        ]

    def responder(self, texto: str) -> str | None:
        for padrao, resposta in self.padroes:
            m = re.search(padrao, texto, re.IGNORECASE)
            if m:
                return resposta(m) if callable(resposta) else resposta
        return None
