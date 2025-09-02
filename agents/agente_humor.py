# agents/agente_humor.py

import random

class AgenteHumor:
    """
    Agrega piadas e retorna uma aleatória para o usuário.
    """
    def __init__(self):
        self.piadas = [
            "🤣 Por que o programador confunde Halloween com Natal?\nPorque OCT 31 == DEC 25!",
            "😂 Qual é o cúmulo da programação?\nFazer um for infinito e ainda retornar.",
            "😜 O que um bit disse ao outro?\n— Somos pares!",
            "😉 Por que o Java foi ao médico?\nPorque estava com NullPointerException!"
        ]

    def responder(self, texto: str) -> str:
        return random.choice(self.piadas)
