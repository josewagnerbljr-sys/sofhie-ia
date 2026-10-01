"""
Supervisor de processos — sobe os 4 componentes do sistema (núcleo Python, ponte
WhatsApp em Node.js, dashboard e agendador) e monitora continuamente. Se qualquer
um deles cair (crash, erro não tratado, etc.), reinicia automaticamente sozinho.

Este é o jeito recomendado de rodar o sistema no dia a dia — evita depender de
você manter 4 terminais abertos manualmente o tempo todo.

Uso: python supervisor.py
Para parar tudo: Ctrl+C uma vez (o supervisor encerra os processos filhos de forma limpa).
"""
import subprocess
import sys
import time
import signal
import os

from src.logging_config import get_logger

log = get_logger("supervisor")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

PROCESSOS = {
    "nucleo": {"comando": [PYTHON, "-m", "src.main"], "cwd": BASE_DIR},
    "dashboard": {"comando": [PYTHON, "dashboard/app.py"], "cwd": BASE_DIR},
    "agendador": {"comando": [PYTHON, "-m", "src.scheduler"], "cwd": BASE_DIR},
    "whatsapp_bridge": {"comando": ["node", "index.js"], "cwd": os.path.join(BASE_DIR, "whatsapp-service")},
}

INTERVALO_VERIFICACAO_SEGUNDOS = 10
LIMITE_REINICIOS_POR_HORA = 10  # se passar disso, algo está estruturalmente errado — não insiste

_handles = {}
_contagem_reinicios = {nome: [] for nome in PROCESSOS}
_encerrando = False


def _iniciar(nome: str):
    conf = PROCESSOS[nome]
    log.info(f"Iniciando processo '{nome}'...")
    _handles[nome] = subprocess.Popen(conf["comando"], cwd=conf["cwd"])


def _reinicios_na_ultima_hora(nome: str) -> int:
    agora = time.time()
    _contagem_reinicios[nome] = [t for t in _contagem_reinicios[nome] if agora - t < 3600]
    return len(_contagem_reinicios[nome])


def _parar_tudo():
    global _encerrando
    _encerrando = True
    log.info("Encerrando todos os processos...")
    for nome, handle in _handles.items():
        if handle.poll() is None:
            handle.terminate()
    time.sleep(2)
    for nome, handle in _handles.items():
        if handle.poll() is None:
            handle.kill()
    log.info("Todos os processos encerrados.")


def _ao_receber_sinal(sig, frame):
    _parar_tudo()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, _ao_receber_sinal)
    signal.signal(signal.SIGTERM, _ao_receber_sinal)

    for nome in PROCESSOS:
        _iniciar(nome)

    log.info("Supervisor ativo — monitorando todos os processos a cada 10s.")

    while not _encerrando:
        time.sleep(INTERVALO_VERIFICACAO_SEGUNDOS)
        for nome, handle in list(_handles.items()):
            if handle.poll() is not None:  # processo caiu
                if _reinicios_na_ultima_hora(nome) >= LIMITE_REINICIOS_POR_HORA:
                    log.error(
                        f"Processo '{nome}' caiu {LIMITE_REINICIOS_POR_HORA}+ vezes na última hora. "
                        f"Parei de reiniciar automaticamente — verifique os logs em data/logs/{nome}.log"
                    )
                    continue
                log.warning(f"Processo '{nome}' caiu (código {handle.returncode}). Reiniciando...")
                _contagem_reinicios[nome].append(time.time())
                _iniciar(nome)


if __name__ == "__main__":
    main()
