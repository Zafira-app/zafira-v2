import os
import requests
import hashlib
import time
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class AliExpressClient:
    """Cliente para interagir com a API do AliExpress Affiliate - VERSÃO SHA256 CORRETA."""
    
    def __init__(self):
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET") 
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        self.api_url = "https://api-sg.aliexpress.com/sync"
        
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress SHA256 CORRETO inicializado com sucesso")

    def search_products(self, keywords: str, max_retries: int = 1) -> List[Dict[str, Any]]:
        """Busca produtos no AliExpress usando palavras-chave."""
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Não é possível buscar produtos, credenciais ausentes.")
            return []

        try:
            logger.info(f"[SHA256] Buscando produtos para: {keywords}")
            
            # Timestamp atual em milissegundos
            timestamp = str(int(time.time() * 1000))
            
            # Parâmetros EXATOS baseados na URL oficial do painel
            params = {
                'method': 'aliexpress.affiliate.product.query',
                'app_key': self.app_key,
                'sign_method': 'sha256',  # SHA256, não MD5!
                'timestamp': timestamp,
                'keywords': keywords,
                'target_currency': 'BRL',
                'target_language': 'PT',
                'ship_to_country': 'BR',
                'tracking_id': self.tracking_id,
                'page_size': '6',
                'page_no': '1',
                'sort': 'SALE_PRICE_ASC',
                'platform_product_type': 'ALL',
                'fields': 'commission_rate,sale_price,discount,product_main_image_url,product_title,product_url,evaluate_rate,original_price,lastest_volume,product_id,target_sale_price,target_sale_price_currency,promotion_link',
                'min_sale_price': '1',
                'max_sale_price': '1000',
                'delivery_days': '15',
                'app_signature': 'zafira_signature'  # Parâmetro adicional necessário
            }
            
            # Gerar assinatura SHA256
            signature = self._generate_signature_sha256(params)
            params['sign'] = signature
            
            logger.info(f"[SHA256] Fazendo requisição para API")
            logger.info(f"[SHA256] Timestamp: {timestamp}")
            logger.info(f"[SHA256] Assinatura SHA256: {signature}")
            
            # Fazer requisição
            response = requests.get(self.api_url, params=params, timeout=30)
            
            logger.info(f"[SHA256] Status da resposta: {response.status_code}")
            logger.info(f"[SHA256] URL completa: {response.url}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[SHA256] Resposta: {str(data)[:300]}...")
                
                # Verificar se há erro na resposta
                if 'error_response' in data:
                    error_info = data['error_response']
                    logger.error(f"[SHA256] Erro da API AliExpress: {error_info}")
                    return []
                
                # Processar resposta de sucesso
                if 'aliexpress_affiliate_product_query_response' in data:
                    query_response = data['aliexpress_affiliate_product_query_response']
                    
                    if 'resp_result' in query_response:
                        resp_result = query_response['resp_result']
                        
                        if 'result' in resp_result and 'products' in resp_result['result']:
                            products = resp_result['result']['products']
                            logger.info(f"[SHA256] SUCESSO! Encontrados {len(products)} produtos")
                            return products
                        else:
                            logger.warning("[SHA256] Nenhum produto encontrado na resposta")
                            return []
                    else:
                        logger.warning("[SHA256] Estrutura de resposta inesperada")
                        return []
                else:
                    logger.warning("[SHA256] Resposta não contém dados de produtos")
                    return []
            else:
                logger.error(f"[SHA256] Erro HTTP: {response.status_code}")
                logger.error(f"[SHA256] Resposta: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"[SHA256] Exceção: {e}")
            return []
        
        return []

    def _generate_signature_sha256(self, params: Dict[str, str]) -> str:
        """
        Gera a assinatura SHA256 baseada na implementação oficial do painel AliExpress.
        """
        
        # 1. Remover 'sign' se existir
        filtered_params = {k: v for k, v in params.items() if k != 'sign'}
        
        # 2. Ordenar alfabeticamente
        sorted_items = sorted(filtered_params.items())
        
        logger.info(f"[SHA256] Parâmetros ordenados: {sorted_items}")
        
        # 3. Concatenar como: key1value1key2value2...
        param_string = ''.join([f'{k}{v}' for k, v in sorted_items])
        
        logger.info(f"[SHA256] String de parâmetros: {param_string}")
        
        # 4. Adicionar app_secret no início e fim
        sign_string = f'{self.app_secret}{param_string}{self.app_secret}'
        
        logger.info(f"[SHA256] String completa para assinatura: {sign_string}")
        
        # 5. Calcular SHA256 e converter para maiúsculo
        signature = hashlib.sha256(sign_string.encode('utf-8')).hexdigest().upper()
        
        logger.info(f"[SHA256] Assinatura SHA256 final: {signature}")
        
        return signature

