"""
Agendador de tarefas recorrentes.
Nesta fase, cuida do envio automático do relatório diário para você.
Nas próximas fases, também vai disparar as publicações programadas
(status, canal do WhatsApp, Instagram, LinkedIn).

Rodar em paralelo ao núcleo principal: python -m src.scheduler
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from src.database import relatorio_do_dia, init_db
from src.notificacoes import notificar_relatorio_diario
from src.publicador import publicar_proximo
from src.logging_config import get_logger
import shutil
import os
import datetime
from src.config import DB_PATH

log = get_logger("agendador")
init_db()
scheduler = BlockingScheduler(timezone="America/Sao_Paulo")


@scheduler.scheduled_job("cron", hour=20, minute=0)
def enviar_relatorio_diario():
    relatorio = relatorio_do_dia()
    enviado = notificar_relatorio_diario(relatorio)
    status = "enviado" if enviado else "falhou ao enviar (verifique a ponte do WhatsApp)"
    log.info(f"Relatório diário {status}: {relatorio}")


@scheduler.scheduled_job("cron", hour=3, minute=0)
def backup_diario():
    """
    Backup automático do banco de dados todo dia às 3h da manhã (fora do horário
    comercial). Mantém os últimos 14 backups — os mais antigos são removidos
    automaticamente para não encher o disco.
    """
    try:
        pasta_backup = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(pasta_backup, exist_ok=True)
        nome = f"sofhie_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        destino = os.path.join(pasta_backup, nome)

        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, destino)
            log.info(f"Backup automático criado: {nome}")

            backups = sorted(
                [f for f in os.listdir(pasta_backup) if f.startswith("sofhie_backup_")]
            )
            for antigo in backups[:-14]:
                os.remove(os.path.join(pasta_backup, antigo))
        else:
            log.warning("Backup automático pulado — banco de dados ainda não existe.")
    except Exception as e:
        log.error(f"Falha ao criar backup automático: {e}")


# ---------- Publicações programadas ----------
# WhatsApp status + canal: volume alto é seguro via API oficial de status/canal —
# distribuído ao longo do dia, em vez de tudo de uma vez.
HORARIOS_WHATSAPP_STATUS = [8, 10, 12, 14, 16, 18, 20, 21]  # 8x/dia, como planejado

for hora in HORARIOS_WHATSAPP_STATUS:
    scheduler.add_job(
        publicar_proximo, "cron", hour=hora, minute=5, args=["whatsapp_status"],
        id=f"whatsapp_status_{hora}h",
    )

scheduler.add_job(
    publicar_proximo, "cron", hour=9, minute=0, args=["whatsapp_canal"], id="whatsapp_canal_manha"
)
scheduler.add_job(
    publicar_proximo, "cron", hour=17, minute=0, args=["whatsapp_canal"], id="whatsapp_canal_tarde"
)

scheduler.add_job(
    publicar_proximo, "cron", hour=11, minute=0, args=["instagram"], id="instagram_manha"
)
scheduler.add_job(
    publicar_proximo, "cron", hour=19, minute=0, args=["instagram"], id="instagram_noite"
)

# LinkedIn: reduzido para 1x/dia por segurança (decisão registrada no projeto) —
# volume alto automatizado é penalizado pela própria plataforma.
scheduler.add_job(
    publicar_proximo, "cron", hour=9, minute=30, args=["linkedin"], id="linkedin_diario"
)


if __name__ == "__main__":
    log.info("Agendador rodando — relatório diário às 20h, backup automático às 3h.")
    scheduler.start()
