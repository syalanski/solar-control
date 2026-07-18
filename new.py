import os
import requests
import time
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# ==================== ХУАВЕЙ API НАСТРОЙКИ ====================
HUAWEI_URL = "https://intl.fusionsolar.huawei.com"  
HUAWEI_USER = "solar_service_bot"
HUAWEI_PASS = "SolarControl2026!"

# Напълно реалните ID-та на твоите две централи!
PLANT_IDS = {
    "sliven": "NE=135069924",              # ТОВА Е РЕАЛНОТО ID ЗА СЛИВЕН (ФТВ)!
    "bel_kladenec": "NE=135112688"        # ТОВА Е РЕАЛНОТО ID ЗА ПЕТРО!
}
# ==============================================================

status_db = {
    "sliven": {"limit": "100%", "schedule": "Няма"},
    "bel_kladenec": {"limit": "100%", "schedule": "Няма"}
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solar Service Control</title>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #e0e0e0; text-align: center; padding: 20px; }
        .card { background: #1e1e1e; padding: 20px; margin: 15px auto; border-radius: 10px; max-width: 400px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
        h1 { color: #ff9800; }
        h2 { margin-top: 0; color: #00e676; }
        .btn { display: inline-block; background: #333; color: white; padding: 12px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; font-size: 16px; font-weight: bold; }
        .btn-green { background: #4caf50; }
        .btn-red { background: #f44336; }
        .btn-orange { background: #ff9800; }
        input[type="time"] { padding: 10px; margin: 10px 0; width: 80%; border-radius: 5px; border: 1px solid #444; background: #222; color: white; font-size: 16px; }
    </style>
</head>
<body>
    <h1>Solar Service</h1>
    <p>Управление на централите директно през API</p>
    
    <div class="card">
        <h2>Сливен (ФТВ)</h2>
        <p>Текущ лимит: <strong>{{ status['sliven']['limit'] }}</strong></p>
        <p>Активен график: <strong>{{ status['sliven']['schedule'] }}</strong></p>
        <a href="/limit/sliven/0" class="btn btn-red">0%</a>
        <a href="/limit/sliven/50" class="btn btn-orange">50%</a>
        <a href="/limit/sliven/100" class="btn btn-green">100%</a>
        
        <form action="/schedule/sliven" method="POST" style="margin-top: 15px;">
            <input type="time" name="time_end" required>
            <button type="submit" class="btn">Задай 0% до час</button>
        </form>
    </div>

    <div class="card">
        <h2>Бял Кладенец (Петро)</h2>
        <p>Текущ лимит: <strong>{{ status['bel_kladenec']['limit'] }}</strong></p>
        <p>Активен график: <strong>{{ status['bel_kladenec']['schedule'] }}</strong></p>
        <a href="/limit/bel_kladenec/0" class="btn btn-red">0%</a>
        <a href="/limit/bel_kladenec/30" class="btn btn-orange">30%</a>
        <a href="/limit/bel_kladenec/100" class="btn btn-green">100%</a>
    </div>
</body>
</html>
"""

def set_huawei_limit(plant_key, percent):
    plant_id = PLANT_IDS.get(plant_key)
    try:
        # 1. Логване в OpenAPI
        login_url = f"{HUAWEI_URL}/thirdData/login"
        login_data = {"userName": HUAWEI_USER, "systemCode": HUAWEI_PASS}
        
        login_res = requests.post(login_url, json=login_data, timeout=10)
        token = login_res.headers.get("X-SRM-TOKEN")
        
        if not token:
            print(f"Грешка: Неуспешно логване за {plant_key}")
            return False
            
        # 2. Изпращане на команда за ограничение
        cmd_url = f"{HUAWEI_URL}/thirdData/setPlantActPower"
        headers = {"X-SRM-TOKEN": token, "Content-Type": "application/json"}
        
        cmd_data = {
            "plantOpenId": plant_id,
            "strategy": 1,          
            "actPowerCap": percent  
        }
        
        response = requests.post(cmd_url, json=cmd_data, headers=headers, timeout=10)
        res_json = response.json()
        
        if res_json.get("success") or res_json.get("code") == 0:
            print(f"Успех! {plant_key} е лимитирана на {percent}%")
            return True
        else:
            print(f"Huawei отказа командата за {plant_key}: {res_json}")
            return False
            
    except Exception as e:
        print(f"API Грешка: {e}")
        return False

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, status=status_db)

@app.route('/limit/<plant_name>/<int:percent>')
def limit(plant_name, percent):
    success = set_huawei_limit(plant_name, percent)
    if success:
        status_db[plant_name]['limit'] = f"{percent}%"
        if percent == 100:
            status_db[plant_name]['schedule'] = "Няма"
    return redirect(url_for('home'))

@app.route('/schedule/<plant_name>', methods=['POST'])
def schedule(plant_name):
    time_end = request.form.get('time_end')
    success = set_huawei_limit(plant_name, 0)
    if success:
        status_db[plant_name]['limit'] = "0%"
        status_db[plant_name]['schedule'] = f"Лимит 0% до {time_end} ч."
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
