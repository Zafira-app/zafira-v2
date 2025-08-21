"""
Zafira V2.0 - Cliente AliExpress FINAL CORRIGIDO
Integração robusta com a API oficial do AliExpress
"""

import requests
import hashlib
import time
import os
import logging
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class AliExpressClient:
    """Cliente robusto para API do AliExpress"""
    
    def __init__(self):
        self.base_url = "https://api-sg.aliexpress.com/sync"
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        
        # Validação de credenciais
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais do AliExpress não configuradas")
        else:
            logger.info("Cliente AliExpress inicializado com sucesso")
    
    def search_products(self, query: str, max_results: int = 3) -> List[Dict]:
        """Busca produtos no AliExpress com retry automático"""
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais não configuradas")
            return []
        
        try:
            logger.info(f"Buscando produtos para: {query}")
            
            # Tenta buscar com retry
            for attempt in range(3):
                try:
                    products = self._search_api(query, max_results)
                    if products:
                        logger.info(f"Encontrados {len(products)} produtos")
                        return products
                    else:
                        logger.warning(f"Tentativa {attempt + 1}: Nenhum produto encontrado")
                        
                except Exception as e:
                    logger.error(f"Tentativa {attempt + 1} falhou: {e}")
                    if attempt < 2:  # Não é a última tentativa
                        time.sleep(1)  # Aguarda 1 segundo antes de tentar novamente
                        continue
                    else:
                        raise e
            
            return []
            
        except Exception as e:
            logger.error(f"Erro na busca de produtos: {e}")
            return []
    
    def _search_api(self, query: str, max_results: int) -> List[Dict]:
        """Executa busca na API do AliExpress"""
        try:
            # Parâmetros da requisição - FORMATO FINAL CORRETO
            timestamp = str(int(time.time() * 1000))
            
            params = {
                "app_key": self.app_key,
                "format": "json",
                "method": "aliexpress.affiliate.product.query",
                "sign_method": "md5",
                "timestamp": timestamp,
                "v": "2.0",
                "keywords": query,
                "page_size": str(max_results * 2),
                "ship_to_country": "BR",
                "sort": "SALE_PRICE_ASC",
                "target_currency": "BRL",
                "target_language": "PT",
                "tracking_id": self.tracking_id,
                "fields": "commission_rate,sale_price,discount,product_main_image_url,product_title,product_url,evaluate_rate,original_price,lastest_volume,product_id,target_sale_price,target_sale_price_currency,promotion_link"
            }
            
            # Gera assinatura FINAL CORRETA
            signature = self._generate_signature(params)
            params["sign"] = signature
            
            logger.info(f"Parâmetros finais da API: {params}")
            
            # Faz a requisição
            response = requests.get(self.base_url, params=params, timeout=30)
            
            logger.info(f"Status da resposta: {response.status_code}")
            logger.info(f"Resposta da API: {response.text[:500]}...")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verifica se há erro na resposta
                if "error_response" in data:
                    error = data["error_response"]
                    logger.error(f"Erro da API AliExpress: {error}")
                    return []
                
                # Extrai produtos da resposta
                if "aliexpress_affiliate_product_query_response" in data:
                    result = data["aliexpress_affiliate_product_query_response"]["resp_result"]
                    
                    if result and "result" in result:
                        products = result["result"]["products"]["product"]
                        
                        if products:
                            # Filtra e processa produtos
                            filtered_products = self._filter_products(products)
                            return filtered_products[:max_results]
                
                logger.warning("Nenhum produto encontrado na resposta da API")
                return []
                
            else:
                logger.error(f"Erro HTTP na API AliExpress: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erro na chamada da API: {e}")
            return []
    
    def _generate_signature(self, params: Dict) -> str:
        """Gera assinatura MD5 FINAL CORRETA para autenticação na API"""
        try:
            # Remove o parâmetro sign se existir
            clean_params = {k: v for k, v in params.items() if k != "sign"}
            
            # Ordena parâmetros alfabeticamente
            sorted_params = sorted(clean_params.items())
            
            # Concatena parâmetros no formato correto: key1value1key2value2...
            param_string = "".join([f"{k}{v}" for k, v in sorted_params])
            
            # Adiciona app_secret no início e fim - FORMATO FINAL CORRETO
            sign_string = f"{self.app_secret}{param_string}{self.app_secret}"
            
            logger.info(f"String final para assinatura: {sign_string[:100]}...")
            
            # Gera hash MD5 e converte para MAIÚSCULAS
            signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
            
            logger.info(f"Assinatura final gerada: {signature}")
            
            return signature
            
        except Exception as e:
            logger.error(f"Erro ao gerar assinatura: {e}")
            return ""
    
    def _filter_products(self, products: List[Dict]) -> List[Dict]:
        """Filtra e melhora produtos retornados"""
        filtered = []
        
        for product in products:
            try:
                # Verifica se tem informações essenciais
                if not product.get('product_title') or not product.get('promotion_link'):
                    continue
                
                # Verifica se tem preço válido
                price = product.get('target_sale_price')
                if not price or price == '0.00':
                    continue
                
                # Verifica se tem avaliação mínima
                rating = product.get('evaluate_rate', '0')
                try:
                    rating_float = float(rating)
                    if rating_float < 3.0:  # Só produtos com avaliação >= 3.0
                        continue
                except:
                    pass
                
                # Formata dados do produto
                formatted_product = {
                    'product_id': product.get('product_id', ''),
                    'product_title': product.get('product_title', ''),
                    'target_sale_price': f"R$ {price}",
                    'original_price': product.get('target_original_price', ''),
                    'evaluate_rate': f"{rating}/5.0",
                    'commission_rate': product.get('commission_rate', ''),
                    'promotion_link': product.get('promotion_link', ''),
                    'product_main_image_url': product.get('product_main_image_url', ''),
                    'shop_id': product.get('shop_id', ''),
                    'lastest_volume': product.get('lastest_volume', '0')
                }
                
                filtered.append(formatted_product)
                
            except Exception as e:
                logger.error(f"Erro ao processar produto: {e}")
                continue
        
        # Ordena por avaliação (melhor primeiro)
        try:
            filtered.sort(key=lambda x: float(x['evaluate_rate'].split('/')[0]), reverse=True)
        except:
            pass
        
        return filtered
    
    def test_connection(self) -> bool:
        """Testa conexão com a API do AliExpress"""
        try:
            logger.info("Testando conexão com AliExpress...")
            
            # Faz uma busca simples para testar
            products = self.search_products("phone", 1)
            
            if products:
                logger.info("Conexão com AliExpress OK")
                return True
            else:
                logger.warning("Conexão OK, mas nenhum produto retornado")
                return False
                
        except Exception as e:
            logger.error(f"Erro no teste de conexão: {e}")
            return False

