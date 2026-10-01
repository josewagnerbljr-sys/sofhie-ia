"""
Notificações automáticas para você (dono do número).
Usa a ponte Node.js já conectada ao WhatsApp para te avisar em tempo real
quando um lead está pronto para fechamento — sem precisar abrir o dashboard.
"""
import requests
from src.config import NUMERO_NOTIFICACAO_DONO, WHATSAPP_BRIDGE_URL


def notificar_lead_pronto(telefone_lead: str, nome_lead: str, ultima_mensagem: str):
    if not NUMERO_NOTIFICACAO_DONO:
        print("[AVISO] NUMERO_NOTIFICACAO_DONO não configurado no .env — notificação não enviada.")
        return False

    texto = (
        "🔔 *Lead pronto para fechamento*\n\n"
        f"Contato: {nome_lead or telefone_lead}\n"
        f"Telefone: {telefone_lead}\n\n"
        f"Última mensagem do cliente:\n\"{ultima_mensagem}\"\n\n"
        "A Sofhie já sinalizou o cliente e está mantendo o atendimento acolhedor. "
        "Assuma a conversa quando puder para finalizar."
    )

    try:
        resposta = requests.post(
            f"{WHATSAPP_BRIDGE_URL}/enviar-mensagem",
            json={"telefone": NUMERO_NOTIFICACAO_DONO, "texto": texto},
            timeout=10,
        )
        return resposta.ok
    except Exception as e:
        print(f"[ERRO] Falha ao notificar o dono sobre lead pronto: {e}")
        return False


def notificar_relatorio_diario(relatorio: dict):
    if not NUMERO_NOTIFICACAO_DONO:
        return False

    publicacoes = relatorio.get("publicacoes_por_canal", {})
    linhas_publicacoes = "\n".join(
        f"  • {canal}: {total}" for canal, total in publicacoes.items()
    ) or "  • Nenhuma publicação registrada"

    texto = (
        f"📊 *Relatório Sofhie IA — {relatorio['data']}*\n\n"
        f"Novos contatos: {relatorio['novos_contatos']}\n"
        f"Mensagens enviadas: {relatorio['mensagens_enviadas']}\n"
        f"Leads encaminhados: {relatorio['leads_encaminhados']}\n\n"
        f"Publicações:\n{linhas_publicacoes}"
    )

    try:
        resposta = requests.post(
            f"{WHATSAPP_BRIDGE_URL}/enviar-mensagem",
            json={"telefone": NUMERO_NOTIFICACAO_DONO, "texto": texto},
            timeout=10,
        )
        return resposta.ok
    except Exception as e:
        print(f"[ERRO] Falha ao enviar relatório diário: {e}")
        return False
