# whatsapp_client.py - VERSÃO FINAL PADRONIZADA

import os
import requests
import logging

logger = logging.getLogger(__name__)

class WhatsAppClient:
    """Cliente para interagir com a API do WhatsApp Cloud."""
    
    def __init__(self):
        self.api_url = "https://graph.facebook.com/v20.0/"
        self.token = os.getenv("WHATSAPP_TOKEN" )
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        
        if not all([self.token, self.phone_number_id]):
            logger.error("Credenciais do WhatsApp não configuradas!")
        else:
            logger.info("Cliente WhatsApp inicializado com sucesso")

    # FIX: Renomeado de 'send_message' para 'send_text_message' para padronizar com o zafira_core
    def send_text_message(self, recipient_id: str, message: str) -> bool:
        """Envia uma mensagem de texto para um destinatário."""
        if not all([self.token, self.phone_number_id]):
            logger.error("Não é possível enviar mensagem, credenciais ausentes.")
            return False
            
        url = f"{self.api_url}{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message},
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_data = response.json()

            if response.status_code == 200 and "messages" in response_data:
                message_id = response_data["messages"][0]["id"]
                logger.info(f"Mensagem aceita com ID: {message_id}")
                # A API apenas aceita a mensagem, não confirma o envio final aqui.
                # O status 'sent' virá por webhook. Consideramos sucesso se a API aceitou.
                logger.info(f"Mensagem enviada com sucesso para {recipient_id}")
                return True
            else:
                logger.error(f"Erro ao enviar mensagem para {recipient_id}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exceção ao enviar mensagem para {recipient_id}: {e}")
            return False

    # FIX: Adicionada a função 'send_error_message' que estava faltando
    def send_error_message(self, recipient_id: str) -> bool:
        """Envia uma mensagem de erro padronizada."""
        error_text = "Ops! 😅 Tive um probleminha técnico aqui dentro. Minha equipe já foi notificada e estou tentando de novo. Por favor, aguarde um instante!"
        return self.send_text_message(recipient_id, error_text)

