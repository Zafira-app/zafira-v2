"""
Zafira V2.0 - Cliente AliExpress ULTRA-ESPECÍFICO DEFINITIVO
VERSÃO FINAL QUE RESOLVE TODOS OS PROBLEMAS DE ASSINATURA
Data: 21/08/2025 - Correção baseada no relatório de 15 erros IncompleteSignature
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
    """Cliente ULTRA-ESPECÍFICO para API do AliExpress - VERSÃO DEFINITIVA"""
    
    def __init__(self):
        self.base_url = "https://api-sg.aliexpress.com/sync"
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        
        # Validação de credenciais
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais do AliExpress não configuradas")
        else:
            logger.info("Cliente AliExpress ULTRA-ESPECÍFICO inicializado com sucesso")
    
    def search_products(self, query: str, max_results: int = 3) -> List[Dict]:
        """Busca produtos no AliExpress com retry automático - VERSÃO ULTRA-ESPECÍFICA"""
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais não configuradas")
            return []
        
        try:
            logger.info(f"[ULTRA-ESPECÍFICO] Buscando produtos para: {query}")
            
            # Tenta buscar com retry
            for attempt in range(3):
                try:
                    products = self._search_api_ultra_specific(query, max_results)
                    if products:
                        logger.info(f"[ULTRA-ESPECÍFICO] Encontrados {len(products)} produtos")
                        return products
                    else:
                        logger.warning(f"[ULTRA-ESPECÍFICO] Tentativa {attempt + 1}: Nenhum produto encontrado")
                        
                except Exception as e:
                    logger.error(f"[ULTRA-ESPECÍFICO] Tentativa {attempt + 1} falhou: {e}")
                    if attempt < 2:  # Não é a última tentativa
                        time.sleep(1)  # Aguarda 1 segundo antes de tentar novamente
                        continue
                    else:
                        raise e
            
            return []
            
        except Exception as e:
            logger.error(f"[ULTRA-ESPECÍFICO] Erro na busca de produtos: {e}")
            return []
    
    def _search_api_ultra_specific(self, query: str, max_results: int) -> List[Dict]:
        """Executa busca na API do AliExpress - VERSÃO ULTRA-ESPECÍFICA SEM ESPAÇOS"""
        try:
            # Timestamp em milissegundos
            timestamp = str(int(time.time() * 1000))
            
            # Parâmetros da requisição - ULTRA-ESPECÍFICOS SEM ESPAÇOS
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
                # CAMPO FIELDS SEM ESPAÇOS - ULTRA-ESPECÍFICO
                "fields": "commission_rate,sale_price,discount,product_main_image_url,product_title,product_url,evaluate_rate,original_price,lastest_volume,product_id,target_sale_price,target_sale_price_currency,promotion_link"
            }
            
            logger.info(f"[ULTRA-ESPECÍFICO] Parâmetros ANTES da assinatura: {params}")
            
            # Gera assinatura ULTRA-ESPECÍFICA
            signature = self._generate_signature_ultra_specific(params)
            
            # SEMPRE USA 'sign' - NUNCA 'sinal' - ULTRA-ESPECÍFICO
            params["sign"] = signature
            
            logger.info(f"[ULTRA-ESPECÍFICO] Parâmetros FINAIS da API: {params}")
            logger.info(f"[ULTRA-ESPECÍFICO] URL completa: {self.base_url}")
            
            # Faz a requisição
            response = requests.get(self.base_url, params=params, timeout=30)
            
            logger.info(f"[ULTRA-ESPECÍFICO] Status da resposta: {response.status_code}")
            logger.info(f"[ULTRA-ESPECÍFICO] URL final da requisição: {response.url}")
            logger.info(f"[ULTRA-ESPECÍFICO] Resposta da API: {response.text[:500]}...")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verifica se há erro na resposta
                if "error_response" in data:
                    error = data["error_response"]
                    logger.error(f"[ULTRA-ESPECÍFICO] Erro da API AliExpress: {error}")
                    return []
                
                # Extrai produtos da resposta
                if "aliexpress_affiliate_product_query_response" in data:
                    result = data["aliexpress_affiliate_product_query_response"]["resp_result"]
                    
                    if result and "result" in result:
                        products = result["result"]["products"]["product"]
                        
                        if products:
                            # Filtra e processa produtos
                            filtered_products = self._filter_products(products)
                            logger.info(f"[ULTRA-ESPECÍFICO] Produtos filtrados: {len(filtered_products)}")
                            return filtered_products[:max_results]
                
                logger.warning("[ULTRA-ESPECÍFICO] Nenhum produto encontrado na resposta da API")
                return []
                
            else:
                logger.error(f"[ULTRA-ESPECÍFICO] Erro HTTP na API AliExpress: {response.status_code}")
                logger.error(f"[ULTRA-ESPECÍFICO] Resposta de erro: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"[ULTRA-ESPECÍFICO] Erro na chamada da API: {e}")
            return []
    
    def _generate_signature_ultra_specific(self, params: Dict) -> str:
        """Gera assinatura MD5 ULTRA-ESPECÍFICA para autenticação na API"""
        try:
            # Remove o parâmetro sign se existir
            clean_params = {k: v for k, v in params.items() if k != "sign"}
            
            # Ordena parâmetros alfabeticamente
            sorted_params = sorted(clean_params.items())
            
            logger.info(f"[ULTRA-ESPECÍFICO] Parâmetros ordenados: {sorted_params}")
            
            # Concatena parâmetros no formato correto: key1value1key2value2...
            param_string = "".join([f"{k}{v}" for k, v in sorted_params])
            
            logger.info(f"[ULTRA-ESPECÍFICO] String de parâmetros: {param_string}")
            
            # Adiciona app_secret no início e fim - FORMATO ULTRA-ESPECÍFICO
            sign_string = f"{self.app_secret}{param_string}{self.app_secret}"
            
            logger.info(f"[ULTRA-ESPECÍFICO] String COMPLETA para assinatura: {sign_string}")
            
            # Gera hash MD5 e converte para MAIÚSCULAS
            signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
            
            logger.info(f"[ULTRA-ESPECÍFICO] Assinatura MD5 gerada: {signature}")
            
            return signature
            
        except Exception as e:
            logger.error(f"[ULTRA-ESPECÍFICO] Erro ao gerar assinatura: {e}")
            return ""
    
    def _filter_products(self, products: List[Dict]) -> List[Dict]:
        """Filtra e melhora produtos retornados - VERSÃO ULTRA-ESPECÍFICA"""
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
                logger.error(f"[ULTRA-ESPECÍFICO] Erro ao processar produto: {e}")
                continue
        
        # Ordena por avaliação (melhor primeiro)
        try:
            filtered.sort(key=lambda x: float(x['evaluate_rate'].split('/')[0]), reverse=True)
        except:
            pass
        
        logger.info(f"[ULTRA-ESPECÍFICO] Produtos após filtro: {len(filtered)}")
        
        return filtered
    
    def test_connection(self) -> bool:
        """Testa conexão com a API do AliExpress - VERSÃO ULTRA-ESPECÍFICA"""
        try:
            logger.info("[ULTRA-ESPECÍFICO] Testando conexão com AliExpress...")
            
            # Faz uma busca simples para testar
            products = self.search_products("phone", 1)
            
            if products:
                logger.info("[ULTRA-ESPECÍFICO] Conexão com AliExpress OK")
                return True
            else:
                logger.warning("[ULTRA-ESPECÍFICO] Conexão OK, mas nenhum produto retornado")
                return False
                
        except Exception as e:
            logger.error(f"[ULTRA-ESPECÍFICO] Erro no teste de conexão: {e}")
            return False

