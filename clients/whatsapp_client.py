# whatsapp_client.py

import os
import requests
import logging

logger = logging.getLogger(__name__)

class WhatsAppClient:
    """Cliente para interagir com a API do WhatsApp Cloud."""

    def __init__(self):
        self.api_url = "https://graph.facebook.com/v20.0/"
        self.token = os.getenv("WHATSAPP_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

        if not all([self.token, self.phone_number_id]):
            logger.error("Credenciais do WhatsApp não configuradas!")
        else:
            logger.info("Cliente WhatsApp inicializado com sucesso")

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
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            data = resp.json()
            if resp.status_code == 200 and "messages" in data:
                msg_id = data["messages"][0]["id"]
                logger.info(f"Mensagem aceita com ID: {msg_id}")
                logger.info(f"Mensagem enviada com sucesso para {recipient_id}")
                return True
            else:
                logger.error(f"Erro ao enviar texto para {recipient_id}: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Exceção ao enviar texto para {recipient_id}: {e}")
            return False

    def send_media_message(
        self,
        recipient_id: str,
        media_url: str,
        caption: str = "",
        media_type: str = "image"
    ) -> bool:
        """
        Envia mídia (imagem ou vídeo) com legenda.
        
        Parâmetros:
          - recipient_id: número do WhatsApp destino (ex: '55119xxxx').
          - media_url: URL pública da imagem ou vídeo.
          - caption: texto que acompanha a mídia.
          - media_type: 'image' ou 'video'.
        """
        if not all([self.token, self.phone_number_id]):
            logger.error("Não é possível enviar mídia, credenciais ausentes.")
            return False

        url = f"{self.api_url}{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        media_payload = { "link": media_url }
        # WhatsApp Cloud API suporta campo 'caption' dentro do objeto de mídia
        if caption:
            media_payload["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": media_type,
            media_type: media_payload,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            data = resp.json()
            if resp.status_code == 200 and "messages" in data:
                msg_id = data["messages"][0]["id"]
                logger.info(f"{media_type.capitalize()} aceita com ID: {msg_id}")
                return True
            else:
                logger.error(f"Erro ao enviar {media_type} para {recipient_id}: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Exceção ao enviar {media_type} para {recipient_id}: {e}")
            return False

    def send_error_message(self, recipient_id: str) -> bool:
        """Envia uma mensagem de erro padronizada."""
        error_text = (
            "Ops! 😅 Tive um probleminha técnico aqui dentro. "
            "Minha equipe já foi notificada e estou tentando de novo. "
            "Por favor, aguarde um instante!"
        )
        return self.send_text_message(recipient_id, error_text)
