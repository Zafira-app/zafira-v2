import os
import logging
import requests

logger = logging.getLogger(__name__)

class AliExpressClient:
    """
    Cliente simples para consultar a API de afiliados do AliExpress.
    """
    def __init__(self):
        self.app_key     = os.getenv("ALIEXPRESS_APP_KEY", "")
        self.app_secret  = os.getenv("ALIEXPRESS_APP_SECRET", "")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID", "")
        self.base_url    = os.getenv("AE_PROXY_URL", "https://api-sg.aliexpress.com/sync")

        logger.info("Cliente AliExpress inicializado.")

    def search_products(self, keywords: str, limit: int = 5, page_no: int = 1) -> dict:
        """
        Faz a query de afiliados:
        ?app_key=...&method=aliexpress.affiliate.product.query
        &page_size={limit}&page_no={page_no}&keywords={keywords}...
        """
        params = {
            "app_key":       self.app_key,
            "method":        "aliexpress.affiliate.product.query",
            "sign_method":   "md5",
            "timestamp":     requests.utils.quote(requests.utils.formatdate(usegmt=True)),
            "keywords":      keywords,
            "tracking_id":   self.tracking_id,
            "page_size":     limit,
            "page_no":       page_no,
            "target_language": "pt",
            "target_currency": "BRL",
            "ship_to_country": "BR",
        }
        # gera sign MD5 (mantenha sua implementação)
        params["sign"] = self._make_sign(params)

        try:
            resp = requests.get(self.base_url, params=params, timeout=15)
            logger.info("AliExpress URL: %s", resp.url)

            # log completo do body para depuração
            logger.info("AliExpress BODY: %s", resp.text)

            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Erro AliExpress API: %s", e, exc_info=True)
            return {"error": str(e)}

    def _make_sign(self, params: dict) -> str:
        # sua lógica de MD5 aqui
        # exemplo simplificado:
        import hashlib
        text = "".join(f"{k}{params[k]}" for k in sorted(params))
        text = self.app_secret + text + self.app_secret
        return hashlib.md5(text.encode("utf-8")).hexdigest().upper()
