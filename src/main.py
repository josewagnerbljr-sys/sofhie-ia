"""
Núcleo principal da Sofhie IA.
Recebe mensagens encaminhadas pela ponte Node.js (whatsapp-service), gera a resposta
com IA, aplica proteções anti-ban e devolve a resposta para ser enviada ao cliente.

Rodar com: python -m src.main
"""
from flask import Flask, request, jsonify

from src.database import (
    init_db,
    registrar_novo_contato,
    registrar_mensagem,
    marcar_pronto_para_fechamento,
    historico_conversa,
)
from src.ia_client import gerar_resposta, detectar_intencao_fechamento
from src.antiban import pode_enviar_mensagem, calcular_delay_humanizado
from src.notificacoes import notificar_lead_pronto
from src.logging_config import get_logger

app = Flask(__name__)
init_db()
log = get_logger("nucleo")


@app.route("/mensagem-recebida", methods=["POST"])
def mensagem_recebida():
    try:
        dados = request.get_json(force=True, silent=True) or {}
        telefone = dados.get("telefone")
        texto_cliente = dados.get("mensagem")

        if not telefone or not texto_cliente:
            log.warning(f"Requisição inválida recebida: {dados}")
            return jsonify({"erro": "telefone e mensagem são obrigatórios"}), 400

        if not pode_enviar_mensagem():
            log.warning(f"Limite diário de mensagens atingido — ignorando mensagem de {telefone}")
            return jsonify({"resposta": None})

        lead_id = registrar_novo_contato(telefone)
        registrar_mensagem(lead_id, "cliente", texto_cliente)
        log.info(f"Mensagem recebida de {telefone} (lead {lead_id})")

        if detectar_intencao_fechamento(texto_cliente):
            marcar_pronto_para_fechamento(lead_id)
            try:
                notificar_lead_pronto(telefone_lead=telefone, nome_lead=None, ultima_mensagem=texto_cliente)
            except Exception as e:
                # A notificação falhar não pode derrubar o atendimento ao cliente.
                log.error(f"Falha ao notificar lead pronto (lead {lead_id}): {e}")

        historico = historico_conversa(lead_id)

        try:
            resposta_texto = gerar_resposta(historico)
        except Exception as e:
            log.error(f"Falha crítica ao gerar resposta (lead {lead_id}): {e}")
            resposta_texto = (
                "Peço desculpas, estou com uma instabilidade momentânea. "
                "Um responsável da equipe vai te retornar em breve."
            )

        registrar_mensagem(lead_id, "sofhie", resposta_texto)
        tempo_delay = calcular_delay_humanizado(len(resposta_texto))

        return jsonify({"resposta": resposta_texto, "delay_ms": int(tempo_delay * 1000)})

    except Exception as e:
        # Rede de segurança final: nenhum erro inesperado deve derrubar o servidor
        # nem deixar o cliente sem resposta alguma.
        log.exception(f"Erro não tratado em /mensagem-recebida: {e}")
        return jsonify({"resposta": "Desculpe, tive um problema técnico. Já estou verificando."}), 200


@app.route("/saude", methods=["GET"])
def saude():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("Núcleo Sofhie IA rodando em http://localhost:8000")
    # threaded=True é essencial aqui: sem isso, o delay humanizado de um
    # atendimento (2-12s) bloquearia TODOS os outros clientes simultâneos.
    app.run(host="0.0.0.0", port=8000, threaded=True)
