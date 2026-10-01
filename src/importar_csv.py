"""
Importa várias publicações de uma vez a partir de um arquivo CSV — muito mais
prático do que rodar um comando por publicação quando você tem 8 posts/dia
para preparar de uma vez.

Formato esperado do CSV (veja modelo_conteudo.csv como exemplo):
  canal,tipo,texto,midia
  whatsapp_status,texto,"Bom dia! ...",
  instagram,imagem,"Legenda do post","https://url-publica-da-imagem.jpg"

Regras:
- canal: whatsapp_status | whatsapp_canal | instagram | linkedin
- tipo: texto | imagem | artigo
- midia: obrigatório apenas para itens do tipo "imagem" indo para o Instagram
  (precisa ser uma URL pública, não um caminho local)
- A ORDEM DAS LINHAS no CSV define a ordem de publicação dentro de cada canal.
  Linhas de canais diferentes não interferem entre si.

Uso:
  python -m src.importar_csv --arquivo modelo_conteudo.csv
  python -m src.importar_csv --arquivo minha_semana_de_posts.csv
"""
import argparse
import csv
import sys

from src.database import init_db, adicionar_ao_fila
from src.logging_config import get_logger

log = get_logger("importador_csv")

CANAIS_VALIDOS = {"whatsapp_status", "whatsapp_canal", "instagram", "linkedin"}
TIPOS_VALIDOS = {"texto", "imagem", "artigo"}


def validar_linha(linha: dict, numero_linha: int) -> list[str]:
    erros = []
    canal = (linha.get("canal") or "").strip()
    tipo = (linha.get("tipo") or "").strip()
    texto = (linha.get("texto") or "").strip()
    midia = (linha.get("midia") or "").strip()

    if canal not in CANAIS_VALIDOS:
        erros.append(f"linha {numero_linha}: canal '{canal}' inválido (use: {', '.join(CANAIS_VALIDOS)})")
    if tipo not in TIPOS_VALIDOS:
        erros.append(f"linha {numero_linha}: tipo '{tipo}' inválido (use: {', '.join(TIPOS_VALIDOS)})")
    if not texto and tipo != "imagem":
        erros.append(f"linha {numero_linha}: texto vazio")
    if canal == "instagram" and tipo == "imagem" and not midia:
        erros.append(f"linha {numero_linha}: Instagram exige uma URL pública de imagem no campo 'midia'")

    return erros


def importar(caminho_csv: str):
    init_db()

    with open(caminho_csv, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        linhas = list(leitor)

    if not linhas:
        print("⚠️  O arquivo CSV está vazio ou não pôde ser lido corretamente.")
        return

    todos_erros = []
    for i, linha in enumerate(linhas, start=2):  # start=2 porque a linha 1 é o cabeçalho
        todos_erros.extend(validar_linha(linha, i))

    if todos_erros:
        print(f"❌ Encontrei {len(todos_erros)} problema(s) no CSV — nada foi importado ainda:\n")
        for erro in todos_erros:
            print(f"   - {erro}")
        print("\nCorrija o arquivo e rode o comando novamente.")
        sys.exit(1)

    contagem_por_canal = {}
    for linha in linhas:
        canal = linha["canal"].strip()
        tipo = linha["tipo"].strip()
        texto = (linha.get("texto") or "").strip() or None
        midia = (linha.get("midia") or "").strip() or None

        adicionar_ao_fila(canal=canal, tipo=tipo, texto=texto, caminho_midia=midia)
        contagem_por_canal[canal] = contagem_por_canal.get(canal, 0) + 1

    log.info(f"Importação concluída: {contagem_por_canal}")
    print("✅ Importação concluída com sucesso:\n")
    for canal, total in contagem_por_canal.items():
        print(f"   - {canal}: {total} item(ns) adicionado(s) à fila")


def main():
    parser = argparse.ArgumentParser(description="Importa conteúdo em massa para a fila de publicações")
    parser.add_argument("--arquivo", required=True, help="Caminho do arquivo CSV")
    args = parser.parse_args()
    importar(args.arquivo)


if __name__ == "__main__":
    main()
