"""
Zafira V2.0 - Cérebro Inteligente
Processamento principal de mensagens e inteligência artificial
"""

import re
import logging
from typing import Optional, Dict, List
from aliexpress_client import AliExpressClient
from whatsapp_client import WhatsAppClient
import requests
import json
import os

logger = logging.getLogger(__name__)

class ZafiraCore:
    """Cérebro principal da Zafira - Inteligente e conversacional"""
    
    def __init__(self):
        self.aliexpress = AliExpressClient()
        self.whatsapp = WhatsAppClient()
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        
        # Contexto da conversa (memória simples )
        self.conversation_context = {}
        
        logger.info("Zafira Core inicializada com sucesso")
    
    def process_message(self, user_id: str, message: str) -> bool:
        """Processa uma mensagem e gera resposta inteligente"""
        try:
            logger.info(f"Processando mensagem de {user_id}: {message}")
            
            # Analisa a intenção da mensagem
            intent = self.analyze_intent(message)
            logger.info(f"Intenção detectada: {intent}")
            
            # Gera resposta baseada na intenção
            if intent == "saudacao":
                response = self.handle_greeting(user_id, message)
            elif intent == "produto":
                response = self.handle_product_request(user_id, message)
            elif intent == "agradecimento":
                response = self.handle_thanks(user_id, message)
            else:
                response = self.handle_conversation(user_id, message)
            
            # Envia a resposta
            if response:
                success = self.whatsapp.send_message(user_id, response)
                if success:
                    logger.info(f"Resposta enviada com sucesso para {user_id}")
                    return True
                else:
                    logger.error(f"Falha ao enviar resposta para {user_id}")
                    return False
            else:
                logger.warning("Nenhuma resposta gerada")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            self.send_error_message(user_id)
            return False
    
    def analyze_intent(self, message: str) -> str:
        """Analisa a intenção da mensagem de forma inteligente"""
        message_lower = message.lower().strip()
        
        # Palavras-chave para saudações
        greeting_patterns = [
            r'\b(oi|olá|ola|hey|e aí|eai|bom dia|boa tarde|boa noite)\b',
            r'\b(como vai|tudo bem|como está|como esta)\b',
            r'^(oi|olá|ola|hey)$'
        ]
        
        # Palavras-chave para produtos
        product_patterns = [
            r'\b(quero|preciso|busco|procuro|me mostra|mostra|encontra)\b',
            r'\b(fone|headphone|celular|smartphone|tênis|tenis|notebook|laptop)\b',
            r'\b(produto|comprar|compra|preço|preco|oferta|desconto)\b',
            r'\b(até|ate|por|menos de|máximo|maximo)\s*\d+\s*(reais|real|r\$)\b'
        ]
        
        # Palavras-chave para agradecimento
        thanks_patterns = [
            r'\b(obrigad[oa]|valeu|vlw|thanks|brigad[oa])\b',
            r'\b(muito bom|perfeito|excelente|ótimo|otimo)\b'
        ]
        
        # Verifica padrões
        for pattern in greeting_patterns:
            if re.search(pattern, message_lower):
                return "saudacao"
        
        for pattern in product_patterns:
            if re.search(pattern, message_lower):
                return "produto"
        
        for pattern in thanks_patterns:
            if re.search(pattern, message_lower):
                return "agradecimento"
        
        return "conversa"
    
    def handle_greeting(self, user_id: str, message: str) -> str:
        """Lida com saudações de forma calorosa"""
        greetings = [
            "Oi! 😊 Sou a Zafira, sua assistente de compras! Como posso te ajudar a encontrar produtos incríveis hoje?",
            "Olá! 👋 Pronta para te ajudar a encontrar os melhores produtos! O que você está procurando?",
            "Oi! 🛍️ Sou especialista em encontrar produtos com ótimos preços! Me conta o que você precisa!",
            "Olá! ✨ Vamos encontrar produtos perfeitos para você! O que tem em mente?"
        ]
        
        import random
        return random.choice(greetings)
    
    def handle_product_request(self, user_id: str, message: str) -> str:
        """Lida com pedidos de produtos"""
        try:
            # Extrai termos de busca da mensagem
            search_terms = self.extract_product_terms(message)
            logger.info(f"Termos de busca extraídos: {search_terms}")
            
            if not search_terms:
                return "Hmm, não consegui entender exatamente o que você está procurando. Pode me dar mais detalhes? Por exemplo: 'quero um fone bluetooth' ou 'celular até 1000 reais' 😊"
            
            # Busca produtos no AliExpress
            products = self.aliexpress.search_products(search_terms)
            
            if not products:
                return f"Não encontrei produtos para '{search_terms}' no momento 😔\n\nTente ser mais específico ou me pergunte sobre outros produtos! Estou aqui para ajudar! 🛍️"
            
            # Formata resposta com produtos
            response = self.format_product_response(search_terms, products)
            return response
            
        except Exception as e:
            logger.error(f"Erro ao processar pedido de produto: {e}")
            return "Ops! Tive um probleminha ao buscar produtos. Tenta novamente em alguns segundos? 😅"
    
    def handle_thanks(self, user_id: str, message: str) -> str:
        """Lida com agradecimentos"""
        thanks_responses = [
            "De nada! 😊 Fico feliz em ajudar! Se precisar de mais alguma coisa, é só falar!",
            "Por nada! 🛍️ Sempre que quiser encontrar produtos incríveis, estarei aqui!",
            "Que bom que ajudei! ✨ Volte sempre que precisar de dicas de produtos!",
            "Disponha! 😄 Adoro ajudar a encontrar produtos perfeitos!"
        ]
        
        import random
        return random.choice(thanks_responses)
    
    def handle_conversation(self, user_id: str, message: str) -> str:
        """Lida com conversas gerais usando IA"""
        try:
            if not self.groq_api_key:
                return "Oi! 😊 Sou especialista em encontrar produtos! Me conta o que você está procurando e vou te ajudar!"
            
            # Usa IA para resposta conversacional
            ai_response = self.get_ai_response(message)
            
            if ai_response:
                return ai_response
            else:
                return "Interessante! 🤔 Mas sou especialista em encontrar produtos! Me conta o que você quer comprar que te ajudo a achar as melhores ofertas! 🛍️"
                
        except Exception as e:
            logger.error(f"Erro na conversa com IA: {e}")
            return "Oi! 😊 Sou a Zafira, especialista em produtos! O que você está procurando hoje?"
    
    def extract_product_terms(self, message: str) -> str:
        """Extrai termos de busca de produtos da mensagem"""
        # Remove palavras irrelevantes
        stop_words = ['quero', 'preciso', 'busco', 'procuro', 'me', 'mostra', 'um', 'uma', 'o', 'a', 'de', 'para', 'com', 'até', 'por']
        
        # Limpa a mensagem
        clean_message = re.sub(r'[^\w\s]', ' ', message.lower())
        words = clean_message.split()
        
        # Remove stop words
        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Junta as palavras relevantes
        search_terms = ' '.join(filtered_words)
        
        return search_terms.strip()
    
    def format_product_response(self, search_terms: str, products: List[Dict]) -> str:
        """Formata resposta com produtos encontrados"""
        response = f"🛍️ Encontrei ótimas opções de {search_terms} para você!\n\n"
        
        for i, product in enumerate(products[:3], 1):
            name = product.get('product_title', 'Produto')[:60]
            price = product.get('target_sale_price', 'Preço não disponível')
            rating = product.get('evaluate_rate', 'N/A')
            link = product.get('promotion_link', '#')
            
            response += f"🏆 **Opção {i}:**\n"
            response += f"📱 {name}\n"
            response += f"💰 {price}\n"
            response += f"⭐ Avaliação: {rating}\n"
            response += f"🔗 {link}\n\n"
        
        response += "✨ Todos os links já incluem desconto especial!\n"
        response += "💬 Quer ver mais opções? É só me falar!"
        
        return response
    
    def get_ai_response(self, message: str) -> Optional[str]:
        """Gera resposta usando IA Groq"""
        try:
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é a Zafira, uma assistente brasileira especialista em encontrar produtos. Seja simpática, use emojis, e sempre direcione a conversa para ajudar com compras. Respostas curtas e objetivas."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                "max_tokens": 100,
                "temperature": 0.7
            }
            
            response = requests.post(self.groq_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data['choices'][0]['message']['content'].strip()
                return ai_response
            else:
                logger.error(f"Erro na API Groq: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao chamar IA: {e}")
            return None
    
    def send_error_message(self, user_id: str):
        """Envia mensagem de erro amigável"""
        try:
            error_message = "Ops! Tive um probleminha técnico 😅\n\nMas já estou funcionando novamente! Me manda sua pergunta que te ajudo! 🛍️"
            self.whatsapp.send_message(user_id, error_message)
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de erro: {e}")
