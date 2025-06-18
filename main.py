import os
import requests
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, time
from dotenv import load_dotenv
from dateutil import parser
import logging

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  

load_dotenv()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

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
        return res.json().get("result")
    except Exception as e:
        app.logger.error(f"❌ Erro ao buscar negócio: {e}")
        return None


def schedule_workflows(deal_id, data_agendamento_str):
    """Agenda os workflows para 20h do dia anterior e 8h do próprio dia"""
    try:
        app.logger.info(f"📥 Data agendamento recebida: {data_agendamento_str}")

        try:
            data_agendamento = parser.parse(data_agendamento_str)
            data_agendamento = data_agendamento.replace(tzinfo=None).replace(tzinfo=BRAZIL_TZ)
        except Exception as e:
            app.logger.error(f"❌ Erro ao converter data: {e}")
            return

        hora_20h_dia_anterior = datetime.combine(
            data_agendamento.date() - timedelta(days=1),
            time(hour=20, minute=0),
            tzinfo=BRAZIL_TZ
        )
        
        hora_8h_do_dia = datetime.combine(
            data_agendamento.date(),
            time(hour=8, minute=0),
            tzinfo=BRAZIL_TZ
        )

        app.logger.info(f"📅 Horário 20h do dia anterior: {hora_20h_dia_anterior}")
        app.logger.info(f"📅 Horário 8h do dia do agendamento: {hora_8h_do_dia}")

        agora = datetime.now(BRAZIL_TZ)
        app.logger.info(f"⏳ Agora: {agora}")

        # Agendamento para 20h do dia anterior
        if hora_20h_dia_anterior < agora:
            app.logger.warning("⚠️ Horário 20h do dia anterior já passou.")
        else:
            app.logger.info("📌 Agendando workflow para 20h do dia anterior...")
            scheduler.add_job(
                lambda: requests.post(f"{URL_VPS}/webhook/workflow_8danoite", json={"deal_id": deal_id}),
                trigger='date',
                run_date=hora_20h_dia_anterior,
                id=f"workflow_20h_{deal_id}",
                replace_existing=True
            )

        # Agendamento para 8h do dia
        if hora_8h_do_dia < agora:
            app.logger.warning("⚠️ Horário 8h do dia já passou.")
        else:
            app.logger.info("📌 Agendando workflow para 8h do dia do agendamento...")
            scheduler.add_job(
                lambda: requests.post(f"{URL_VPS}/webhook/workflow_8damanha", json={"deal_id": deal_id}),
                trigger='date',
                run_date=hora_8h_do_dia,
                id=f"workflow_8h_{deal_id}",
                replace_existing=True
            )

    except Exception as e:
        app.logger.error(f"❌ Erro ao agendar workflows: {e}")


@app.route("/agendar_workflows", methods=["POST"])
def agendar():
    """Endpoint POST que agenda workflows com base no deal_id enviado via JSON"""
    data = request.get_json()
    deal_id = data.get("deal_id")

    if not deal_id:
        app.logger.warning("🚫 Parâmetro 'deal_id' ausente no corpo da requisição.")
        return jsonify({"error": "Parâmetro 'deal_id' é obrigatório"}), 400

    app.logger.info(f"📲 Requisição recebida para agendar workflows para o negócio ID: {deal_id}")

    deal = get_deal_data(deal_id)
    if not deal:
        app.logger.warning(f"🚫 Negócio não encontrado para ID {deal_id}")
        return jsonify({"error": "Negócio não encontrado"}), 404

    data_agendamento = deal.get("UF_CRM_1698761052502")
    app.logger.info(f"🧾 Campo UF_CRM_1698761052502 (data de agendamento): {data_agendamento}")

    if not data_agendamento:
        app.logger.warning("🚫 Campo de agendamento não encontrado no negócio")
        return jsonify({"error": "Campo de agendamento não encontrado"}), 400

    schedule_workflows(deal_id, data_agendamento)
    return jsonify({"message": "Workflows agendados com sucesso"}), 200


if __name__ == "__main__":
    app.logger.info("🚀 Servidor iniciando na porta 1444...")
    app.run(host="0.0.0.0", port=1444)
