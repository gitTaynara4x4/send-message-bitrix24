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

print("🔄 Carregando variáveis de ambiente...")
load_dotenv()

app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()

print("⚙️ Scheduler iniciado!")

BITRIX_WEBHOOK_BASE = "https://marketingsolucoes.bitrix24.com.br/rest/5332/8zyo7yj1ry4k59b5/crm.deal.get"
URL_VPS = os.getenv("URL_VPS")
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

def get_deal_data(deal_id):
    """Busca dados do negócio no Bitrix"""
    try:
        print(f"🔍 Buscando dados do negócio ID: {deal_id}")
        res = requests.get(f"{BITRIX_WEBHOOK_BASE}?id={deal_id}")
        res.raise_for_status()
        result = res.json().get("result")
        print(f"✅ Dados do negócio recebidos: {result}")
        return result
    except Exception as e:
        print(f"❌ Erro ao buscar negócio: {e}")
        return None

def schedule_workflows(deal_id, data_agendamento_str):
    """Agenda os dois workflows nos horários corretos"""
    try:
        print(f"📥 Data agendamento bruta recebida: {data_agendamento_str}")
        data_agendamento = parser.parse(data_agendamento_str).astimezone(BRAZIL_TZ)
        print(f"🕐 Data agendamento convertida: {data_agendamento}")

        hora_20h_dia_anterior = datetime.combine(data_agendamento.date() - timedelta(days=1),
                                                 datetime.min.time(), tzinfo=BRAZIL_TZ) + timedelta(hours=20)
        hora_8h_do_dia = datetime.combine(data_agendamento.date(),
                                          datetime.min.time(), tzinfo=BRAZIL_TZ) + timedelta(hours=8)

        print(f"📅 Horário 20h do dia anterior: {hora_20h_dia_anterior}")
        print(f"📅 Horário 8h do dia do agendamento: {hora_8h_do_dia}")

        agora = datetime.now(BRAZIL_TZ)
        print(f"⏳ Agora: {agora}")

        if hora_20h_dia_anterior < agora:
            print(f"⚠️ Aviso: horário 20h do dia anterior já passou, não será agendado.")
        else:
            print(f"📌 Agendando workflow das 20h...")
            scheduler.add_job(lambda: requests.get(f"{URL_VPS}/webhook/workflow_8danoite?deal_id={deal_id}"),
                              trigger='date', run_date=hora_20h_dia_anterior,
                              id=f"workflow_20h_{deal_id}", replace_existing=True)

        if hora_8h_do_dia < agora:
            print(f"⚠️ Aviso: horário 8h do dia já passou, não será agendado.")
        else:
            print(f"📌 Agendando workflow das 8h...")
            scheduler.add_job(lambda: requests.get(f"{URL_VPS}/webhook/workflow_8damanha?deal_id={deal_id}"),
                              trigger='date', run_date=hora_8h_do_dia,
                              id=f"workflow_8h_{deal_id}", replace_existing=True)

    except Exception as e:
        print(f"❌ Erro ao agendar workflows: {e}")

@app.route("/agendar_workflows/<int:deal_id>", methods=["GET"])
def agendar(deal_id):
    """Endpoint para agendar os workflows com base no negócio"""
    print(f"📲 Requisição recebida para agendar workflows para o negócio ID: {deal_id}")
    deal = get_deal_data(deal_id)
    if not deal:
        print(f"🚫 Negócio não encontrado para ID {deal_id}")
        return jsonify({"error": "Negócio não encontrado"}), 404

    data_agendamento = deal.get("UF_CRM_1698761052502")
    print(f"🧾 Campo UF_CRM_1698761052502 (data de agendamento): {data_agendamento}")
    if not data_agendamento:
        print(f"🚫 Campo de agendamento não encontrado no negócio")
        return jsonify({"error": "Campo de agendamento não encontrado"}), 400

    schedule_workflows(deal_id, data_agendamento)
    print(f"✅ Agendamento concluído para o negócio ID: {deal_id}")
    return jsonify({"message": "Workflows agendados com sucesso"}), 200

if __name__ == "__main__":
    print("🚀 Servidor iniciado na porta 1444...")
    app.run(host="0.0.0.0", port=1444)
