import os
import time
import hashlib
import logging
import requests

logger = logging.getLogger(__name__)

class AliExpressClient:
    """
    Cliente para chamar aliexpress.affiliate.product.query (Affiliate API),
    usando assinatura MD5 e timestamp UTC no formato correto.
    """

    def __init__(self):
        # Se você usa proxy para escapar do AppWhiteIpLimit, mantenha essa URL.
        # Caso contrário, troque para "https://api-sg.aliexpress.com/sync"
        self.api_url = os.getenv("AE_PROXY_URL", "https://api-sg.aliexpress.com/sync")
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY", "")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET", "")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID", "")

        if not (self.app_key and self.app_secret and self.tracking_id):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("AliExpressClient (Affiliate API / MD5) inicializado.")

    def _generate_signature(self, params: dict) -> str:
        """
        MD5(app_secret + concat(chave+valor ordenados) + app_secret).upper()
        """
        sorted_items = sorted(params.items())
        concat = "".join(f"{k}{v}" for k, v in sorted_items)
        raw = f"{self.app_secret}{concat}{self.app_secret}".encode("utf-8")
        sign = hashlib.md5(raw).hexdigest().upper()
        logger.debug("MD5 raw string: %s", raw)
        logger.debug("MD5 signature: %s", sign)
        return sign

    def search_products(self, keywords: str, limit: int = 3) -> dict:
        """
        Chama aliexpress.affiliate.product.query e retorna o dict da resposta JSON.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        params = {
            "app_key": self.app_key,
            "method": "aliexpress.affiliate.product.query",
            "sign_method": "md5",
            "timestamp": timestamp,
            "keywords": keywords,
            "tracking_id": self.tracking_id,
            "page_size": str(limit),
            "target_language": "pt",
            "target_currency": "BRL",
            "ship_to_country": "BR"
        }

        # Assinatura MD5
        params["sign"] = self._generate_signature(params)

        # Log de diagnóstico
        prepared = requests.Request("GET", self.api_url, params=params).prepare()
        logger.info("AliExpress QUERY URL: %s", prepared.url)

        try:
            resp = requests.get(self.api_url, params=params, timeout=40)
            logger.info("AliExpress STATUS: %s", resp.status_code)
            logger.info("AliExpress BODY: %s", resp.text[:500])
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Erro na API AliExpress: %s", e, exc_info=True)
            return {"error": str(e)}
