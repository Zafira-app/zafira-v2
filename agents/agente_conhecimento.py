# agents/agente_conhecimento.py

import re

class AgenteConhecimento:
    """
    Responde perguntas gerais mapeadas em um pequeno banco de dados interno.
    """
    def __init__(self):
        # Base de conhecimento simples (você pode expandir conforme desejar)
        self.knowledge = {
            "capital da frança": "Paris",
            "capital do brasil": "Brasília",
            "quem descobriu o brasil": "Pedro Álvares Cabral",
            "o que é api": (
                "API significa Application Programming Interface. "
                "É um conjunto de rotinas e padrões de programação que permitem "
                "a comunicação entre diferentes sistemas de software."
            ),
            "qual a moeda dos estados unidos": "Dólar americano (USD)",
            "quem foi albert einstein": (
                "Albert Einstein foi um físico teórico nascido na Alemanha, "
                "conhecido pela teoria da relatividade."
            ),
        }

    def responder(self, texto: str) -> str | None:
        """
        Tenta encontrar a pergunta no banco interno. Se não encontrar,
        retorna None para cair no fallback.
        """
        t = texto.lower().strip().rstrip("?")
        # Normaliza espaços
        t = re.sub(r"\s+", " ", t)

        # Verifica correspondência exata
        if t in self.knowledge:
            return self.knowledge[t]

        # Você pode incluir buscas parciais:
        for key, answer in self.knowledge.items():
            if key in t:
                return answer

        return None
