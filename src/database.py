"""
Banco de dados local (SQLite) — sem dependência de nuvem.
Guarda leads, histórico de conversas, publicações feitas e contadores diários.
"""
import sqlite3
import datetime
from contextlib import contextmanager
from src.config import DB_PATH


@contextmanager
def get_conn():
    # timeout maior + modo WAL: essencial aqui porque o núcleo, o agendador e o
    # dashboard são processos separados acessando o MESMO arquivo de banco ao
    # mesmo tempo. Sem isso, é comum aparecer erro "database is locked".
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefone TEXT UNIQUE NOT NULL,
                nome TEXT,
                status TEXT DEFAULT 'novo',  -- novo | em_conversa | pronto_fechamento | encaminhado
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS mensagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                remetente TEXT NOT NULL,  -- 'cliente' ou 'sofhie'
                conteudo TEXT NOT NULL,
                enviado_em TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS publicacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canal TEXT NOT NULL,  -- whatsapp_status | whatsapp_canal | instagram | linkedin
                conteudo_resumo TEXT,
                agendado_para TEXT,
                publicado_em TEXT,
                status TEXT DEFAULT 'pendente'  -- pendente | publicado | falhou
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS fila_conteudo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canal TEXT NOT NULL,        -- whatsapp_status | whatsapp_canal | instagram | linkedin
                tipo TEXT NOT NULL,         -- texto | imagem | artigo
                texto TEXT,
                caminho_midia TEXT,         -- caminho local do arquivo de imagem, se houver
                ordem INTEGER NOT NULL,     -- define a sequência exata de uso, por canal
                usado INTEGER DEFAULT 0,    -- 0 = ainda não publicado, 1 = já publicado
                criado_em TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS contadores_diarios (
                data TEXT PRIMARY KEY,
                novos_contatos INTEGER DEFAULT 0,
                mensagens_enviadas INTEGER DEFAULT 0,
                leads_encaminhados INTEGER DEFAULT 0
            )
        """)


def _hoje():
    return datetime.date.today().isoformat()


def _garantir_contador_hoje(conn):
    conn.execute(
        "INSERT OR IGNORE INTO contadores_diarios (data) VALUES (?)", (_hoje(),)
    )


def registrar_novo_contato(telefone: str, nome: str = None):
    agora = datetime.datetime.now().isoformat()
    with get_conn() as conn:
        _garantir_contador_hoje(conn)
        cur = conn.execute("SELECT id FROM leads WHERE telefone = ?", (telefone,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO leads (telefone, nome, criado_em, atualizado_em) VALUES (?, ?, ?, ?)",
            (telefone, nome, agora, agora),
        )
        conn.execute(
            "UPDATE contadores_diarios SET novos_contatos = novos_contatos + 1 WHERE data = ?",
            (_hoje(),),
        )
        return cur.lastrowid


def registrar_mensagem(lead_id: int, remetente: str, conteudo: str):
    agora = datetime.datetime.now().isoformat()
    with get_conn() as conn:
        _garantir_contador_hoje(conn)
        conn.execute(
            "INSERT INTO mensagens (lead_id, remetente, conteudo, enviado_em) VALUES (?, ?, ?, ?)",
            (lead_id, remetente, conteudo, agora),
        )
        conn.execute("UPDATE leads SET atualizado_em = ? WHERE id = ?", (agora, lead_id))
        if remetente == "sofhie":
            conn.execute(
                "UPDATE contadores_diarios SET mensagens_enviadas = mensagens_enviadas + 1 WHERE data = ?",
                (_hoje(),),
            )


def marcar_pronto_para_fechamento(lead_id: int):
    with get_conn() as conn:
        _garantir_contador_hoje(conn)
        conn.execute("UPDATE leads SET status = 'pronto_fechamento' WHERE id = ?", (lead_id,))
        conn.execute(
            "UPDATE contadores_diarios SET leads_encaminhados = leads_encaminhados + 1 WHERE data = ?",
            (_hoje(),),
        )


def contar_novos_contatos_hoje() -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT novos_contatos FROM contadores_diarios WHERE data = ?", (_hoje(),)
        )
        row = cur.fetchone()
        return row["novos_contatos"] if row else 0


def contar_mensagens_hoje() -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT mensagens_enviadas FROM contadores_diarios WHERE data = ?", (_hoje(),)
        )
        row = cur.fetchone()
        return row["mensagens_enviadas"] if row else 0


def historico_conversa(lead_id: int, limite: int = 20):
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT remetente, conteudo FROM mensagens WHERE lead_id = ? ORDER BY id DESC LIMIT ?",
            (lead_id, limite),
        )
        rows = list(reversed(cur.fetchall()))
        return [{"role": "user" if r["remetente"] == "cliente" else "assistant", "content": r["conteudo"]} for r in rows]


def relatorio_do_dia(data: str = None):
    data = data or _hoje()
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM contadores_diarios WHERE data = ?", (data,))
        contadores = cur.fetchone()
        cur = conn.execute(
            "SELECT canal, COUNT(*) as total FROM publicacoes WHERE date(publicado_em) = ? AND status = 'publicado' GROUP BY canal",
            (data,),
        )
        publicacoes = {r["canal"]: r["total"] for r in cur.fetchall()}
        return {
            "data": data,
            "novos_contatos": contadores["novos_contatos"] if contadores else 0,
            "mensagens_enviadas": contadores["mensagens_enviadas"] if contadores else 0,
            "leads_encaminhados": contadores["leads_encaminhados"] if contadores else 0,
            "publicacoes_por_canal": publicacoes,
        }


# ---------- Fila de conteúdo (publicações programadas) ----------

def adicionar_ao_fila(canal: str, tipo: str, texto: str = None, caminho_midia: str = None, ordem: int = None):
    """
    Adiciona um item à fila de um canal. Se 'ordem' não for informado, entra no final da fila.
    """
    agora = datetime.datetime.now().isoformat()
    with get_conn() as conn:
        if ordem is None:
            cur = conn.execute(
                "SELECT COALESCE(MAX(ordem), 0) + 1 as prox FROM fila_conteudo WHERE canal = ?", (canal,)
            )
            ordem = cur.fetchone()["prox"]
        conn.execute(
            """INSERT INTO fila_conteudo (canal, tipo, texto, caminho_midia, ordem, criado_em)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (canal, tipo, texto, caminho_midia, ordem, agora),
        )


def proximo_item_da_fila(canal: str):
    """Retorna o próximo item não publicado do canal, respeitando a ordem definida."""
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM fila_conteudo WHERE canal = ? AND usado = 0 ORDER BY ordem ASC LIMIT 1",
            (canal,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def marcar_item_usado(item_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE fila_conteudo SET usado = 1 WHERE id = ?", (item_id,))


def itens_restantes_na_fila(canal: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) as total FROM fila_conteudo WHERE canal = ? AND usado = 0", (canal,)
        )
        return cur.fetchone()["total"]


def registrar_publicacao(canal: str, resumo: str, sucesso: bool):
    agora = datetime.datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO publicacoes (canal, conteudo_resumo, agendado_para, publicado_em, status)
               VALUES (?, ?, ?, ?, ?)""",
            (canal, resumo, agora, agora, "publicado" if sucesso else "falhou"),
        )
