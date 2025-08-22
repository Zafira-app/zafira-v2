# aliexpress_client.py - VERSÃO FINAL COM FLUXO DE AUTENTICAÇÃO DE TOKEN

import requests
import hashlib
import time
import logging
import os
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class AliExpressClient:
    """
    Cliente para interagir com a API do AliExpress, implementando o fluxo de 
    autenticação de duas etapas com Access Token, conforme a documentação oficial.
    """
    def __init__(self):
        self.api_url = "https://api-sg.aliexpress.com/sync"
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY" )
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        
        # Variáveis para gerenciar o Access Token
        self.access_token = None
        self.token_expiry_time = 0

        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais críticas do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress (com fluxo de Access Token) inicializado.")

    def _generate_signature(self, params: dict) -> str:
        """Gera a assinatura SHA256 para uma dada lista de parâmetros."""
        sorted_params = sorted(params.items())
        concatenated_string = "".join([f"{k}{v}" for k, v in sorted_params])
        string_to_sign = self.app_secret + concatenated_string + self.app_secret
        signature = hashlib.sha256(string_to_sign.encode('utf-8')).hexdigest().upper()
        return signature

    def _get_access_token(self) -> str | None:
        """
        Busca um novo Access Token da API /auth/token/security/create.
        Esta é a Etapa 1 do fluxo de autenticação.
        """
        logger.info("Verificando a validade do Access Token...")
        # Se o token atual ainda for válido (com uma margem de 5 minutos), reutilize-o.
        if self.access_token and time.time() < self.token_expiry_time - 300:
            logger.info("Reutilizando Access Token existente.")
            return self.access_token

        logger.info("Access Token expirado ou inexistente. Buscando um novo...")
        
        params = {
            'app_key': self.app_key,
            'method': '/auth/token/security/create',
            'sign_method': 'sha256',
            'timestamp': str(int(time.time() * 1000)),
            'code': self.app_key # A documentação sugere usar o app_key como 'code'
        }
        params['sign'] = self._generate_signature(params)

        try:
            response = requests.get(self.api_url, params=params, timeout=20)
            data = response.json()
            logger.info(f"Resposta da API de Token: {data}")

            if 'error_response' in data:
                logger.error(f"Falha ao obter Access Token: {data['error_response']}")
                return None

            token_data = data.get('aliexpress_authtoken_security_create_response', {}).get('token_result', {})
            self.access_token = token_data.get('access_token')
            
            # Define o tempo de expiração (expire_time é em segundos)
            expire_in = int(token_data.get('expire_time', 0))
            self.token_expiry_time = time.time() + expire_in
            
            logger.info(f"Novo Access Token obtido com sucesso. Válido por {expire_in / 3600:.2f} horas.")
            return self.access_token

        except Exception as e:
            logger.error(f"Exceção ao buscar Access Token: {e}")
            return None

    def search_products(self, keywords: str, limit: int = 3) -> list | bool:
        """
        Busca produtos na API, garantindo primeiro a obtenção de um Access Token válido.
        Esta é a Etapa 2 do fluxo de autenticação.
        """
        # Etapa 1: Garante que temos um token
        token = self._get_access_token()
        if not token:
            logger.error("Não foi possível continuar a busca sem um Access Token.")
            return False

        # Etapa 2: Prepara e executa a busca de produtos
        params = {
            'app_key': self.app_key,
            'method': 'aliexpress.affiliate.product.query',
            'sign_method': 'sha256',
            'timestamp': str(int(time.time() * 1000)),
            'access_token': token, # PARÂMETRO CRUCIAL ADICIONADO
            'keywords': keywords,
            'tracking_id': self.tracking_id,
            'page_size': str(limit),
            'target_language': 'PT',
            'target_currency': 'BRL',
            'ship_to_country': 'BR'
        }
        params['sign'] = self._generate_signature(params)

        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            data = response.json()
            logger.info(f"Resposta da API de Produtos: {data}")

            if 'error_response' in data:
                error_info = data['error_response']
                logger.error(f"Erro da API de Produtos: Código {error_info.get('code')}, Mensagem: {error_info.get('msg')}")
                return False

            result = data.get('aliexpress_affiliate_product_query_response', {}).get('resp_result', {}).get('result', {})
            products = result.get('products', {}).get('product', [])
            
            return products

        except Exception as e:
            logger.error(f"Exceção na busca de produtos: {e}")
            return False
