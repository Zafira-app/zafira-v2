# app.py - VERSÃO 2.0.1 - CORREÇÃO DE SINTAXE

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
            logger.info(f"Mensagem enviada para {recipient_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Falha ao enviar WhatsApp: {e}")
            return False

# ==============================================================================
# CLIENTE ALIEXPRESS (Sem alterações)
# ==============================================================================
class AliExpressClient:
    def __init__(self):
        self.api_url     = os.getenv("AE_API_URL", "https://api-sg.aliexpress.com/sync" )
        self.app_key     = os.getenv("ALIEXPRESS_APP_KEY", "")
        self.app_secret  = os.getenv("ALIEXPRESS_APP_SECRET", "")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID", "")
        if not (self.app_key and self.app_secret and self.tracking_id):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress inicializado.")

    def _generate_signature(self, params: dict) -> str:
        sorted_items = sorted(params.items())
        concat  = "".join(f"{k}{v}" for k, v in sorted_items)
        raw     = f"{self.app_secret}{concat}{self.app_secret}".encode("utf-8")
        return hashlib.md5(raw).hexdigest().upper()

    def search_products(self, keywords: str, limit: int = 3) -> dict:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        page_no   = random.randint(1, 5)

        params = {
            "app_key":          self.app_key,
            "method":           "aliexpress.affiliate.product.query",
            "sign_method":      "md5",
            "timestamp":        timestamp,
            "keywords":         keywords,
            "tracking_id":      self.tracking_id,
            "page_size":        str(limit),
            "page_no":          str(page_no),
            "target_language":  "pt",
            "target_currency":  "BRL",
            "ship_to_country":  "BR"
        }
        params["sign"] = self._generate_signature(params)
        
        logger.info("AliExpress QUERY PARAMS: %s", params)

        try:
            resp = requests.get(self.api_url, params=params, timeout=40)
            logger.info("AliExpress STATUS: %s", resp.status_code)
            logger.info("AliExpress BODY: %s", resp.text[:500])
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Erro na API AliExpress: {e}")
            return {"error": str(e)}

# ==============================================================================
# NÚCLEO DA ZAFIRA (Atualizado para usar o BrainAgent)
# ==============================================================================
class ZafiraCore:
    def __init__(self):
        self.brain      = BrainAgent()
        self.whatsapp   = WhatsAppClient()
        self.aliexpress = AliExpressClient()
        logger.info("Zafira Core inicializada com BrainAgent.")

    def process_message(self, sender_id: str, message: str):
        logger.info(f"Recebido de {sender_id}: {message}")
        
        analysis = self.brain.analyze(message)
        intent = analysis.get("intent")
        reply_text = analysis.get("empathetic_reply", "Desculpe, não entendi. Pode repetir?")

        if intent == "busca_produto":
            search_terms = analysis.get("search_terms")
            if not search_terms:
                self.whatsapp.send_text_message(sender_id, "Entendi que você quer buscar algo, mas não ficou claro o quê. Pode me dizer o produto?")
                return

            # Envia a resposta empática primeiro, para o usuário saber que foi entendido.
            self.whatsapp.send_text_message(sender_id, reply_text)
            
            # Agora, busca os produtos
            logger.info("Iniciando busca de produto com termos: '%s'", search_terms)
            ali_data  = self.aliexpress.search_products(search_terms, limit=3)
            product_reply = self._format_product_response(ali_data, search_terms)
            self.whatsapp.send_text_message(sender_id, product_reply)

        else: # Para "saudacao", "conversa_geral" ou "error"
            self.whatsapp.send_text_message(sender_id, reply_text)

    def _format_product_response(self, data: dict, query: str) -> str:
        if "error_response" in data or "error" in data:
            logger.error("Erro recebido da API AliExpress: %s", data)
            return "😔 Tive um problema para buscar os produtos no AliExpress. A loja pode estar instável. Por favor, tente novamente mais tarde."
        
        products = (data.get("aliexpress_affiliate_product_query_response", {})
                        .get("resp_result", {})
                        .get("result", {})
                        .get("products", {})
                        .get("product", []))
        
        if not products:
            return f"⚠️ Não encontrei resultados para '{query}'. Que tal tentar um termo diferente?"

        lines = [f"Aqui estão os melhores resultados para '{query}' que encontrei! 🚀"]
        for p in products[:3]:
            title = p.get("product_title", "-")
            price = p.get("target_sale_price", "Preço indisponível")
            link  = p.get("promotion_link") or p.get("product_detail_url", "")
            if len(title) > 70: title = title[:67] + "..."
            lines.append(f"🛒 *{title}*\n💰 Preço: {price}\n🔗 Link: {link}")
        
        return "\n\n".join(lines)

# ==============================================================================
# FLASK & ROTAS (COM A CORREÇÃO DE SINTAXE)
# ==============================================================================
app = Flask(__name__)
zafira = ZafiraCore()
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if (request.args.get("hub.mode") == "subscribe" and
            request.args.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN):
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    payload = request.get_json(force=True)
    logger.info("Webhook recebido: %s", json.dumps(payload, indent=2, ensure_ascii=False))
    try:
        change = payload["entry"][0]["changes"][0]
        if change["field"] == "messages":
            msg    = change["value"]["messages"][0]
            sender = msg["from"]
            text   = msg["text"]["body"]
            zafira.process_message(sender, text)
    except (KeyError, IndexError, TypeError) as e:
        logger.info("Ignorado: webhook sem texto de mensagem de usuário ou formato inesperado. Erro: %s", e)
    
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
