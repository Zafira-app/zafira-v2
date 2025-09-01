# app.py - VERSÃO 2.0 - ZAFIRA COM CÉREBRO (GROQ INTEGRADO)

import os
import json
import logging
import re
import time
import hashlib
import random
import requests
from urllib.parse import urlencode

from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ==============================================================================
# CARREGA VARIÁVEIS DE AMBIENTE E CONFIGURA LOG
# ==============================================================================
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==============================================================================
# BRAIN AGENT (O CÉREBRO DA ZAFIRA - POWERED BY GROQ)
# ==============================================================================
class BrainAgent:
    def __init__(self):
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.api_key = os.getenv("GROQ_API_KEY" )
        self.model = "llama3-8b-8192"
        if not self.api_key:
            logger.error("GROQ_API_KEY não configurada! O cérebro não pode funcionar.")
        else:
            logger.info("BrainAgent inicializado com o modelo %s.", self.model)

    def analyze(self, user_message: str) -> dict:
        if not self.api_key:
            return {"intent": "error", "empathetic_reply": "Desculpe, estou com um problema na minha conexão cerebral. Tente novamente mais tarde."}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        system_prompt = """
        Você é o cérebro da Zafira, uma assistente de compras do WhatsApp. Sua função é analisar a mensagem do usuário e retornar um JSON estruturado.

        Siga estas regras estritamente:
        1.  **Analise a intenção (intent)**:
            - "saudacao": Se for apenas um oi, bom dia, olá, tudo bem, etc.
            - "busca_produto": Se o usuário expressar qualquer desejo de encontrar, procurar, ver ou comprar um produto.
            - "conversa_geral": Para qualquer outra coisa que não seja uma busca (agradecimentos, perguntas sobre você, etc).
        2.  **Extraia os termos de busca (search_terms)**: O produto principal que o usuário quer. Seja conciso.
        3.  **Extraia os filtros (filters)**: Detalhes como preço máximo/mínimo, cor, marca, etc. Retorne como um objeto. Se não houver filtros, retorne um objeto vazio {}.
        4.  **Crie uma resposta empática (empathetic_reply)**: Uma frase curta, amigável e natural em português para iniciar a conversa, confirmando que você entendeu o pedido.

        **Exemplos:**
        - User: "Oi, tudo bem?" -> {"intent": "saudacao", "search_terms": null, "filters": {}, "empathetic_reply": "Olá! Tudo bem por aqui. 😊 Como posso te ajudar a encontrar algo hoje?"}
        - User: "tô pensando em dar um fone de ouvido gamer bom, mas não posso gastar mais de 300 reais" -> {"intent": "busca_produto", "search_terms": "fone de ouvido gamer", "filters": {"max_price": 300}, "empathetic_reply": "Ótima ideia de presente! 🎮 Vou procurar alguns fones de ouvido gamer excelentes até R$300 para você."}
        - User: "obrigado zafira" -> {"intent": "conversa_geral", "search_terms": null, "filters": {}, "empathetic_reply": "De nada! Se precisar de mais alguma coisa, é só chamar! 😉"}

        O JSON de saída DEVE ter sempre as 4 chaves: "intent", "search_terms", "filters", "empathetic_reply".
        """

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.5,
            "response_format": {"type": "json_object"}
        }

        try:
            logger.info("Enviando para análise do BrainAgent: '%s'", user_message)
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=25)
            response.raise_for_status()
            analysis_str = response.json()["choices"][0]["message"]["content"]
            logger.info("Análise recebida do BrainAgent: %s", analysis_str)
            return json.loads(analysis_str)
        except requests.RequestException as e:
            logger.error("Erro na API da Groq: %s", e)
            return {"intent": "error", "empathetic_reply": "Desculpe, meu cérebro está um pouco lento agora. Poderia repetir, por favor?"}
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Erro ao processar resposta da Groq: %s", e)
            return {"intent": "error", "empathetic_reply": "Tive uma ideia brilhante, mas me perdi no pensamento. Pode me dizer de novo?"}


# ==============================================================================
# CLIENTE WHATSAPP (Sem alterações)
# ==============================================================================
class WhatsAppClient:
    def __init__(self):
        self.api_url         = "https://graph.facebook.com/v20.0/"
        self.token           = os.getenv("WHATSAPP_TOKEN", "" )
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        if not (self.token and self.phone_number_id):
            logger.error("Credenciais do WhatsApp não configuradas!")
        else:
            logger.info("Cliente WhatsApp inicializado.")

    def send_text_message(self, recipient_id: str, message: str) -> bool:
        url = f"{self.api_url}{self.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": recipient_id, "type": "text", "text": {"body": message, "preview_url": False}}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
  
