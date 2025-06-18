import os
import requests
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from dotenv import load_dotenv
from dateutil import parser
import logging

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from zoneinfo import ZoneInfo

load_dotenv()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)  # <--- garante que logs INFO apareçam
scheduler = BackgroundScheduler()
scheduler.start()

BITRIX_WEBHOOK_BASE = "https://marketingsolucoes.bitrix24.com.br/rest/5332/8zyo7yj1ry4k59b5/crm.deal.get"
URL_VPS = os.getenv("URL_VPS")
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def get_deal_data(deal_id):
    """Busca dados do negócio no Bitrix"""
    try:
        app.logger.info(f"🔍 Buscando dados do negócio ID: {deal_id}")
        res = requests.get(f"{BITRIX_WEBHOOK_BASE}?id={deal_id}")
        res.raise_for_status()
        result = res.json().get("result")
        return result
    except Exception as e:
        app.logger.error(f"❌ Erro ao buscar negócio: {e}")
        return None


def schedule_workflows(deal_id, data_agendamento_str):
    """Agenda os dois workflows nos horários corretos"""
    try:
        app.logger.info(f"📥 Data agendamento bruta recebida: {data_agendamento_str}")

        try:
            data_agendamento = parser.parse(data_agendamento_str)
            app.logger.info(f"📆 Data agendamento antes de timezone: {data_agendamento}")
            data_agendamento = data_agendamento.astimezone(BRAZIL_TZ)
        except Exception as e:
            app.logger.error(f"❌ Erro ao converter data: {e}")
            return

        app.logger.info(f"📆 Data de agendamento formatada: {data_agendamento.strftime('%d/%m/%Y %H:%M:%S')}")
        app.logger.info(f"🕐 Data agendamento convertida: {data_agendamento}")

        # Define os horários-alvo
        hora_20h_dia_anterior = datetime.combine(
            data_agendamento.date() - timedelta(days=1),
            datetime.min.time(),
            tzinfo=BRAZIL_TZ
        ) + timedelta(hours=20)

        hora_8h_do_dia = datetime.combine(
            data_agendamento.date(),
            datetime.min.time(),
            tzinfo=BRAZIL_TZ
        ) + timedelta(hours=8)

        app.logger.info(f"📅 Horário 20h do dia anterior: {hora_20h_dia_anterior}")
        app.logger.info(f"📅 Horário 8h do dia do agendamento: {hora_8h_do_dia}")

        agora = datetime.now(BRAZIL_TZ)
        app.logger.info(f"⏳ Agora: {agora}")

        if hora_20h_dia_anterior < agora:
            app.logger.warning("⚠️ Aviso: horário 20h do dia anterior já passou, não será agendado.")
        else:
            app.logger.info("📌 Agendando workflow das 20h...")
            scheduler.add_job(
                lambda: requests.get(f"{URL_VPS}/webhook/workflow_8danoite?deal_id={deal_id}"),
                trigger='date',
                run_date=hora_20h_dia_anterior,
                id=f"workflow_20h_{deal_id}",
                replace_existing=True
            )

        if hora_8h_do_dia < agora:
            app.logger.warning("⚠️ Aviso: horário 8h do dia já passou, não será agendado.")
        else:
            app.logger.info("📌 Agendando workflow das 8h...")
            scheduler.add_job(
                lambda: requests.get(f"{URL_VPS}/webhook/workflow_8damanha?deal_id={deal_id}"),
                trigger='date',
                run_date=hora_8h_do_dia,
                id=f"workflow_8h_{deal_id}",
                replace_existing=True
            )

    except Exception as e:
        app.logger.error(f"❌ Erro ao agendar workflows: {e}")


@app.route("/agendar_workflows/<int:deal_id>", methods=["GET"])
def agendar(deal_id):
    """Endpoint para agendar os workflows com base no negócio"""
    app.logger.info(f"📲 Requisição recebida para agendar workflows para o negócio ID: {deal_id}")
    deal = get_deal_data(deal_id)
    if not deal:
        app.logger.warning(f"🚫 Negócio não encontrado para ID {deal_id}")
        return jsonify({"error": "Negócio não encontrado"}), 404

    data_agendamento = deal.get("UF_CRM_1698761052502")
    app.logger.info(f"🧾 Campo UF_CRM_1698761052502 (data de agendamento): {data_agendamento}")
    if not data_agendamento:
        app.logger.warning(f"🚫 Campo de agendamento não encontrado no negócio")
        return jsonify({"error": "Campo de agendamento não encontrado"}), 400

    schedule_workflows(deal_id, data_agendamento)
    return jsonify({"message": "Workflows agendados com sucesso"}), 200


if __name__ == "__main__":
    app.logger.info("🚀 Servidor iniciando na porta 1444...")
    app.run(host="0.0.0.0", port=1444)
