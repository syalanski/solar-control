import os
import requests
import time
from flask import Flask, render_template_string, request, redirect, url_for
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ========================= ХУАВЕЙ API НАСТРОЙКИ =========================
# Използваме твоите нови администраторски данни
HUAWEI_URL = "https://eu5.fusionsolar.huawei.com:31943"
HUAWEI_USER = "Stako123"
HUAWEI_PASS = "PV123456"

PLANT_IDS = {
    "sliven": "NE=135069924"
}
# =======================================================================

status_db = {
    "sliven": {"limit": "100%", "schedule": "Няма", "last_action": "Няма"}
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
        .last-action { font-size: 0.8rem; color: #95a5a6; margin-top: 10px; font-style: italic; }
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
            <div class="last-action">Статус: {{ sliven.last_action }}</div>
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
        print(f"Опит за логване в Huawei API с потребител: {HUAWEI_USER}...")
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        
        if data.get("failCode") == 0:
            token = response.headers.get("X-SRM-TOKEN")
            if token:
                print("Логването е успешно. Токенът е получен.")
                return token
        
        msg = data.get('message', 'Неизвестна грешка')
        print(f"Грешка при логване: {msg}")
        return None
    except Exception as e:
        print(f"Критична грешка при връзка с Huawei: {e}")
        return None

def set_plant_limit(plant_key, limit_percent):
    token = huawei_login()
    if not token:
        return False, "Грешка при автентификация - провери потребителското име и паролата"

    plant_id = PLANT_IDS.get(plant_key)
    if not plant_id:
        return False, "Невалидно ID на соларната централа"

    url = f"{HUAWEI_URL}/thirdData/setPlantLimit"
    payload = {
        "plantId": plant_id,
        "limit": int(limit_percent)
    }
    headers = {
        'Content-Type': 'application/json',
        'X-SRM-TOKEN': token
    }

    try:
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        
        if data.get("failCode") == 0:
            print(f"Успешно зададен лимит от {limit_percent}% за {plant_key}.")
            return True, "Успешно изпълнено"
        
        return False, data.get("message", "Huawei отказа промяната")
    except Exception as e:
        return False, f"Грешка при заявката: {str(e)}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, sliven=status_db["sliven"])

@app.route('/limit/<plant_key>/<limit>')
def change_limit(plant_key, limit):
    success, message = set_plant_limit(plant_key, limit)
    if success:
        status_db[plant_key]["limit"] = f"{limit}%"
        status_db[plant_key]["schedule"] = "Ръчно зададен"
        status_db[plant_key]["last_action"] = f"Успех в {time.strftime('%H:%M:%S')}"
    else:
        status_db[plant_key]["last_action"] = f"Грешка: {message}"
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
