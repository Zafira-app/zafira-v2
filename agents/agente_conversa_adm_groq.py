# agents/agente_conversa_adm_groq.py

import os
import requests

class AgenteConversaADMGroq:
    """
    Usa a Groq Chat Completions (compatível OpenAI) para conversa livre no modo ADM.
    """
    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        # O typo no seu .env é GROP_APP_KEY; ajustamos aqui:
        self.token = os.getenv("GROP_APP_KEY")  

    def responder(self, history: list[str], message: str) -> str:
        # Monta o corpo da requisição no formato OpenAI
        messages = [{"role": "system", "content": "Você é a Zafira, assistente inteligente."}]
        # Adiciona histórico de mensagens (contexto)
        for h in history:
            messages.append({"role": "user", "content": h})
        # Adiciona a última mensagem do Admin
        messages.append({"role": "user", "content": message})

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "max_tokens": 150,
            "temperature": 0.7
        }

        resp = requests.post(self.API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
