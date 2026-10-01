"""
Publicador de status e canal do WhatsApp Business — usa a ponte Node.js (Baileys)
já conectada ao número da empresa. Não tem custo, mas herda o mesmo risco de
bloqueio já avisado sobre o uso da biblioteca não-oficial.
"""
import requests
from src.config import WHATSAPP_BRIDGE_URL


def publicar_status(item_fila: dict) -> tuple[bool, str]:
    texto = item_fila.get("texto") or ""
    if not texto:
        return False, "Item sem texto — status do WhatsApp requer conteúdo"

    try:
        resposta = requests.post(
            f"{WHATSAPP_BRIDGE_URL}/publicar-status", json={"texto": texto}, timeout=15
        )
        resposta.raise_for_status()
        return True, "Status publicado com sucesso"
    except requests.exceptions.RequestException as e:
        return False, f"Erro ao publicar status: {e}"


def publicar_canal(item_fila: dict) -> tuple[bool, str]:
    """
    Publicação em Canal do WhatsApp (WhatsApp Channel).
    A biblioteca Baileys tem suporte experimental a canais (newsletters) — a
    ponte Node.js precisa do ID do canal configurado para isso funcionar de fato.
    Por ora, este publicador está pronto na estrutura, mas depende de você
    confirmar o ID do seu canal para ativação completa na Fase 3.
    """
    texto = item_fila.get("texto") or ""
    if not texto:
        return False, "Item sem texto — publicação no canal requer conteúdo"

    try:
        resposta = requests.post(
            f"{WHATSAPP_BRIDGE_URL}/publicar-canal", json={"texto": texto}, timeout=15
        )
        resposta.raise_for_status()
        return True, "Publicado no canal com sucesso"
    except requests.exceptions.RequestException as e:
        return False, f"Erro ao publicar no canal (verifique se o ID do canal já foi configurado na ponte): {e}"
