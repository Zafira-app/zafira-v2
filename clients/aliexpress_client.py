import os
import requests
import hashlib
import time
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class AliExpressClient:
    """Cliente baseado EXATAMENTE na URL que funcionou no painel oficial."""
    
    def __init__(self):
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET") 
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        self.api_url = "https://api-sg.aliexpress.com/sync"
        
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress EXATO PAINEL inicializado com sucesso")

    def search_products(self, keywords: str, max_retries: int = 1) -> List[Dict[str, Any]]:
        """Busca produtos usando EXATAMENTE os parâmetros que funcionaram no painel."""
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Não é possível buscar produtos, credenciais ausentes.")
            return []

        try:
            logger.info(f"[PAINEL] Buscando produtos para: {keywords}")
            
            # Timestamp atual em milissegundos
            timestamp = str(int(time.time() * 1000))
            
            # Parâmetros EXATOS da URL que funcionou no painel:
            # https://api-sg.aliexpress.com/sync?min_sale_price=15&keywords=celular&target_currency=BRL&target_language=PT&delivery_days=3&page_no=1&sort=SALE_PRICE_ASC&ship_to_country=BR&app_signature=asdasdasdsa&platform_product_type=ALL&promotion_name=Business+Top+Sellers+with+Exclusive+Price&max_sale_price=100&category_ids=111%2C222%2C333&fields=commission_rate%2Csale_price&tracking_id=zafira&page_size=6&method=aliexpress.affiliate.product.query&app_key=518284&sign_method=sha256&timestamp=1755813243788&sign=6B209D0C611F4CB0ADCAD94BC9B9105A2DAD15DE9344A8146A89CEE7BEDF8762
            
            params = {
                'method': 'aliexpress.affiliate.product.query',
                'app_key': self.app_key,
                'sign_method': 'sha256',
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
                'fields': 'commission_rate,sale_price',  # Só estes campos como no painel
                'min_sale_price': '15',
                'max_sale_price': '100',
                'delivery_days': '3',
                'app_signature': 'asdasdasdsa',  # Exato como no painel
                'category_ids': '111,222,333',  # Exato como no painel
                'promotion_name': 'Business Top Sellers with Exclusive Price'  # Exato como no painel
            }
            
            # Gerar assinatura SHA256
            signature = self._generate_signature_sha256(params)
            params['sign'] = signature
            
            logger.info(f"[PAINEL] Fazendo requisição para API")
            logger.info(f"[PAINEL] Timestamp: {timestamp}")
            logger.info(f"[PAINEL] Assinatura SHA256: {signature}")
            
            # Fazer requisição
            response = requests.get(self.api_url, params=params, timeout=30)
            
            logger.info(f"[PAINEL] Status da resposta: {response.status_code}")
            logger.info(f"[PAINEL] URL completa: {response.url}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[PAINEL] Resposta: {str(data)[:300]}...")
                
                # Verificar se há erro na resposta
                if 'error_response' in data:
                    error_info = data['error_response']
                    logger.error(f"[PAINEL] Erro da API AliExpress: {error_info}")
                    return []
                
                # Processar resposta de sucesso
                if 'aliexpress_affiliate_product_query_response' in data:
                    query_response = data['aliexpress_affiliate_product_query_response']
                    
                    if 'resp_result' in query_response:
                        resp_result = query_response['resp_result']
                        
                        if 'result' in resp_result and 'products' in resp_result['result']:
                            products = resp_result['result']['products']
                            logger.info(f"[PAINEL] SUCESSO! Encontrados {len(products)} produtos")
                            
                            # Processar produtos para formato esperado
                            processed_products = []
                            if 'product' in products:
                                for product in products['product']:
                                    processed_product = {
                                        'product_title': product.get('product_title', 'Produto sem título'),
                                        'target_sale_price': f"R$ {product.get('target_sale_price', '0')}",
                                        'evaluate_rate': product.get('evaluate_rate', '0%'),
                                        'promotion_link': product.get('promotion_link', ''),
                                        'product_main_image_url': product.get('product_main_image_url', ''),
                                        'commission_rate': product.get('commission_rate', '0%')
                                    }
                                    processed_products.append(processed_product)
                            
                            return processed_products
                        else:
                            logger.warning("[PAINEL] Nenhum produto encontrado na resposta")
                            return []
                    else:
                        logger.warning("[PAINEL] Estrutura de resposta inesperada")
                        return []
                else:
                    logger.warning("[PAINEL] Resposta não contém dados de produtos")
                    return []
            else:
                logger.error(f"[PAINEL] Erro HTTP: {response.status_code}")
                logger.error(f"[PAINEL] Resposta: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"[PAINEL] Exceção: {e}")
            return []
        
        return []

    def _generate_signature_sha256(self, params: Dict[str, str]) -> str:
        """
        Gera a assinatura SHA256 EXATAMENTE como o painel oficial faz.
        """
        
        # 1. Remover 'sign' se existir
        filtered_params = {k: v for k, v in params.items() if k != 'sign'}
        
        # 2. Ordenar alfabeticamente
        sorted_items = sorted(filtered_params.items())
        
        logger.info(f"[PAINEL] Parâmetros ordenados: {sorted_items}")
        
        # 3. Concatenar como: key1value1key2value2...
        param_string = ''.join([f'{k}{v}' for k, v in sorted_items])
        
        logger.info(f"[PAINEL] String de parâmetros: {param_string}")
        
        # 4. Adicionar app_secret no início e fim
        sign_string = f'{self.app_secret}{param_string}{self.app_secret}'
        
        logger.info(f"[PAINEL] String completa para assinatura: {sign_string}")
        
        # 5. Calcular SHA256 e converter para maiúsculo
        signature = hashlib.sha256(sign_string.encode('utf-8')).hexdigest().upper()
        
        logger.info(f"[PAINEL] Assinatura SHA256 final: {signature}")
        
        return signature

