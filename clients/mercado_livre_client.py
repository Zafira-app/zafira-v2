# clients/mercado_livre_client.py

import os
import requests
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class MercadoLivreClient:
    """
    Busca produtos no Mercado Livre e já monta links de afiliado.
    """

    def __init__(self):
        self.base_url      = "https://api.mercadolibre.com/sites/MLB/search"
        self.affiliate_id  = os.getenv("ML_AFFILIATE_ID", "").strip()
        self.social_tool   = os.getenv("ML_SOCIAL_TOOL", "").strip()
        self.social_ref    = os.getenv("ML_SOCIAL_REF", "").strip()

        if not self.affiliate_id:
            logger.warning("ML_AFFILIATE_ID não configurado – links sem afiliado.")

    def _make_affiliate_link(self, permalink: str, query: str) -> str:
        sep = "&" if "?" in permalink else "?"
        link = f"{permalink}{sep}mkt_affiliate={self.affiliate_id}&forceInApp=true"
        # se tiver bloco social opcional
        if self.social_tool and self.social_ref:
            mq = quote_plus(query)
            link += (
                f"&matt_word={mq}"
                f"&matt_tool={self.social_tool}"
                f"&ref={quote_plus(self.social_ref)}"
            )
        return link

    def search_products(self, query: str, limit: int = 10, offset: int = 0):
        params = {"q": query, "limit": limit, "offset": offset}
        try:
            resp = requests.get(self.base_url, params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("results", [])
        except Exception as e:
            logger.error(f"Erro na busca do Mercado Livre: {e}")
            return []

        products = []
        for item in items:
            title     = item.get("title", "")
            price     = str(item.get("price", "0"))
            thumbnail = item.get("thumbnail", "")
            permalink = item.get("permalink", "")
            affiliate_link = self._make_affiliate_link(permalink, query)

            products.append({
                "product_title":          title,
                "target_sale_price":      price,
                "product_main_image_url": thumbnail,
                "promotion_link":         affiliate_link,
                "source":                 "MercadoLivre"
            })

        return products
