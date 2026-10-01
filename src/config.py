"""
Configuração central do sistema Sofhie IA.
Carrega variáveis do arquivo .env e expõe como constantes.
"""
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

LIMITE_NOVOS_CONTATOS_DIA = int(os.getenv("LIMITE_NOVOS_CONTATOS_DIA", "30"))
LIMITE_MENSAGENS_DIA = int(os.getenv("LIMITE_MENSAGENS_DIA", "200"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))

NUMERO_NOTIFICACAO_DONO = os.getenv("NUMERO_NOTIFICACAO_DONO", "")
WHATSAPP_BRIDGE_URL = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:8001")

# Instagram (API oficial - Graph API)
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

# LinkedIn (API oficial)
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
# LINKEDIN_AUTHOR_URN aceita tanto urn:li:person:... (perfil pessoal, aprovado hoje)
# quanto urn:li:organization:... (Página da Empresa, quando o Community Management
# API for aprovado — só trocar o valor aqui, o código do publicador não muda).
LINKEDIN_AUTHOR_URN = os.getenv("LINKEDIN_AUTHOR_URN", "")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "sofhie.db")

if not GROQ_API_KEY:
    print("[AVISO] GROQ_API_KEY não configurada no .env — a IA não vai conseguir gerar respostas.")
