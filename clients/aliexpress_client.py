import os
import requests
import hashlib
import time
import logging
from typing import List, Dict, Any
import urllib.parse

logger = logging.getLogger(__name__)

class AliExpressClient:
    """Cliente para interagir com a API do AliExpress Affiliate - SOLUÇÃO STACKOVERFLOW."""
    
    def __init__(self):
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY")
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        self.api_url = "https://api-sg.aliexpress.com/sync"
        
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress STACKOVERFLOW inicializado com sucesso")
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Gera assinatura MD5 usando a solução exata do Stack Overflow.
        Remove símbolos & e = antes de gerar o hash.
        """
        # Ordena os parâmetros
        sorted_params = sorted(params.items())
        
        # Cria string de parâmetros
        param_string = ""
        for key, value in sorted_params:
            if param_string == "":
                param_string = f"{key}={value}"
            else:
                param_string = f"{param_string}&{key}={value}"
        
        # SOLUÇÃO DO STACKOVERFLOW: Remove & e = da string de assinatura
        sign_string = param_string.replace("&amp;", "")
        sign_string = sign_string.replace("&", "")
        sign_string = sign_string.replace("=", "")
        
        # Gera assinatura MD5
        signature_input = f"{self.app_secret}{sign_string}{self.app_secret}"
        signature = hashlib.md5(signature_input.encode('utf-8')).hexdigest().upper()
        
        logger.info(f"[STACKOVERFLOW] String de parâmetros: {param_string}")
        logger.info(f"[STACKOVERFLOW] String para assinatura (sem & e =): {sign_string}")
        logger.info(f"[STACKOVERFLOW] Input da assinatura: {signature_input}")
        logger.info(f"[STACKOVERFLOW] Assinatura MD5: {signature}")
        
        return signature
    
    def search_products(self, keywords: str, page_size: int = 6) -> List[Dict[str, Any]]:
        """
        Busca produtos usando a API do AliExpress com a solução do Stack Overflow.
        """
        logger.info(f"[STACKOVERFLOW] Buscando produtos para: {keywords}")
        
        # Parâmetros da API
        params = {
            "app_key": self.app_key,
            "format": "json",
            "method": "aliexpress.affiliate.product.query",
            "sign_method": "md5",
            "timestamp": str(int(time.time() * 1000)),
            "keywords": keywords,
            "target_currency": "BRL",
            "target_language": "PT",
            "ship_to_country": "BR",
            "tracking_id": self.tracking_id,
            "page_size": str(page_size),
            "sort": "SALE_PRICE_ASC",
            "fields": "commission_rate,sale_price,discount,product_main_image_url,product_title,product_url,evaluate_rate,original_price,lastest_volume,product_id,target_sale_price,target_sale_price_currency,promotion_link"
        }
        
        # Gera assinatura usando solução do Stack Overflow
        signature = self._generate_signature(params)
        
        # Adiciona assinatura aos parâmetros
        params["sign"] = signature
        
        try:
            # Faz requisição
            logger.info(f"[STACKOVERFLOW] Fazendo requisição para API")
            response = requests.get(self.api_url, params=params, timeout=30)
            
            logger.info(f"[STACKOVERFLOW] Status da resposta: {response.status_code}")
            logger.info(f"[STACKOVERFLOW] URL completa: {response.url}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[STACKOVERFLOW] Resposta: {data}")
                
                # Verifica se há erro na resposta
                if "error_response" in data:
                    error = data["error_response"]
                    logger.error(f"[STACKOVERFLOW] Erro da API AliExpress: {error}")
                    return []
                
                # Extrai produtos da resposta
                if "aliexpress_affiliate_product_query_response" in data:
                    resp_result = data["aliexpress_affiliate_product_query_response"]["resp_result"]
                    if "result" in resp_result and "products" in resp_result["result"]:
                        products = resp_result["result"]["products"]["product"]
                        logger.info(f"[STACKOVERFLOW] {len(products)} produtos encontrados")
                        return self._format_products(products)
                
                logger.warning("[STACKOVERFLOW] Nenhum produto encontrado na resposta")
                return []
            else:
                logger.error(f"[STACKOVERFLOW] Erro HTTP: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"[STACKOVERFLOW] Erro na requisição: {str(e)}")
            return []
    
    def _format_products(self, products: List[Dict]) -> List[Dict[str, Any]]:
        """Formata produtos para exibição."""
        formatted_products = []
        
        for product in products:
            try:
                formatted_product = {
                    "title": product.get("product_title", "Produto sem título"),
                    "price": f"R$ {product.get('target_sale_price', '0')}",
                    "original_price": f"R$ {product.get('target_original_price', '0')}",
                    "discount": product.get("discount", "0%"),
                    "rating": product.get("evaluate_rate", "N/A"),
                    "sales": product.get("lastest_volume", 0),
                    "commission": product.get("commission_rate", "0%"),
                    "image_url": product.get("product_main_image_url", ""),
                    "product_url": product.get("promotion_link", product.get("product_detail_url", ""))
                }
                formatted_products.append(formatted_product)
            except Exception as e:
                logger.error(f"Erro ao formatar produto: {e}")
                continue
        
        return formatted_products

