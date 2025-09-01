import os
import logging
import requests

logger = logging.getLogger(__name__)

class GROCClient:
    """
    Cliente para buscar itens de mercearia via GROC API.
    """
    def __init__(self):
        self.base_url = os.getenv("GROC_BASE_URL", "https://api.groc.example.com/v1")
        self.api_key  = os.getenv("GROQ_API_KEY", "")
        if not self.api_key:
            logger.error("GROC_API_KEY não configurado!")
        else:
            logger.info("Cliente GROC inicializado.")

    def search_items(self, query: str, limit: int = 5) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params  = {"q": query, "limit": limit}
        try:
            resp = requests.get(f"{self.base_url}/search", headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Erro na GROC API: %s", e, exc_info=True)
            return {"error": str(e)}
