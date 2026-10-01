"""
Gera o token de acesso do LinkedIn (perfil pessoal) automaticamente:
abre o navegador, espera voce autorizar, captura o codigo, troca por um
token de acesso, descobre o URN do seu perfil e ja escreve tudo no .env.

Uso:
  python -m src.gerar_token_linkedin

Voce vai precisar ter em maos, na hora: o Client ID e o Client Secret
(aba "Auth" do seu app em linkedin.com/developers/apps).

IMPORTANTE: a URL de redirecionamento configurada no app do LinkedIn
precisa ser EXATAMENTE: http://localhost:8765/callback
"""
import http.server
import socketserver
import urllib.parse
import webbrowser
import threading
import requests
import re
import os

PORTA_CALLBACK = 8765
REDIRECT_URI = f"http://localhost:{PORTA_CALLBACK}/callback"
ESCOPO = "openid profile w_member_social"
CAMINHO_ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

_codigo_recebido = {"valor": None}


class HandlerCallback(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _codigo_recebido["valor"] = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<h2>Autorizado com sucesso!</h2><p>Pode fechar esta aba e voltar ao terminal.</p>".encode("utf-8")
            )
        else:
            erro = params.get("error_description", ["Erro desconhecido"])[0]
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h2>Falha na autorizacao</h2><p>{erro}</p>".encode("utf-8"))

    def log_message(self, format, *args):
        pass  # silencia o log padrao do servidor HTTP


def escrever_no_env(chave: str, valor: str):
    """Atualiza (ou adiciona) uma linha no .env sem apagar o resto do arquivo."""
    with open(CAMINHO_ENV, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    padrao = re.compile(rf"^{re.escape(chave)}=.*$")
    encontrada = False
    for i, linha in enumerate(linhas):
        if padrao.match(linha.strip()):
            linhas[i] = f"{chave}={valor}\n"
            encontrada = True
            break

    if not encontrada:
        linhas.append(f"{chave}={valor}\n")

    with open(CAMINHO_ENV, "w", encoding="utf-8") as f:
        f.writelines(linhas)


def main():
    print("=== Gerador de token do LinkedIn (perfil pessoal) ===\n")

    if not os.path.exists(CAMINHO_ENV):
        print(f"ERRO: arquivo .env nao encontrado em {CAMINHO_ENV}")
        print("Rode o instalador primeiro, ou copie o .env.example para .env.")
        return

    client_id = input("Cole o CLIENT ID: ").strip()
    print("Cole o CLIENT SECRET (vai aparecer na tela — sem problema, e so local):")
    client_secret = input("> ").strip()

    # Remove aspas acidentais, caso tenha colado com elas
    client_secret = client_secret.strip('"').strip("'")  # verificar:ignorar
    client_id = client_id.strip('"').strip("'")

    if not client_id or not client_secret:
        print("ERRO: Client ID e Client Secret sao obrigatorios.")
        return

    # Sobe um servidor local temporario so para capturar o redirecionamento do LinkedIn
    servidor = socketserver.TCPServer(("localhost", PORTA_CALLBACK), HandlerCallback)
    thread_servidor = threading.Thread(target=servidor.handle_request)
    thread_servidor.start()

    url_autorizacao = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code&client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&scope={urllib.parse.quote(ESCOPO)}"
        "&state=sofhie_ia_local"
    )

    print("\nAbrindo o navegador para voce fazer login e autorizar o app...")
    print("(se nao abrir sozinho, copie e cole esta URL no navegador:)")
    print(url_autorizacao)
    webbrowser.open(url_autorizacao)

    print("\nAguardando voce autorizar no navegador...")
    thread_servidor.join(timeout=180)

    codigo = _codigo_recebido["valor"]
    if not codigo:
        print("\nERRO: nao recebi o codigo de autorizacao a tempo (180s).")
        print("Confirme que a URL de redirecionamento no app do LinkedIn e exatamente:")
        print(f"   {REDIRECT_URI}")
        return

    print("\nCodigo de autorizacao recebido. Trocando por um token de acesso...")

    resposta = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": codigo,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )

    if not resposta.ok:
        print(f"\nERRO ao trocar o codigo por um token: {resposta.status_code} - {resposta.text}")
        if "invalid_client" in resposta.text:
            print("\nCausa mais provavel: o CLIENT SECRET colado esta incorreto (ou o codigo")
            print("de autorizacao ja expirou/foi usado). Va em linkedin.com/developers/apps,")
            print(f"aba Auth do app {client_id[:6]}..., copie o Client Secret de novo com cuidado")
            print("(sem espacos extras no inicio/fim) e rode o script novamente do zero.")
        return

    dados_token = resposta.json()
    access_token = dados_token["access_token"]
    expira_em_dias = dados_token.get("expires_in", 0) // 86400
    print(f"Token obtido com sucesso! Validade: ~{expira_em_dias} dias.")

    print("\nDescobrindo o URN do seu perfil...")
    resposta_perfil = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )

    if not resposta_perfil.ok:
        print(f"AVISO: nao consegui descobrir o URN automaticamente: {resposta_perfil.text}")
        print("O token foi salvo mesmo assim, mas preencha LINKEDIN_AUTHOR_URN manualmente.")
        author_urn = None
    else:
        sub = resposta_perfil.json().get("sub")
        author_urn = f"urn:li:person:{sub}"
        print(f"URN do perfil: {author_urn}")

    escrever_no_env("LINKEDIN_ACCESS_TOKEN", access_token)
    if author_urn:
        escrever_no_env("LINKEDIN_AUTHOR_URN", author_urn)

    print(f"\nPronto! .env atualizado em: {CAMINHO_ENV}")
    print("Reinicie o supervisor (Ctrl+C e 'python supervisor.py' de novo) para valer.")


if __name__ == "__main__":
    main()
