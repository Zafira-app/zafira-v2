"""
Zafira V2.0 - Cliente WhatsApp
Comunicação robusta com a API do WhatsApp Business
"""

import requests
import os
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

class WhatsAppClient:
    """Cliente robusto para WhatsApp Business API"""
    
    def __init__(self):
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        
        # Validação de credenciais
        if not all([self.access_token, self.phone_number_id] ):
            logger.error("Credenciais do WhatsApp não configuradas")
        else:
            logger.info("Cliente WhatsApp inicializado com sucesso")
    
    def send_message(self, user_id: str, message: str) -> bool:
        """Envia mensagem para usuário com retry automático"""
        if not all([self.access_token, self.phone_number_id]):
            logger.error("Credenciais WhatsApp não configuradas")
            return False
        
        try:
            logger.info(f"Enviando mensagem para {user_id}: {message[:50]}...")
            
            # Tenta enviar com retry
            for attempt in range(3):
                try:
                    success = self._send_api_message(user_id, message)
                    if success:
                        logger.info(f"Mensagem enviada com sucesso para {user_id}")
                        return True
                    else:
                        logger.warning(f"Tentativa {attempt + 1}: Falha no envio")
                        
                except Exception as e:
                    logger.error(f"Tentativa {attempt + 1} falhou: {e}")
                    if attempt < 2:  # Não é a última tentativa
                        time.sleep(2)  # Aguarda 2 segundos antes de tentar novamente
                        continue
                    else:
                        raise e
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False
    
    def _send_api_message(self, user_id: str, message: str) -> bool:
        """Executa envio via API do WhatsApp"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Formata mensagem (quebra em partes se muito longa)
            formatted_message = self._format_message(message)
            
            payload = {
                "messaging_product": "whatsapp",
                "to": user_id,
                "type": "text",
                "text": {
                    "body": formatted_message
                }
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Verifica se há erro na resposta
                if "error" in data:
                    logger.error(f"Erro da API WhatsApp: {data['error']}")
                    return False
                
                # Verifica se mensagem foi aceita
                if "messages" in data and data["messages"]:
                    message_id = data["messages"][0].get("id")
                    logger.info(f"Mensagem aceita com ID: {message_id}")
                    return True
                else:
                    logger.error("Resposta da API não contém ID da mensagem")
                    return False
                    
            else:
                logger.error(f"Erro HTTP na API WhatsApp: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro na chamada da API WhatsApp: {e}")
            return False
    
    def _format_message(self, message: str) -> str:
        """Formata mensagem para WhatsApp"""
        try:
            # Limite de caracteres do WhatsApp
            max_length = 4096
            
            if len(message) <= max_length:
                return message
            
            # Se muito longa, trunca e adiciona indicação
            truncated = message[:max_length - 50]
            return f"{truncated}...\n\n(Mensagem truncada)"
            
        except Exception as e:
            logger.error(f"Erro ao formatar mensagem: {e}")
            return message[:1000]  # Fallback seguro
    
    def send_typing_indicator(self, user_id: str) -> bool:
        """Envia indicador de digitação (opcional)"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": user_id,
                "type": "typing"
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erro ao enviar indicador de digitação: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Testa conexão com a API do WhatsApp"""
        try:
            logger.info("Testando conexão com WhatsApp...")
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Testa com uma requisição simples
            test_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
            response = requests.get(test_url, headers=headers, timeout=10 )
            
            if response.status_code == 200:
                logger.info("Conexão com WhatsApp OK")
                return True
            else:
                logger.error(f"Erro no teste de conexão: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erro no teste de conexão WhatsApp: {e}")
            return False
    
    def mark_as_read(self, message_id: str) -> bool:
        """Marca mensagem como lida (opcional)"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erro ao marcar como lida: {e}")
            return False
