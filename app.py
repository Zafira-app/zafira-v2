# app.py - VERSÃO FINAL (Assinatura Corrigida para API Affiliate)

import os
import json
import logging
import re
import requests
import hashlib
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ... (As classes WhatsAppClient e ZafiraCore e o servidor Flask continuam iguais) ...
# A única mudança está na função _generate_signature dentro da classe AliExpressClient.

# ==============================================================================
# CLASSE DO CLIENTE ALIEXPRESS (COM A CORREÇÃO)
# ==============================================================================
class AliExpressClient:
    def __init__(self):
        self.api_url = "https://api-sg.aliexpress.com/sync"
        self.app_key = os.getenv("ALIEXPRESS_APP_KEY" )
        self.app_secret = os.getenv("ALIEXPRESS_APP_SECRET")
        self.tracking_id = os.getenv("ALIEXPRESS_TRACKING_ID")
        if not all([self.app_key, self.app_secret, self.tracking_id]):
            logger.error("Credenciais críticas do AliExpress não configuradas!")
        else:
            logger.info("Cliente AliExpress (API Affiliate com Assinatura Corrigida) inicializado.")

    def _generate_signature(self, params: dict) -> str:
        """
        Gera a assinatura SHA256 para a API affiliate.
        AQUI ESTÁ A CORREÇÃO FINAL: A string é montada apenas com a concatenação
        de chaves e valores, sem o nome da chave na frente.
        """
        sorted_params = sorted(params.items())
        
        # CORREÇÃO: Monta a string como "app_keyXXXXkeywordsYYYY..."
        concatenated_string = "".join([f"{k}{v}" for k, v in sorted_params])
        
        # A fórmula de envolver com o secret continua a mesma
        string_to_sign = self.app_secret + concatenated_string + self.app_secret
        
        signature = hashlib.sha256(string_to_sign.encode('utf-8')).hexdigest().upper()
        logger.info(f"String para assinar (ocultando secret): app_secret+{concatenated_string}+app_secret")
        logger.info(f"Assinatura gerada: {signature}")
        return signature

    def search_products(self, keywords: str, limit: int = 3) -> list | bool:
        params = {
            'app_key': self.app_key,
            'method': 'aliexpress.affiliate.product.query',
            'sign_method': 'sha256',
            'timestamp': str(int(time.time() * 1000)),
            'keywords': keywords,
            'tracking_id': self.tracking_id,
            'page_size': str(limit),
            'target_language': 'pt',
            'target_currency': 'BRL',
            'ship_to_country': 'BR'
        }
        params['sign'] = self._generate_signature(params)
        
        try:
            response = requests.post(self.api_url, params=params, timeout=40)
            logger.info(f"Resposta da API - Status: {response.status_code}, Texto: {response.text[:500]}")
            response.raise_for_status()
            data = response.json()
            if 'error_response' in data:
                error_info = data['error_response']
                logger.error(f"Erro da API AliExpress: Código {error_info.get('code')}, Mensagem: {error_info.get('msg')}")
                return False
            result = data.get('aliexpress_affiliate_product_query_response', {}).get('resp_result', {}).get('result', {})
            products = result.get('products', {}).get('product', [])
            return products
        except Exception as e:
            logger.error(f"Exceção na busca de produtos: {e}", exc_info=True)
            return False

# ==============================================================================
# COLE O RESTANTE DO SEU CÓDIGO (ZafiraCore, WhatsAppClient, Flask) AQUI
# ...
# ==============================================================================
