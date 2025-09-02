# agents/session_manager.py

class SessionManager:
    """
    Gerencia o histórico de mensagens por usuário (sender_id).
    Mantém até max_len entradas para cada sessão.
    """
    def __init__(self, max_len: int = 10):
        self.max_len = max_len
        self.sessions = {}  # { sender_id: [mensagens] }

    def push(self, sender_id: str, message: str) -> list[str]:
        hist = self.sessions.setdefault(sender_id, [])
        hist.append(message)
        if len(hist) > self.max_len:
            hist.pop(0)
        return hist

    def get(self, sender_id: str) -> list[str]:
        return self.sessions.get(sender_id, [])
