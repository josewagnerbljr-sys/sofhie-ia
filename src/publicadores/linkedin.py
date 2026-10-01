"""
Publicador do LinkedIn — usa a API OFICIAL (produto "Share on LinkedIn", ja aprovado).

IMPORTANTE: no momento, o app so tem aprovacao para publicar no PERFIL PESSOAL
(escopo w_member_social), nao na Pagina da Empresa. Publicar na Pagina exige o
produto "Community Management API" (aprovacao separada, mais rigorosa) — quando
esse for aprovado, so trocar o LINKEDIN_AUTHOR_URN pelo URN da organizacao.

Decisao ja registrada no projeto: reduzimos de 8 para 1-2 publicacoes automatizadas
por dia neste canal. Volume alto automatizado no LinkedIn e detectado e penalizado/
banido pela propria plataforma — isso nao e uma limitacao de codigo, e politica da
plataforma. Use o alto volume nos canais de WhatsApp/Instagram, que suportam isso
oficialmente.
"""
import requests
from src.config import LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR_URN

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def publicar(item_fila: dict) -> tuple[bool, str]:
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_AUTHOR_URN:
        return False, "LinkedIn nao configurado (rode 'python -m src.gerar_token_linkedin' primeiro)"

    texto = item_fila.get("texto") or ""
    if not texto:
        return False, "Item sem texto — publicacao no LinkedIn requer conteudo textual"

    corpo = {
        "author": LINKEDIN_AUTHOR_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": texto},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    try:
        resposta = requests.post(
            f"{LINKEDIN_API_BASE}/ugcPosts",
            json=corpo,
            headers={
                "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resposta.raise_for_status()
        return True, f"Publicado com sucesso (id: {resposta.headers.get('x-restli-id', 'n/d')})"
    except requests.exceptions.RequestException as e:
        detalhe = e.response.text if e.response is not None else str(e)
        return False, f"Erro ao publicar no LinkedIn: {detalhe}"
