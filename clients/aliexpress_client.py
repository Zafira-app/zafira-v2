import os
import requests
import hashlib
import time
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class AliExpressClient:
    """Cliente para interagir com a API do AliExpress Affiliate."""
    
    def __init__(self):
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET") 
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        self.api_url = "https://api-sg.aliexpress.com/sync"
        
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress DEFINITIVO inicializado com sucesso")

    def search_products(self, keywords: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Busca produtos no AliExpress usando palavras-chave."""
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Não é possível buscar produtos, credenciais ausentes.")
            return []

        for attempt in range(max_retries):
            try:
                logger.info(f"[DEFINITIVO] Tentativa {attempt + 1}: Buscando produtos para: {keywords}")
                
                # Timestamp atual em milissegundos
                timestamp = str(int(time.time() * 1000))
                
                # Parâmetros da API - SEM ESPAÇOS EXTRAS
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
                
                # Gerar assinatura
                signature = self._generate_signature(params)
                params['sign'] = signature
                
                logger.info(f"[DEFINITIVO] Fazendo requisição para API com {len(params)} parâmetros")
                
                # Fazer requisição
                response = requests.get(self.api_url, params=params, timeout=30)
                
                logger.info(f"[DEFINITIVO] Status da resposta: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verificar se há erro na resposta
                    if 'error_response' in data:
                        error_info = data['error_response']
                        logger.error(f"[DEFINITIVO] Erro da API AliExpress: {error_info}")
                        
                        # Se for erro de assinatura, tentar novamente
                        if error_info.get('code') == 'IncompleteSignature':
                            logger.warning(f"[DEFINITIVO] Tentativa {attempt + 1}: Erro de assinatura, tentando novamente...")
                            time.sleep(1)  # Aguardar 1 segundo antes de tentar novamente
                            continue
                        else:
                            logger.error(f"[DEFINITIVO] Erro não relacionado à assinatura: {error_info}")
                            return []
                    
                    # Processar resposta de sucesso
                    if 'aliexpress_affiliate_product_query_response' in data:
                        query_response = data['aliexpress_affiliate_product_query_response']
                        
                        if 'resp_result' in query_response:
                            resp_result = query_response['resp_result']
                            
                            if 'result' in resp_result and 'products' in resp_result['result']:
                                products = resp_result['result']['products']
                                logger.info(f"[DEFINITIVO] Encontrados {len(products)} produtos")
                                return products
                            else:
                                logger.warning("[DEFINITIVO] Nenhum produto encontrado na resposta")
                                return []
                        else:
                            logger.warning("[DEFINITIVO] Estrutura de resposta inesperada")
                            return []
                    else:
                        logger.warning("[DEFINITIVO] Resposta não contém dados de produtos")
                        return []
                else:
                    logger.error(f"[DEFINITIVO] Erro HTTP: {response.status_code}")
                    return []
                    
            except Exception as e:
                logger.error(f"[DEFINITIVO] Exceção na tentativa {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Aguardar 2 segundos antes de tentar novamente
                    continue
                else:
                    return []
        
        logger.error(f"[DEFINITIVO] Todas as {max_retries} tentativas falharam")
        return []

    def _generate_signature(self, params: Dict[str, str]) -> str:
        """Gera a assinatura MD5 para a API do AliExpress."""
        # Ordenar parâmetros alfabeticamente (excluindo 'sign' se existir)
        sorted_params = sorted([(k, v) for k, v in params.items() if k != 'sign'])
        
        # Criar string de parâmetros
        param_string = ''.join([f'{k}{v}' for k, v in sorted_params])
        
        # Adicionar app_secret no início e no fim
        sign_string = f'{self.app_secret}{param_string}{self.app_secret}'
        
        # Gerar hash MD5
        signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
        
        logger.info(f"[DEFINITIVO] Assinatura gerada com sucesso")
        
        return signature

