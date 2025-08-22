# aliexpress_client.py - VERSÃO FINAL BASEADA NA DOCUMENTAÇÃO DA DISTRIBUTION API

import requests
import hashlib
import time
import logging
import os
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class AliExpressClient:
    """
    Cliente para interagir com a AliExpress Distribution Data API,
    seguindo a documentação oficial encontrada (NodeId=27493).
    """
    def __init__(self):
        # Usaremos o proxy com IP estático para evitar o erro AppWhiteIpLimit
        self.api_url = "https://zafira-proxy.fly.dev/sync"
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY" )
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET") 
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")

        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais críticas do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress (Distribution API) inicializado.")

    def _generate_signature(self, params: dict) -> str:
        """
        Gera a assinatura SHA256 conforme a documentação da Distribution API:
        SHA256(app_key + sorted_param_string)
        """
        sorted_params = sorted(params.items())
        concatenated_string = "".join([f"{k}{v}" for k, v in sorted_params])
        string_to_sign = self.app_key + concatenated_string
        
        signature = hashlib.sha256(string_to_sign.encode('utf-8')).hexdigest().upper()
        logger.info(f"String para assinar: {string_to_sign}")
        logger.info(f"Assinatura gerada: {signature}")
        return signature

    def search_products(self, keywords: str, limit: int = 3) -> list | bool:
        """Busca produtos usando o método aliexpress.distribution.product.query."""
        
        params = {
            'app_key': self.app_key,
            'method': 'aliexpress.distribution.product.query',
            'sign_method': 'sha256',
            'timestamp': str(int(time.time() * 1000)),
            'keywords': keywords,
            'tracking_id': self.tracking_id,
            'page_size': str(limit),
            'page_no': '1',
            'fields': 'product_id,product_title,product_main_image_url,target_sale_price,discount,evaluate_rate,target_sale_price_currency,promotion_link'
        }

        params['app_signature'] = self._generate_signature(params)
        
        full_url = f"{self.api_url}?{urlencode(params)}"
        logger.info(f"Executando requisição para a URL: {full_url}")

        try:
            response = requests.post(self.api_url, params=params, timeout=40)
            data = response.json()
            logger.info(f"Resposta completa da API AliExpress: {data}")

            if 'error_response' in data:
                error_info = data['error_response']
                logger.error(f"Erro da API AliExpress: Código {error_info.get('code')}, Mensagem: {error_info.get('msg')}")
                return False

            result = data.get('aliexpress_distribution_product_query_response', {}).get('result', {})
            products = result.get('products', [])
            
            if not products:
                 logger.warning(f"A busca foi bem-sucedida, mas nenhum produto foi retornado para '{keywords}'.")
            
            return products

        except Exception as e:
            logger.error(f"Exceção na busca de produtos: {e}", exc_info=True)
            return False
