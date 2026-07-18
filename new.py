import os
import requests
import time
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# ========================= ХУАВЕЙ API НАСТРОЙКИ =========================
HUAWEI_URL = "https://eu5.fusionsolar.huawei.com/"
HUAWEI_USER = "solar_service_bot"
HUAWEI_PASS = "SolarControl2026!"

PLANT_IDS = {
    "sliven": "NE=135069924",
    "bel_kladenec": "NE=135112688"
}
# =======================================================================

status_db = {
    "sliven": {"limit": "100%", "schedule": "Няма"},
    "bel_kladenec": {"limit": "100%", "schedule": "Няма"}
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bg">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Контрол на Соларни Централи</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #2c3e50; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;}
        h1 { color: #ecf0f1; font-size: 1.5rem; margin-bottom: 20px; }
        .plants-container { display: flex; flex-direction: column; gap: 20px; width: 100%; max-width: 500px; }
        .plant-card { background-color: #34495e; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center;}
        .plant-name { font-size: 1.2rem; font-weight: bold; color: #1abc9c; margin-bottom: 10px; }
        .status { font-size: 0.9rem; color: #bdc3c7; margin-bottom: 15px; }
        .btn-group { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }
        .btn { padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; color: white; font-weight: bold; font-size: 0.9rem; text-decoration: none; transition: background-color 0.3s; flex: 1 0 calc(33.33% - 10px); max-width: 100px; text-align: center; }
        .btn-0 { background-color: #e74c3c; } .btn-0:hover { background-color: #c0392b; }
        .btn-50 { background-color: #f39c12; } .btn-50:hover { background-color: #d35400; }
        .btn-100 { background-color: #2ecc71; } .btn-100:hover { background-color: #27ae60; }
        @media (max-width: 400px) { h1 { font-size: 1.2rem; } .plant-name { font-size: 1rem; } .btn { font-size: 0.8rem; padding: 8px 10px; } }
    </style>
</head>
<body>
    <h1>Управление на Производството</h1>
    <div class="plants-container">
        <div class="plant-card">
            <div class="plant-name">ФТВ Сливен</div>
            <div class="status">Лимит: {{ sliven.limit }} | График: {{ sliven.schedule }}</div>
            <div class="btn-group">
                <a href="/limit/sliven/0" class="btn btn-0">0%</a>
                <a href="/limit/sliven/50" class="btn btn-50">50%</a>
                <a href="/limit/sliven/100" class="btn btn-100">100%</a>
            </div>
        </div>
        <div class="plant-card">
            <div class="plant-name">Петро Бял Кладенец</div>
            <div class="status">Лимит: {{ bel_kladenec.limit }} | График: {{ bel_kladenec.schedule }}</div>
            <div class="btn-group">
                <a href="/limit/bel_kladenec/0" class="btn btn-0">0%</a>
                <a href="/limit/bel_kladenec/50" class="btn btn-50">50%</a>
                <a href="/limit/bel_kladenec/100" class="btn btn-100">100%</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

def huawei_login():
    url = f"{HUAWEI_URL}/thirdData/login"
  payload = {
        "userName": HUAWEI_USER,
        "systemCode": HUAWEI_PASS
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("failCode") == 0:
            token = response.headers.get("X-SRM-TOKEN")
            if token:
                print("Логването успешно. Токен получен.")
                return token
        print(f"Грешка: Неуспешно логване. Huawei върна: {data.get('message', data)}")
    except Exception as e:
        print(f"Грешка при логване: {e}")
    return None

def set_plant_limit(plant_key, limit_percent):
    token = huawei_login()
    if not token:
        return False, "Грешка при логване в Huawei"

    plant_id = PLANT_IDS.get(plant_key)
    if not plant_id:
        return False, "Централата не е намерена"

    url = f"{HUAWEI_URL}/thirdData/setPlantLimit"
    payload = {
        "plantId": plant_id,
        "limit": limit_percent
    }
    headers = {
        'Content-Type': 'application/json',
        'X-SRM-TOKEN': token
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("failCode") == 0:
            print(f"Лимитът за {plant_key} е зададен успешно на {limit_percent}%.")
            return True, "Успешно"
        print(f"Грешка от Huawei при лимит за {plant_key}: {data.get('message', data)}")
        return False, data.get("message", "Неизвестна грешка")
    except Exception as e:
        print(f"Грешка при заявка за лимит: {e}")
        return False, str(e)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, sliven=status_db["sliven"], bel_kladenec=status_db["bel_kladenec"])

@app.route('/limit/<plant_key>/<limit>')
def change_limit(plant_key, limit):
    success, message = set_plant_limit(plant_key, limit)
    if success:
        status_db[plant_key]["limit"] = f"{limit}%"
        status_db[plant_key]["schedule"] = "Ръчно зададен"
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
