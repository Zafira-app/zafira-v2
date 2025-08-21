import os
import requests
import hashlib
import time
import logging
from typing import Optional, List, Dict, Any
import urllib.parse

logger = logging.getLogger(__name__)

class AliExpressClient:
    """Cliente para interagir com a API do AliExpress Affiliate - VERSÃO OFICIAL."""
    
    def __init__(self):
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET") 
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        self.api_url = "https://api-sg.aliexpress.com/sync"
        
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress OFICIAL inicializado com sucesso")

    def search_products(self, keywords: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Busca produtos no AliExpress usando palavras-chave."""
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Não é possível buscar produtos, credenciais ausentes.")
            return []

        for attempt in range(max_retries):
            try:
                logger.info(f"[OFICIAL] Tentativa {attempt + 1}: Buscando produtos para: {keywords}")
                
                # Timestamp atual em milissegundos
                timestamp = str(int(time.time() * 1000))
                
                # Parâmetros da API - EXATAMENTE como na documentação oficial
                params = {
                    'app_key': self.app_key,
                    'format': 'json',
                    'method': 'aliexpress.affiliate.product.query',
                    'sign_method': 'md5',
                    'timestamp': timestamp,
                    'v': '2.0',
                    'keywords': keywords,
                    'page_size': '6',
                    'ship_to_country': 'BR',
                    'sort': 'SALE_PRICE_ASC',
                    'target_currency': 'BRL',
                    'target_language': 'PT',
                    'tracking_id': self.tracking_id,
                    'fields': 'commission_rate,sale_price,discount,product_main_image_url,product_title,product_url,evaluate_rate,original_price,lastest_volume,product_id,target_sale_price,target_sale_price_currency,promotion_link'
                }
                
                # Gerar assinatura seguindo documentação oficial
                signature = self._generate_signature_official(params)
                params['sign'] = signature
                
                logger.info(f"[OFICIAL] Fazendo requisição para API")
                logger.info(f"[OFICIAL] Timestamp: {timestamp}")
                logger.info(f"[OFICIAL] Assinatura: {signature}")
                
                # Fazer requisição
                response = requests.get(self.api_url, params=params, timeout=30)
                
                logger.info(f"[OFICIAL] Status da resposta: {response.status_code}")
                logger.info(f"[OFICIAL] URL da requisição: {response.url}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"[OFICIAL] Resposta recebida: {str(data)[:200]}...")
                    
                    # Verificar se há erro na resposta
                    if 'error_response' in data:
                        error_info = data['error_response']
                        logger.error(f"[OFICIAL] Erro da API AliExpress: {error_info}")
                        
                        # Se for erro de assinatura, tentar novamente
                        if error_info.get('code') == 'IncompleteSignature':
                            logger.warning(f"[OFICIAL] Tentativa {attempt + 1}: Erro de assinatura, tentando novamente...")
                            time.sleep(1)
                            continue
                        else:
                            logger.error(f"[OFICIAL] Erro não relacionado à assinatura: {error_info}")
                            return []
                    
                    # Processar resposta de sucesso
                    if 'aliexpress_affiliate_product_query_response' in data:
                        query_response = data['aliexpress_affiliate_product_query_response']
                        
                        if 'resp_result' in query_response:
                            resp_result = query_response['resp_result']
                            
                            if 'result' in resp_result and 'products' in resp_result['result']:
                                products = resp_result['result']['products']
                                logger.info(f"[OFICIAL] Encontrados {len(products)} produtos")
                                return products
                            else:
                                logger.warning("[OFICIAL] Nenhum produto encontrado na resposta")
                                return []
                        else:
                            logger.warning("[OFICIAL] Estrutura de resposta inesperada")
                            return []
                    else:
                        logger.warning("[OFICIAL] Resposta não contém dados de produtos")
                        return []
                else:
                    logger.error(f"[OFICIAL] Erro HTTP: {response.status_code}")
                    logger.error(f"[OFICIAL] Resposta: {response.text}")
                    return []
                    
            except Exception as e:
                logger.error(f"[OFICIAL] Exceção na tentativa {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    return []
        
        logger.error(f"[OFICIAL] Todas as {max_retries} tentativas falharam")
        return []

    def _generate_signature_official(self, params: Dict[str, str]) -> str:
        """
        Gera a assinatura MD5 seguindo EXATAMENTE a documentação oficial do AliExpress.
        
        Algoritmo oficial:
        1. Ordenar parâmetros alfabeticamente (excluindo 'sign')
        2. Concatenar como: key1value1key2value2...
        3. Adicionar app_secret no início e fim: app_secret + params_string + app_secret
        4. Calcular MD5 e converter para maiúsculo
        """
        
        # 1. Filtrar e ordenar parâmetros (excluindo 'sign' se existir)
        filtered_params = {k: v for k, v in params.items() if k != 'sign'}
        sorted_items = sorted(filtered_params.items())
        
        logger.info(f"[OFICIAL] Parâmetros ordenados: {sorted_items}")
        
        # 2. Concatenar parâmetros: key1value1key2value2...
        param_string = ''.join([f'{k}{v}' for k, v in sorted_items])
        
        logger.info(f"[OFICIAL] String de parâmetros: {param_string}")
        
        # 3. Adicionar app_secret no início e fim
        sign_string = f'{self.app_secret}{param_string}{self.app_secret}'
        
        logger.info(f"[OFICIAL] String completa para assinatura: {sign_string}")
        
        # 4. Calcular MD5 e converter para maiúsculo
        signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
        
        logger.info(f"[OFICIAL] Assinatura MD5 final: {signature}")
        
        return signature

