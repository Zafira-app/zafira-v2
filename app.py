import os
import sys
import logging
import time
import json
import hmac
import hashlib
import requests

# Configurações vindas do ambiente (Render)
ALIEXPRESS_APP_KEY = os.getenv("ALIEXPRESS_APP_KEY")
ALIEXPRESS_APP_SECRET = os.getenv("ALIEXPRESS_APP_SECRET")
ALIEXPRESS_TRACKING_ID = os.getenv("ALIEXPRESS_TRACKING_ID")

class AliExpressClient:
    def __init__(self, app_key, app_secret, tracking_id):
        self.app_key = app_key
        self.app_secret = app_secret
        self.tracking_id = tracking_id
        self.api_url = "https://api-sg.aliexpress.com/sync"

    def _generate_signature(self, params: dict) -> str:
        """
        Gera assinatura HMAC-SHA256 no formato exigido pelo AliExpress
        """
        sorted_params = sorted(params.items())
        concatenated_string = "".join(f"{k}{v}" for k, v in sorted_params)
        return hmac.new(
            self.app_secret.encode('utf-8'),
            concatenated_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()

    def search_products(self, keywords: str, limit: int = 3):
        """
        Busca produtos no AliExpress usando a API de afiliados
        """
        params = {
            'app_key': self.app_key,
            'method': 'aliexpress.affiliate.product.query',
            'sign_method': 'hmac',
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),  # UTC correto
            'keywords': keywords,
            'tracking_id': self.tracking_id,
            'page_size': str(limit),
            'target_language': 'pt',
            'target_currency': 'BRL',
            'ship_to_country': 'BR'
        }

        # Gera assinatura
        params['sign'] = self._generate_signature(params)

        # Faz requisição GET
        try:
            response = requests.get(self.api_url, params=params, timeout=40)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

# Função para formatar a resposta para WhatsApp (opcional)
def format_products_for_whatsapp(api_response):
    """
    Recebe o JSON da API e retorna uma string formatada para enviar no WhatsApp
    """
    if "resp_result" not in api_response:
        return "❌ Não foi possível obter produtos no momento."

    products = api_response["resp_result"].get("result", {}).get("products", [])
    if not products:
        return "⚠️ Nenhum produto encontrado para essa busca."

    mensagens = []
    for p in products:
        nome = p.get("product_title", "Produto sem título")
        preco = p.get("target_sale_price", "Preço indisponível")
        link = p.get("promotion_link", p.get("product_detail_url", ""))
        mensagens.append(f"🛒 *{nome}*\n💰 {preco}\n🔗 {link}")

    return "\n\n".join(mensagens)

# Teste isolado (executa só se rodar este arquivo diretamente)
if __name__ == "__main__":
    client = AliExpressClient(
        app_key=ALIEXPRESS_APP_KEY,
        app_secret=ALIEXPRESS_APP_SECRET,
        tracking_id=ALIEXPRESS_TRACKING_ID
    )

    termo = "smartwatch"
    resultado = client.search_products(termo, limit=3)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

    # Exemplo de formatação para WhatsApp
    print("\n--- Mensagem formatada ---\n")
    print(format_products_for_whatsapp(resultado))
