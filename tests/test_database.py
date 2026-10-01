"""
Testes automatizados das partes mais críticas do sistema: banco de dados,
fila de conteúdo e detecção de intenção de fechamento.

Rodar com: pytest tests/ -v
"""
import os
import tempfile
import pytest

import src.config as config

# Usa um banco de dados temporário só para os testes, nunca o banco real.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
config.DB_PATH = _tmp_db.name

from src import database  # noqa: E402  (import depois de trocar o DB_PATH)


@pytest.fixture(autouse=True)
def banco_limpo():
    database.init_db()
    yield
    # limpa as tabelas entre testes para isolamento
    with database.get_conn() as conn:
        for tabela in ["leads", "mensagens", "publicacoes", "fila_conteudo", "contadores_diarios"]:
            conn.execute(f"DELETE FROM {tabela}")


def test_registrar_novo_contato_cria_lead_unico():
    id1 = database.registrar_novo_contato("5544999990000")
    id2 = database.registrar_novo_contato("5544999990000")  # mesmo telefone
    assert id1 == id2  # não deve duplicar


def test_contador_novos_contatos_incrementa():
    database.registrar_novo_contato("5544999990001")
    database.registrar_novo_contato("5544999990002")
    assert database.contar_novos_contatos_hoje() == 2


def test_mensagem_sofhie_incrementa_contador_mas_cliente_nao():
    lead_id = database.registrar_novo_contato("5544999990003")
    database.registrar_mensagem(lead_id, "cliente", "Oi, tudo bem?")
    database.registrar_mensagem(lead_id, "sofhie", "Tudo ótimo! Como posso ajudar?")
    assert database.contar_mensagens_hoje() == 1  # só conta mensagens da Sofhie


def test_fila_de_conteudo_respeita_ordem():
    database.adicionar_ao_fila("whatsapp_status", "texto", texto="Primeira mensagem")
    database.adicionar_ao_fila("whatsapp_status", "texto", texto="Segunda mensagem")

    primeiro = database.proximo_item_da_fila("whatsapp_status")
    assert primeiro["texto"] == "Primeira mensagem"

    database.marcar_item_usado(primeiro["id"])
    segundo = database.proximo_item_da_fila("whatsapp_status")
    assert segundo["texto"] == "Segunda mensagem"


def test_fila_vazia_retorna_none():
    assert database.proximo_item_da_fila("linkedin") is None


def test_lead_pronto_para_fechamento_incrementa_contador():
    lead_id = database.registrar_novo_contato("5544999990004")
    database.marcar_pronto_para_fechamento(lead_id)
    relatorio = database.relatorio_do_dia()
    assert relatorio["leads_encaminhados"] == 1


def test_detectar_intencao_fechamento():
    from src.ia_client import detectar_intencao_fechamento

    assert detectar_intencao_fechamento("Como faço para fechar o contrato?") is True
    assert detectar_intencao_fechamento("Qual a previsão do tempo hoje?") is False
