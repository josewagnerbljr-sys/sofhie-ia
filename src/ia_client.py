"""
Camada de IA conversacional: usa Groq (gratuito, muito rápido) como principal.
Se a Groq falhar (limite diário atingido, erro de rede, etc.), cai automaticamente
para o Gemini (também gratuito) como fallback — a Sofhie nunca fica "muda".
"""
from groq import Groq
import google.generativeai as genai
import time
from src.config import GROQ_API_KEY, GEMINI_API_KEY
from src.persona import SOFHIE_SYSTEM_PROMPT
from src.logging_config import get_logger

log = get_logger("ia_client")

_groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    _gemini_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SOFHIE_SYSTEM_PROMPT,
    )
else:
    _gemini_model = None

GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TENTATIVAS = 2


def _com_retry(func, *args, tentativas=MAX_TENTATIVAS, **kwargs):
    """Tenta a função algumas vezes antes de desistir — cobre falhas momentâneas de rede/API."""
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ultimo_erro = e
            log.warning(f"Tentativa {tentativa}/{tentativas} falhou: {e}")
            if tentativa < tentativas:
                time.sleep(1.5 * tentativa)
    log.error(f"Todas as {tentativas} tentativas falharam. Último erro: {ultimo_erro}")
    return None


def _tentar_groq(historico: list) -> str | None:
    if not _groq_client:
        return None

    def _chamar():
        mensagens = [{"role": "system", "content": SOFHIE_SYSTEM_PROMPT}] + historico
        resposta = _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=mensagens,
            temperature=0.6,
            max_tokens=400,
        )
        return resposta.choices[0].message.content.strip()

    resultado = _com_retry(_chamar)
    if resultado is None:
        log.warning("Groq indisponível após retries — acionando fallback Gemini.")
    return resultado


def _tentar_gemini(historico: list) -> str | None:
    if not _gemini_model:
        return None

    def _chamar():
        chat = _gemini_model.start_chat(history=[
            {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
            for m in historico[:-1]
        ])
        resposta = chat.send_message(historico[-1]["content"])
        return resposta.text.strip()

    resultado = _com_retry(_chamar)
    if resultado is None:
        log.error("Gemini (fallback) também indisponível após retries.")
    return resultado


def gerar_resposta(historico: list) -> str:
    """
    historico: lista de dicts [{"role": "user"/"assistant", "content": "..."}]
    Retorna a resposta da Sofhie, ou uma mensagem segura caso ambos os provedores falhem.
    """
    resposta = _tentar_groq(historico)
    if resposta:
        return resposta

    resposta = _tentar_gemini(historico)
    if resposta:
        return resposta

    return (
        "Peço desculpas, estou com uma instabilidade momentânea no meu sistema. "
        "Um responsável da equipe vai te retornar em breve — obrigada pela paciência!"
    )


def detectar_intencao_fechamento(mensagem_cliente: str) -> bool:
    """
    Checagem simples e barata (sem chamar IA) para sinalizar quando o cliente
    demonstra intenção clara de compra. Serve de gatilho rápido para o handoff humano,
    complementando a instrução já dada à persona no system prompt.
    """
    gatilhos = [
        "fechar", "contrato", "assinar", "como pago", "como faço para comprar",
        "quero contratar", "proposta comercial", "quero adquirir", "forma de pagamento",
    ]
    texto = mensagem_cliente.lower()
    return any(g in texto for g in gatilhos)
