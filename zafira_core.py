import os
import json
import logging

from pydantic import BaseModel, ConfigDict
from crewai import Agent, Task, Crew, Process
from crewai_tools import BaseTool
from langchain_groq import ChatGroq

from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient

logger = logging.getLogger(__name__)

class AliExpressToolAdapter(BaseTool):
    name: str = "AliExpress Search"
    description: str = "Busca produtos no AliExpress via API de afiliados."
    aliexpress_client: AliExpressClient
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, keywords: str) -> str:
        logger.info(f"[AliExpressTool] Buscando por: '{keywords}'")
        data = self.aliexpress_client.search_products(keywords)
        products = (
            data.get("aliexpress_affiliate_product_query_response", {})
                .get("resp_result", {})
                .get("result", {})
                .get("products", {})
                .get("product", [])
        )
        return json.dumps(products or [])

class AnalysisModel(BaseModel):
    intent: str
    search_terms: str | None
    empathetic_reply: str

class ZafiraCore:
    def __init__(self):
        logger.info("Inicializando Zafira Core…")
        self.whatsapp_client   = WhatsAppClient()
        self.aliexpress_client = AliExpressClient()
        self.llm = self._initialize_llm()
        self.crew = self._initialize_crew() if self.llm else None

        if not self.crew:
            logger.error("CrewAI desativado – falha ao iniciar LLM.")
        else:
            logger.info("CrewAI iniciado com sucesso.")

    def _initialize_llm(self) -> ChatGroq | None:
        groq_key = os.getenv("GROQ_API_KEY", "")
        if not groq_key:
            logger.error("GROQ_API_KEY não configurada.")
            return None
        try:
            llm = ChatGroq(api_key=groq_key, model_name="llama3-8b-8192")
            logger.info("Groq LLM inicializado: llama3-8b-8192.")
            return llm
        except Exception as e:
            logger.error(f"Erro ao iniciar LLM Groq: {e}", exc_info=True)
            return None

    def _initialize_crew(self) -> Crew:
        tool = AliExpressToolAdapter(aliexpress_client=self.aliexpress_client)
        requester = Agent(
            role="Analisador de Mensagem",
            goal="Entender intenção e extrair termos de busca.",
            backstory="Você é um especialista em atendimento ao cliente.",
            llm=self.llm, allow_delegation=False, verbose=False
        )
        hunter = Agent(
            role="Buscador AliExpress",
            goal="Buscar produtos a partir dos termos extraídos.",
            backstory="Você domina a API de afiliados do AliExpress.",
            llm=self.llm, tools=[tool], allow_delegation=False, verbose=False
        )
        curator = Agent(
            role="Curador de Resposta",
            goal="Selecionar 3 melhores produtos e formatar a resposta final.",
            backstory="Você é excelente em comunicação clara e amigável.",
            llm=self.llm, allow_delegation=False, verbose=False
        )
        analysis_task = Task(
            description='Analise a mensagem: "{message}", extraia intent e termos.',
            expected_output="JSON conforme AnalysisModel.",
            agent=requester, output_pydantic=AnalysisModel
        )
        product_task = Task(
            description="Use os termos da análise para buscar produtos.",
            expected_output="Lista JSON de produtos.",
            agent=hunter, context=[analysis_task]
        )
        curation_task = Task(
            description="Selecione e formate a resposta final para o usuário.",
            expected_output="Texto final da mensagem.",
            agent=curator, context=[analysis_task, product_task]
        )
        return Crew(
            agents=[requester, hunter, curator],
            tasks=[analysis_task, product_task, curation_task],
            process=Process.sequential, verbose=1
        )

    def process_message(self, sender_id: str, user_message: str):
        logger.info(f"[ZafiraCore] Mensagem recebida de {sender_id}: '{user_message}'")
        if not self.crew:
            self.whatsapp_client.send_text_message(
                sender_id,
                "Desculpe, estou com dificuldade no meu cérebro. Tente novamente mais tarde."
            )
            return
        try:
            inputs = {"message": user_message}
            result = self.crew.kickoff(inputs=inputs)
            logger.info(f"[ZafiraCore] Resposta gerada pelo Crew: {result}")
            self.whatsapp_client.send_text_message(sender_id, result)
        except Exception as e:
            logger.error(f"Erro crítico no CrewAI: {e}", exc_info=True)
            self.whatsapp_client.send_text_message(
                sender_id,
                "Putz, deu um nó na minha cabeça! Tente reformular a pergunta."
            )
