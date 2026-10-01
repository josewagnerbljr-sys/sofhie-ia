"""
Proteções contra bloqueio do número de WhatsApp.
Sem isso, um número comercial fazendo automação de conversas é banido em dias.
"""
import random
from src.config import LIMITE_NOVOS_CONTATOS_DIA, LIMITE_MENSAGENS_DIA
from src.database import contar_novos_contatos_hoje, contar_mensagens_hoje


def pode_iniciar_novo_contato() -> bool:
    return contar_novos_contatos_hoje() < LIMITE_NOVOS_CONTATOS_DIA


def pode_enviar_mensagem() -> bool:
    return contar_mensagens_hoje() < LIMITE_MENSAGENS_DIA


def calcular_delay_humanizado(tamanho_resposta: int = 100) -> float:
    """
    Calcula (sem esperar de verdade) um tempo de "digitacao humana" com base
    no tamanho da resposta — quanto maior a mensagem, mais tempo simulado.

    IMPORTANTE: esta funcao NAO bloqueia (nao faz time.sleep). Ela so retorna
    o valor em segundos. Quem efetivamente espera esse tempo e a ponte
    Node.js, uma unica vez, logo antes de enviar a mensagem pelo WhatsApp.
    Antes, o nucleo Python tambem dormia esse tempo E a ponte dormia de novo —
    isso dobrava a demora e travava as respostas. Corrigido aqui.
    """
    base = min(1.5 + tamanho_resposta / 50, 8)
    variacao = random.uniform(0.8, 1.2)
    return base * variacao


def intervalo_entre_publicacoes():
    """Pequena variação aleatória entre publicações programadas, para não parecer robótico."""
    return random.randint(20, 180)  # segundos
