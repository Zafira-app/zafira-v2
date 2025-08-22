# aliexpress_client.py - VERSÃO FINAL COM DETECTOR DE IP
import requests
import hashlib
import time
import logging
import os
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class AliExpressClient:
    """
    Cliente para interagir com a API do AliExpress.
    VERSÃO FINAL: Inclui detector de IP de saída para debug do Whitelist.
    """
    def __init__(self):
        self.api_url = "https://api-sg.aliexpress.com/sync"
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY" )
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            # A solução do StackOverflow funcionou, mantemos ela.
            logger.info("Cliente AliExpress (SOLUÇÃO STACKOVERFLOW) inicializado com sucesso")

    def _get_public_ip(self) -> str:
        """Descobre o IP público de saída do servidor para adicioná-lo à whitelist."""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=10 )
            response.raise_for_status()
            ip = response.json()['ip']
            logger.info(f"O IP de saída detectado é: {ip}")
            return ip
        except Exception as e:
            logger.error(f"Falha ao detectar o IP de saída: {e}")
            return "Não foi possível detectar o IP"

    def _generate_signature(self, params: dict) -> str:
        """Gera a assinatura MD5 conforme a solução que funcionou (sem & e =)."""
        # Ordena os parâmetros em ordem alfabética
        sorted_params = sorted(params.items())
        
        # Concatena os parâmetros em uma única string
        concatenated_string = "".join([f"{k}{v}" for k, v in sorted_params])
        
        # Adiciona o app_secret no início e no fim
        string_to_sign = self.app_secret + concatenated_string + self.app_secret
        
        # Gera o hash MD5 e converte para maiúsculas
        signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()
        return signature

    def search_products(self, keywords: str, limit: int = 3) -> list | bool:
        """Busca produtos na API do AliExpress."""
        
        # PASSO 1: Descobrir e logar o IP de saída
        self._get_public_ip()

        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Busca cancelada, credenciais do AliExpress ausentes.")
            return False

        timestamp = str(int(time.time() * 1000))
        
        params = {
            'app_key': self.app_key,
            'method': 'aliexpress.affiliate.product.query',
            'sign_method': 'md5',
            'timestamp': timestamp,
            'keywords': keywords,
            'tracking_id': self.tracking_id,
            'page_size': str(limit),
            'target_language': 'PT',
            'target_currency': 'BRL',
            'ship_to_country': 'BR'
        }

        # Gera a assinatura com os parâmetros
        params['sign'] = self._generate_signature(params)
        
        full_url = f"{self.api_url}?{urlencode(params)}"
        logger.info(f"Executando requisição para a URL: {full_url}")

        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Log da resposta completa para depuração final
            logger.info(f"Resposta completa da API AliExpress: {data}")

            # Verifica se a resposta contém o erro de IP
            if 'error_response' in data:
                error_info = data['error_response']
                logger.error(f"Erro da API AliExpress: Código {error_info.get('code')}, Mensagem: {error_info.get('msg')}")
                return False

            # Processa a resposta de sucesso
            result = data.get('aliexpress_affiliate_product_query_response', {}).get('resp_result', {}).get('result', {})
            products = result.get('products', {}).get('product', [])
            
            if not products:
                logger.warning("A busca foi bem-sucedida, mas nenhum produto foi retornado.")
                return []
            
            return products

        except requests.exceptions.RequestException as e:
            logger.error(f"Exceção na requisição para a API do AliExpress: {e}")
            return False
