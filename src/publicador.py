"""
Orquestrador de publicações — puxa o próximo item da fila de cada canal
(respeitando a ordem/sequência definida por você) e publica de fato,
registrando o resultado no banco para aparecer no relatório diário.
"""
from src.database import proximo_item_da_fila, marcar_item_usado, registrar_publicacao
from src.publicadores import instagram, linkedin, whatsapp_canal


def publicar_proximo(canal: str):
    item = proximo_item_da_fila(canal)
    if not item:
        print(f"[Publicador] Fila do canal '{canal}' está vazia — nada para publicar.")
        return

    if canal == "instagram":
        sucesso, mensagem = instagram.publicar(item)
    elif canal == "linkedin":
        sucesso, mensagem = linkedin.publicar(item)
    elif canal == "whatsapp_status":
        sucesso, mensagem = whatsapp_canal.publicar_status(item)
    elif canal == "whatsapp_canal":
        sucesso, mensagem = whatsapp_canal.publicar_canal(item)
    else:
        print(f"[Publicador] Canal desconhecido: {canal}")
        return

    resumo = (item.get("texto") or "")[:100]
    registrar_publicacao(canal, resumo, sucesso)

    if sucesso:
        marcar_item_usado(item["id"])
        print(f"[Publicador] OK — {canal}: {mensagem}")
    else:
        # Item NÃO é marcado como usado em caso de falha — tenta de novo no próximo ciclo,
        # sem perder o lugar na fila.
        print(f"[Publicador] FALHOU — {canal}: {mensagem}")
