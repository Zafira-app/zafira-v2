import os
import time
import hashlib
import logging
import requests
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class AliExpressClient:
    """
    Cliente para aliexpress.affiliate.product.query usando sign_method=md5,
    com valores URL-encoded no cálculo da assinatura.
    """

    def __init__(self):
        self.api_url = os.getenv("AE_PROXY_URL", "https://api-sg.aliexpress.com/sync")
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY", "")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET", "")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID", "")

        if not (self.app_key and self.app_secret and self.tracking_id):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("AliExpressClient (Affiliate MD5) inicializado.")

    def _generate_signature(self, params: dict) -> str:
        """
        Faz MD5(app_secret + concat_por_nome_valor + app_secret), onde
        cada valor é URL-encoded (quote_plus) para corresponder à query real.
        """
        # 1) Ordena por chave
        items = sorted(params.items())
        # 2) URL-encode no valor
        encoded = [(k, quote_plus(str(v))) for k, v in items]
        # 3) Monta string concatenada
        concat = "".join(f"{k}{v}" for k, v in encoded)
        # 4) Adiciona secret antes e depois
        raw = f"{self.app_secret}{concat}{self.app_secret}".encode("utf-8")
        sig = hashlib.md5(raw).hexdigest().upper()

        logger.debug("String para MD5: %s", raw)
        logger.debug("MD5 signature: %s", sig)
        return sig

    def search_products(self, keywords: str, limit: int = 3) -> dict:
        """
        Chama aliexpress.affiliate.product.query e devolve o JSON da resposta.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        params = {
            "app_key":    self.app_key,
            "method":     "aliexpress.affiliate.product.query",
            "sign_method":"md5",
            "timestamp":  timestamp,
            "keywords":   keywords,
            "tracking_id":self.tracking_id,
            "page_size":  str(limit),
            "target_language":"pt",
            "target_currency":"BRL",
            "ship_to_country":"BR"
        }

        # injeta a assinatura correta
        params["sign"] = self._generate_signature(params)

        # mostra a URL real para debug
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
