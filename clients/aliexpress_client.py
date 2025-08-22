# aliexpress_client.py - VERSÃO FINAL: SHA256 + LÓGICA STACKOVERFLOW

import requests
import hashlib
import time
import logging
import os
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class AliExpressClient:
    def __init__(self):
        self.api_url = "https://api-sg.aliexpress.com/sync"
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY" )
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress (SHA256 + StackOverflow) inicializado")

    def _get_public_ip(self) -> str:
        try:
            ip = requests.get('https://api.ipify.org', timeout=10 ).text
            logger.info(f"O IP de saída detectado é: {ip}")
            return ip
        except Exception as e:
            logger.error(f"Falha ao detectar o IP de saída: {e}")
            return "Não foi possível detectar o IP"

    def _generate_signature(self, params: dict) -> str:
        """
        Gera a assinatura SHA256, combinando a lógica do painel e do StackOverflow.
        """
        # Ordena os parâmetros em ordem alfabética
        sorted_params = sorted(params.items())
        
        # Concatena os parâmetros em uma única string
        concatenated_string = "".join([f"{k}{v}" for k, v in sorted_params])
        
        # Adiciona o app_secret no início e no fim
        string_to_sign = self.app_secret + concatenated_string + self.app_secret
        
        # Gera o hash SHA256 e converte para maiúsculas
        signature = hashlib.sha256(string_to_sign.encode('utf-8')).hexdigest().upper()
        return signature

    def search_products(self, keywords: str, limit: int = 3) -> list | bool:
        self._get_public_ip()

        if not all([self.app_key, self.app_secret, self.tracking_id]):
            return False

        timestamp = str(int(time.time() * 1000))
        
        params = {
            'app_key': self.app_key,
            'method': 'aliexpress.affiliate.product.query',
            'sign_method': 'sha256', # CORRIGIDO PARA SHA256
            'timestamp': timestamp,
            'keywords': keywords,
            'tracking_id': self.tracking_id,
            'page_size': str(limit),
            'target_language': 'PT',
            'target_currency': 'BRL',
            'ship_to_country': 'BR'
        }

        params['sign'] = self._generate_signature(params)
        
        full_url = f"{self.api_url}?{urlencode(params)}"
        logger.info(f"Executando requisição para a URL: {full_url}")

        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            data = response.json()
            logger.info(f"Resposta completa da API AliExpress: {data}")

            if 'error_response' in data:
                error_info = data['error_response']
                logger.error(f"Erro da API AliExpress: Código {error_info.get('code')}, Mensagem: {error_info.get('msg')}")
                return False

            result = data.get('aliexpress_affiliate_product_query_response', {}).get('resp_result', {}).get('result', {})
            products = result.get('products', {}).get('product', [])
            
            if not products:
                logger.warning("A busca foi bem-sucedida, mas nenhum produto foi retornado.")
                return []
            
            return products

        except requests.exceptions.RequestException as e:
            logger.error(f"Exceção na requisição para a API do AliExpress: {e}")
            return False
