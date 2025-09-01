# app.py - VERSÃO 3.3 - USANDO O MODELO MIXTRAL ESTÁVEL

import os
import json
import logging
import time
import hashlib
import random
import requests
from urllib.parse import urlencode

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process
from crewai_tools import BaseTool
from langchain_groq import ChatGroq
from pydantic import BaseModel

# ==============================================================================
# CARREGA VARIÁVEIS DE AMBIENTE E CONFIGURA LOG
# ==============================================================================
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# ==============================================================================
# MODELO DE DADOS PARA A SAÍDA JSON
# ==============================================================================
class AnalysisModel(BaseModel):
    intent: str
    search_terms: str | None
    empathetic_reply: str

# ==============================================================================
# FERRAMENTA PERSONALIZADA PARA BUSCA NO ALIEXPRESS
# ==============================================================================
class AliExpressSearchTool(BaseTool):
    name: str = "Ferramenta de Busca de Produtos no AliExpress"
    description: str = "Use esta ferramenta para buscar produtos no AliExpress com base em palavras-chave. Ela retorna uma lista de produtos."

    def _run(self, keywords: str) -> str:
        logger.info(f"AliExpressSearchTool: Buscando por '{keywords}'")
        try:
            app_key = os.getenv("ALIEXPRESS_APP_KEY")
            app_secret = os.getenv("ALIEXPRESS_APP_SECRET")
            tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
            api_url = "https://api-sg.aliexpress.com/sync"

            if not all([app_key, app_secret, tracking_id] ):
                return "Erro: Credenciais do AliExpress não configuradas."

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            params = {
                "app_key": app_key, "method": "aliexpress.affiliate.product.query",
                "sign_method": "md5", "timestamp": timestamp, "keywords": keywords,
                "tracking_id": tracking_id, "page_size": "5", "target_language": "pt",
                "target_currency": "BRL", "ship_to_country": "BR"
            }
            
            sorted_items = sorted(params.items())
            concat = "".join(f"{k}{v}" for k, v in sorted_items)
            raw = f"{app_secret}{concat}{app_secret}".encode("utf-8")
            params["sign"] = hashlib.md5(raw).hexdigest().upper()

            resp = requests.get(api_url, params=params, timeout=40)
            resp.raise_for_status()
            data = resp.json()

            products = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
            if not products: return "Nenhum produto encontrado."

            simplified_products = [{"title": p.get("product_title", "-"), "price": p.get("target_sale_price", "N/A"), "link": p.get("promotion_link") or p.get("product_detail_url", "")} for p in products]
            return json.dumps(simplified_products)

        except Exception as e:
            logger.error(f"Erro na AliExpressSearchTool: {e}")
            return f"Erro ao buscar produtos: {e}"

aliexpress_tool = AliExpressSearchTool()

# ==============================================================================
# CONFIGURAÇÃO DO LLM (GROQ)
# ==============================================================================
try:
    # ==================================================================
    # A ÚLTIMA TENTATIVA: Usando o modelo Mixtral, que está ativo.
    # ==================================================================
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="mixtral-8x7b-32768" 
    )
    logger.info("LLM da Groq inicializado com sucesso com o modelo mixtral-8x7b-32768.")
except Exception as e:
    logger.error(f"Falha ao inicializar o LLM da Groq: {e}")
    llm = None

# ==============================================================================
# DEFINIÇÃO DOS AGENTES E TAREFAS (CREWAI)
# ==============================================================================
request_analyzer = Agent(role='Analisador de Pedidos', goal='Analisar a mensagem do cliente, entender a intenção e extrair os termos de busca.', backstory='Você é um especialista em atendimento que entende a necessidade real do cliente.', llm=llm, allow_delegation=False, verbose=True)
product_hunter = Agent(role='Especialista em Buscas no AliExpress', goal='Encontrar os melhores produtos correspondentes aos termos de busca.', backstory='Você é um mestre em usar a API do AliExpress.', llm=llm, tools=[aliexpress_tool], allow_delegation=False, verbose=True)
response_curator = Agent(role='Curador de Respostas', goal='Selecionar os 3 melhores produtos e formatar uma resposta final amigável.', backstory='Você tem um olho clínico para qualidade e sabe apresentar informações de forma clara.', llm=llm, allow_delegation=False, verbose=True)

analysis_task = Task(
    description='Analise a mensagem do cliente: "{message}". Classifique a intenção como "busca_produto" ou "conversa_geral". Se for busca, extraia os termos de busca. Crie uma resposta empática.',
    expected_output='Um objeto JSON seguindo o modelo AnalysisModel.',
    agent=request_analyzer,
    output_pydantic=AnalysisModel
)

product_task = Task(description='Com base nos termos de busca da análise, use a ferramenta para encontrar os produtos.', expected_output='Uma lista JSON de produtos.', agent=product_hunter, context=[analysis_task])
curation_task = Task(description='Analise a conversa e a lista de produtos. Selecione os 3 melhores e formate uma resposta final para o cliente. Se nenhum produto foi encontrado, crie uma mensagem simpática informando isso.', expected_output='O texto final da mensagem a ser enviada para o cliente.', agent=response_curator, context=[analysis_task, product_task])

shopping_crew = Crew(agents=[request_analyzer, product_hunter, response_curator], tasks=[analysis_task, product_task, curation_task], process=Process.sequential, verbose=2)

# ==============================================================================
# CLIENTE WHATSAPP
# ==============================================================================
class WhatsAppClient:
    def __init__(self):
        self.api_url = f"https://graph.facebook.com/v20.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID' )}/messages"
        self.token = os.getenv("WHATSAPP_TOKEN")
        if not (self.token and os.getenv("WHATSAPP_PHONE_NUMBER_ID")): logger.error("Credenciais do WhatsApp não configuradas!")
        else: logger.info("Cliente WhatsApp inicializado.")

    def send_text_message(self, recipient_id: str, message: str):
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": recipient_id, "type": "text", "text": {"body": message, "preview_url": True}}
        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info(f"Mensagem final enviada para {recipient_id}")
        except requests.RequestException as e:
            logger.error(f"Falha ao enviar WhatsApp: {e}")

# ==============================================================================
# FLASK & ROTAS
# ==============================================================================
app = Flask(__name__)
whatsapp_client = WhatsAppClient()

@app.route("/health", methods=["GET"])
def health(): return "OK", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN"):
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    try:
        payload = request.get_json()
        logger.info("Webhook recebido: %s", json.dumps(payload, indent=2))
        
        change = payload["entry"][0]["changes"][0]
        if change["field"] == "messages":
            message_data = change["value"]["messages"][0]
            sender_id = message_data["from"]
            user_message = message_data["text"]["body"]

            logger.info(f"Mensagem de {sender_id}: '{user_message}'")
            
            if not llm:
                whatsapp_client.send_text_message(sender_id, "Desculpe, meu cérebro (LLM) não está funcionando no momento.")
                return jsonify({"status": "ok"}), 200

            inputs = {'message': user_message}
            result = shopping_crew.kickoff(inputs=inputs)
            
            logger.info("Resultado final da tripulação: %s", result)
            whatsapp_client.send_text_message(sender_id, result)

    except (KeyError, IndexError, TypeError) as e:
        logger.info("Ignorado: webhook sem texto de mensagem de usuário ou formato inesperado. Erro: %s", e)
    except Exception as e:
        logger.error("Erro inesperado no webhook: %s", e, exc_info=True)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
