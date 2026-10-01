"""
Script utilitário para você adicionar conteúdo à fila de publicações,
sem precisar escrever código Python. Roda direto no terminal.

Exemplos de uso:

  python -m src.adicionar_conteudo --canal whatsapp_status --tipo texto --texto "Bom dia! Confira nossa novidade..."

  python -m src.adicionar_conteudo --canal instagram --tipo imagem --texto "Legenda do post" --midia "https://link-publico-da-imagem.jpg"

  python -m src.adicionar_conteudo --canal linkedin --tipo artigo --texto "Texto completo do artigo/post..."

IMPORTANTE (Instagram): a Graph API exige uma URL PÚBICA de imagem — não um caminho
local do seu notebook. Hospede as imagens em algum lugar acessível (ex: um bucket
gratuito, GitHub, ou mesmo um link do Google Drive configurado como público) antes
de adicionar à fila.
"""
import argparse
from src.database import init_db, adicionar_ao_fila

CANAIS_VALIDOS = ["whatsapp_status", "whatsapp_canal", "instagram", "linkedin"]
TIPOS_VALIDOS = ["texto", "imagem", "artigo"]


def main():
    parser = argparse.ArgumentParser(description="Adiciona um item à fila de publicações da Sofhie IA")
    parser.add_argument("--canal", required=True, choices=CANAIS_VALIDOS)
    parser.add_argument("--tipo", required=True, choices=TIPOS_VALIDOS)
    parser.add_argument("--texto", default=None, help="Texto ou legenda do conteúdo")
    parser.add_argument("--midia", default=None, help="URL pública da imagem (obrigatório para Instagram)")
    parser.add_argument("--ordem", type=int, default=None, help="Posição na fila (padrão: entra no final)")
    args = parser.parse_args()

    init_db()
    adicionar_ao_fila(
        canal=args.canal, tipo=args.tipo, texto=args.texto, caminho_midia=args.midia, ordem=args.ordem
    )
    print(f"✅ Item adicionado à fila do canal '{args.canal}'.")


if __name__ == "__main__":
    main()
