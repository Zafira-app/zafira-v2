# zafira_core.py - VERSÃO 4.1 - REUTILIZANDO SUA ESTRUTURA EXISTENTE

import os
import json
import logging
from crewai import Agent, Task, Crew, Process, BaseTool
from pydantic import BaseModel
from langchain_groq import ChatGroq

# Importa os clientes que VOCÊ criou, que é a forma correta.
from clients.whatsapp_client import WhatsAppClient
from clients.aliexpress_client import AliExpressClient

# Configuração do Logging
logger = logging.getLogger(__name__)

# ==============================================================================
# FERRAMENTA-ADAPTADOR PARA O SEU ALIEXPRESSCLIENT
# Isso permite que o CrewAI use seu código existente sem modificá-lo.
# ==============================================================================
class AliExpressToolAdapter(BaseTool):
    name: str = "Ferramenta de Busca de Produtos no AliExpress"
    description: str = "Use esta ferramenta para buscar produtos no AliExpress com base em palavras-chave."
    aliexpress_client: AliExpressClient

    def _run(self, keywords: str) -> str:
        logger.info(f"Adaptador chamando AliExpressClient com keywords: '{keywords}'")
        products = self.aliexpress_client.search_products(keywords)
        if not products or not isinstance(products, list):
            return "Nenhum produto encontrado."
        return json.dumps(products)

# ==============================================================================
# MODELO DE DADOS PARA A SAÍDA DA ANÁLISE
# ==============================================================================
class AnalysisModel(BaseModel):
    intent: str
    search_terms: str | None
    empathetic_reply: str

# ==============================================================================
# ZAFIRA CORE - A CLASSE PRINCIPAL (ATUALIZADA E CORRETA)
# ==============================================================================
class ZafiraCore:
    def __init__(self):
        logger.info("Inicializando o Zafira Core...")
        self.whatsapp_client = WhatsAppClient()
        self.aliexpress_client = AliExpressClient() # <-- Seu cliente existente
        self.llm = self._initialize_llm()
        self.crew = self._initialize_crew() if self.llm else None
        
        if not self.crew:
            logger.error("Zafira Core: CÉREBRO (CREWAI) DESATIVADO DEVIDO A FALHA NA INICIALIZAÇÃO DO LLM.")
        else:
            logger.info("Zafira Core inicializado com sucesso com CrewAI.")

    def _initialize_llm(self):
        """Inicializa o cliente do Large Language Model."""
        try:
            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                logger.error("GROQ_API_KEY não configurada! O LLM não pode ser inicializado.")
                return None
            
            llm = ChatGroq(api_key=groq_api_key, model_name="llama3-8b-8192")
            logger.info("LLM da Groq (llama3-8b-8192) inicializado com sucesso.")
            return llm
        except Exception as e:
            logger.error(f"Falha catastrófica ao inicializar o LLM da Groq: {e}")
            return None

    def _initialize_crew(self):
        """Inicializa os agentes e a tripulação (crew) usando o cliente existente."""
        # Cria a ferramenta adaptadora, passando seu cliente já inicializado.
        aliexpress_tool = AliExpressToolAdapter(aliexpress_client=self.aliexpress_client)

        # --- AGENTES ---
        request_analyzer = Agent(role='Analisador de Pedidos', goal='Analisar a mensagem do cliente, entender a intenção e extrair os termos de busca.', backstory='Você é um especialista em atendimento que entende a necessidade real do cliente.', llm=self.llm, allow_delegation=False, verbose=True)
        product_hunter = Agent(role='Especialista em Buscas no AliExpress', goal='Encontrar os melhores produtos correspondentes aos termos de busca.', backstory='Você é um mestre em usar a API do AliExpress.', llm=self.llm, tools=[aliexpress_tool], allow_delegation=False, verbose=True)
        response_curator = Agent(role='Curador de Respostas', goal='Selecionar os 3 melhores produtos e formatar uma resposta final amigável.', backstory='Você tem um olho clínico para qualidade e sabe apresentar informações de forma clara.', llm=self.llm, allow_delegation=False, verbose=True)

        # --- TAREFAS ---
        analysis_task = Task(description='Analise a mensagem do cliente: "{message}". Classifique a intenção como "busca_produto" ou "conversa_geral". Se for busca, extraia os termos de busca. Crie uma resposta empática.', expected_output='Um objeto JSON seguindo o modelo AnalysisModel.', agent=request_analyzer, output_pydantic=AnalysisModel)
        product_task = Task(description='Com base nos termos de busca da análise, use a ferramenta para encontrar os produtos.', expected_output='Uma lista JSON de produtos.', agent=product_hunter, context=[analysis_task])
        curation_task = Task(description='Analise a conversa e a lista de produtos. Selecione os 3 melhores e formate uma resposta final para o cliente. Se nenhum produto foi encontrado, crie uma mensagem simpática informando isso.', expected_output='O texto final da mensagem a ser enviada para o cliente.', agent=response_curator, context=[analysis_task, product_task])

        return Crew(agents=[request_analyzer, product_hunter, response_curator], tasks=[analysis_task, product_task, curation_task], process=Process.sequential, verbose=2)

    def process_message(self, sender_id: str, user_message: str):
        """Processa a mensagem recebida do usuário usando o CrewAI."""
        logger.info(f"Zafira Core processando mensagem de {sender_id} com CrewAI: '{user_message}'")
        
        if not self.crew:
            self.whatsapp_client.send_text_message(sender_id, "Desculpe, estou com um problema sério no meu cérebro e não consigo pensar agora. Tente novamente mais tarde.")
            return

        try:
            inputs = {'message': user_message}
            result = self.crew.kickoff(inputs=inputs)
            
            logger.info(f"Resultado final da tripulação: {result}")
            self.whatsapp_client.send_text_message(sender_id, result)
        except Exception as e:
            logger.error(f"Erro catastrófico ao executar a tripulação (crew): {e}", exc_info=True)
            self.whatsapp_client.send_text_message(sender_id, "Uau, essa pergunta deu um nó na minha cabeça! Tive um erro aqui. Você pode tentar perguntar de outra forma?")

