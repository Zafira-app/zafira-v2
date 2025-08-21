"""
Zafira V2.0 - Webhook Handler Principal
Assistente inteligente de compras para WhatsApp
"""

from flask import Flask, request, jsonify
import os
import logging
from zafira_core import ZafiraCore

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Inicializa o cérebro da Zafira
zafira = ZafiraCore()

@app.route('/', methods=['GET'])
def health_check():
    """Verificação de saúde do serviço"""
    return "Zafira V2.0 - Assistente inteligente de compras ativa! 🛍️", 200

@app.route('/webhook', methods=['GET'])
def webhook_verification():
    """Verificação do webhook do WhatsApp"""
    verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN')
    
    if request.args.get('hub.verify_token') == verify_token:
        logger.info("Webhook verificado com sucesso")
        return request.args.get('hub.challenge'), 200
    else:
        logger.error("Token de verificação inválido")
        return "Token inválido", 403

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handler principal para mensagens do WhatsApp"""
    try:
        data = request.get_json()
        logger.info(f"Webhook recebido: {data}")
        
        # Verifica se há mensagens na requisição
        if 'entry' in data:
            for entry in data['entry']:
                if 'changes' in entry:
                    for change in entry['changes']:
                        if 'value' in change and 'messages' in change['value']:
                            for message in change['value']['messages']:
                                # Processa cada mensagem
                                process_message(message, change['value'])
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_message(message, value):
    """Processa uma mensagem individual"""
    try:
        # Extrai informações da mensagem
        user_id = message['from']
        message_text = message.get('text', {}).get('body', '')
        message_type = message.get('type', 'text')
        
        logger.info(f"Processando mensagem de {user_id}: {message_text}")
        
        # Ignora mensagens que não são texto
        if message_type != 'text' or not message_text:
            logger.info("Mensagem ignorada (não é texto)")
            return
        
        # Processa com o cérebro da Zafira
        response = zafira.process_message(user_id, message_text)
        
        if response:
            logger.info(f"Resposta gerada: {response[:100]}...")
        else:
            logger.warning("Nenhuma resposta gerada")
            
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        # Em caso de erro, tenta enviar uma mensagem de erro amigável
        try:
            zafira.send_error_message(user_id)
        except:
            pass

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Iniciando Zafira V2.0 na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
