import os
import time
import hashlib
import logging
import requests
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class AliExpressClient:
    """
    Cliente para chamar aliexpress.affiliate.product.query (Affiliate API),
    com debug de variáveis e assinatura MD5.
    """

    def __init__(self):
        # Lê as variáveis de ambiente
        self.app_key     = os.getenv("ALIEXPRESS_APP_KEY", "")
        self.app_secret  = os.getenv("ALIEXPRESS_APP_SECRET", "")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID", "")
        self.api_url     = os.getenv("AE_PROXY_URL", "https://api-sg.aliexpress.com/sync")

        # DEBUG: mostra partes do key e secret para confirmação
        masked_key    = f"{self.app_key[:3]}…{self.app_key[-3:]}"
        masked_secret = f"{self.app_secret[:3]}…{self.app_secret[-3:]}"
        logger.info("DEBUG AliExpressKey: %s, Secret: %s", masked_key, masked_secret)

        if not (self.app_key and self.app_secret and self.tracking_id):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("AliExpressClient inicializado.")

    def _generate_signature(self, params: dict) -> str:
        """
        MD5(app_secret + concat(chave+valor ordenados, URL-encoded) + app_secret).upper()
        """
        # 1) Ordena params por chave
        items = sorted(params.items())
        # 2) Aplica URL-encoding no valor para casar com o query string real
        encoded = [(k, quote_plus(str(v))) for k, v in items]
        # 3) Concatena tudo
        concat = "".join(f"{k}{v}" for k, v in encoded)
        # 4) Adiciona secret antes e depois
        raw = f"{self.app_secret}{concat}{self.app_secret}".encode("utf-8")
        signature = hashlib.md5(raw).hexdigest().upper()

        # DEBUG: mostra a string e a assinatura gerada
        logger.info("String para MD5: %s", raw)
        logger.info("MD5 gerado: %s", signature)

        return signature

    def search_products(self, keywords: str, limit: int = 3) -> dict:
        """
        Executa aliexpress.affiliate.product.query e retorna o JSON de resposta.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        params = {
            "app_key":         self.app_key,
            "method":          "aliexpress.affiliate.product.query",
            "sign_method":     "md5",
            "timestamp":       timestamp,
            "keywords":        keywords,
            "tracking_id":     self.tracking_id,
            "page_size":       str(limit),
            "target_language": "pt",
            "target_currency": "BRL",
            "ship_to_country": "BR"
        }

        # Gera e injeta a assinatura MD5
        params["sign"] = self._generate_signature(params)

        # DEBUG: mostra a URL completa que será chamada
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
