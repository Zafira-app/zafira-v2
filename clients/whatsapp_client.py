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

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def send_text_message(self, recipient_id: str, message: str) -> bool:
        """Envia uma mensagem de texto."""
        url = f"{self.api_url}{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message},
        }
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            data = resp.json()
            if resp.status_code == 200 and "messages" in data:
                msg_id = data["messages"][0]["id"]
                logger.info(f"Texto aceito com ID: {msg_id}")
                return True
            logger.error(f"Erro ao enviar texto: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Exceção ao enviar texto: {e}")
        return False

    def send_media_message(
        self,
        recipient_id: str,
        media_url: str,
        caption: str = "",
        media_type: str = "image"
    ) -> bool:
        """Envia imagem ou vídeo com legenda."""
        url = f"{self.api_url}{self.phone_number_id}/messages"
        media_payload = {"link": media_url}
        if caption:
            media_payload["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": media_type,
            media_type: media_payload,
        }
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            data = resp.json()
            if resp.status_code == 200 and "messages" in data:
                msg_id = data["messages"][0]["id"]
                logger.info(f"{media_type.capitalize()} aceito com ID: {msg_id}")
                return True
            logger.error(f"Erro ao enviar {media_type}: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Exceção ao enviar {media_type}: {e}")
        return False

    def send_list_message(
        self,
        recipient_id: str,
        header: str,
        body: str,
        footer: str,
        button: str,
        sections: list
    ) -> bool:
        """Envia uma mensagem interativa do tipo lista."""
        url = f"{self.api_url}{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": header},
                "body":   {"text": body},
                "footer": {"text": footer},
                "action": {"button": button, "sections": sections}
            }
        }
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            data = resp.json()
            if resp.status_code == 200 and "messages" in data:
                msg_id = data["messages"][0]["id"]
                logger.info(f"Lista aceita com ID: {msg_id}")
                return True
            logger.error(f"Erro ao enviar lista: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Exceção ao enviar lista: {e}")
        return False
