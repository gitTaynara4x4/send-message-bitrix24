import os
import requests
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from dotenv import load_dotenv
from dateutil import parser

try:
    from zoneinfo import ZoneInfo  
except ImportError:
    from zoneinfo import ZoneInfo


load_dotenv()

app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()


BITRIX_WEBHOOK_BASE = "https://marketingsolucoes.bitrix24.com.br/rest/5332/8zyo7yj1ry4k59b5/crm.deal.get"
URL_VPS = os.getenv("URL_VPS")  
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

def get_deal_data(deal_id):
    """Busca dados do negócio no Bitrix"""
    try:
        res = requests.get(f"{BITRIX_WEBHOOK_BASE}?id={deal_id}")
        res.raise_for_status()
        return res.json().get("result")
    except Exception as e:
        print(f"Erro ao buscar negócio: {e}")
        return None

def schedule_workflows(deal_id, data_agendamento_str):
    """Agenda os dois workflows nos horários corretos"""
    try:
        # Converte string com timezone para datetime no fuso de Brasília
        data_agendamento = parser.parse(data_agendamento_str).astimezone(BRAZIL_TZ)

        # Define os horários-alvo
        hora_20h_dia_anterior = datetime.combine(data_agendamento.date() - timedelta(days=1),
                                                 datetime.min.time(), tzinfo=BRAZIL_TZ) + timedelta(hours=20)
        hora_8h_do_dia = datetime.combine(data_agendamento.date(),
                                          datetime.min.time(), tzinfo=BRAZIL_TZ) + timedelta(hours=8)

        print(f"📅 Agendado 20h anterior: {hora_20h_dia_anterior}")
        print(f"📅 Agendado 8h do dia:    {hora_8h_do_dia}")

        # Agenda workflow das 20h
        scheduler.add_job(lambda: requests.get(f"{URL_VPS}/webhook/workflow_8danoite?deal_id={deal_id}"),
                          trigger='date', run_date=hora_20h_dia_anterior,
                          id=f"workflow_20h_{deal_id}", replace_existing=True)

        # Agenda workflow das 8h
        scheduler.add_job(lambda: requests.get(f"{URL_VPS}/webhook/workflow_8damanha?deal_id={deal_id}"),
                          trigger='date', run_date=hora_8h_do_dia,
                          id=f"workflow_8h_{deal_id}", replace_existing=True)

    except Exception as e:
        print(f"❌ Erro ao agendar workflows: {e}")

@app.route("/agendar_workflows/<int:deal_id>", methods=["GET"])
def agendar(deal_id):
    """Endpoint para agendar os workflows com base no negócio"""
    deal = get_deal_data(deal_id)
    if not deal:
        return jsonify({"error": "Negócio não encontrado"}), 404

    data_agendamento = deal.get("UF_CRM_1698761052502")
    if not data_agendamento:
        return jsonify({"error": "Campo de agendamento não encontrado"}), 400

    schedule_workflows(deal_id, data_agendamento)
    return jsonify({"message": "Workflows agendados com sucesso"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1444)
