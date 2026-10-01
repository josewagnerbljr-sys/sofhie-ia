"""
Publicador do Instagram — usa a API OFICIAL (Graph API da Meta), gratuita.
Requer: conta Instagram Profissional vinculada a uma Página do Facebook,
e um token de acesso de longa duração gerado no Meta for Developers.

Como uma imagem é obrigatória para publicar no feed via Graph API, itens do
tipo "texto" sem imagem não são suportados neste canal — use "imagem".
"""
import requests
from src.config import INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"


def publicar(item_fila: dict) -> tuple[bool, str]:
    """
    item_fila: dict vindo de database.proximo_item_da_fila()
    Retorna (sucesso: bool, mensagem: str)
    """
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
        return False, "Instagram não configurado (faltam credenciais no .env)"

    if not item_fila.get("caminho_midia"):
        return False, "Item sem imagem — Instagram exige mídia para publicar no feed"

    legenda = item_fila.get("texto") or ""
    url_imagem = item_fila["caminho_midia"]  # precisa ser uma URL pública da imagem

    try:
        # Passo 1: criar o container de mídia
        resposta_container = requests.post(
            f"{GRAPH_API_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media",
            data={
                "image_url": url_imagem,
                "caption": legenda,
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=30,
        )
        resposta_container.raise_for_status()
        container_id = resposta_container.json()["id"]

        # Passo 2: publicar o container criado
        resposta_publish = requests.post(
            f"{GRAPH_API_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish",
            data={"creation_id": container_id, "access_token": INSTAGRAM_ACCESS_TOKEN},
            timeout=30,
        )
        resposta_publish.raise_for_status()
        return True, f"Publicado com sucesso (id: {resposta_publish.json().get('id')})"

    except requests.exceptions.RequestException as e:
        detalhe = e.response.text if e.response is not None else str(e)
        return False, f"Erro ao publicar no Instagram: {detalhe}"
