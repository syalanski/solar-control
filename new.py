import os
import requests
import datetime
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# Твоите данни за Huawei OpenAPI
HUAWEI_URL = "https://uni003eu5.fusionsolar.huawei.com" # Провери адреса си!
HUAWEI_USER = "solar_service_bot"
HUAWEI_PASS = "SolarBot2026!"

# Лесна парола за достъп до твоя уебсайт, за да е защитен
ACCESS_PASSWORD = "mania" 

# Проста база данни в паметта за текущите лимити и графици
status_db = {
    "sliven": {"limit": "100%", "schedule": "Няма"},
    "bel_kladenec": {"limit": "100%", "schedule": "Няма"}
}

# HTML дизайн за твоя телефон (лек, тъмен режим, големи бутони)
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
        input[type="text"], input[type="time"] { padding: 10px; margin: 10px 0; width: 80%; border-radius: 5px; border: 1px solid #444; background: #222; color: white; font-size: 16px; }
    </style>
</head>
<body>
    <h1>Solar Service</h1>
    <p>Управление на централите директно през API</p>
    
    <div class="card">
        <h2>Сливен</h2>
        <p>Текущ лимит: <strong>{{ status['sliven']['limit'] }}</strong></p>
        <p>Активен график: <strong>{{ status['sliven']['schedule'] }}</strong></p>
        <a href="/limit/sliven/0" class="btn btn-red">0%</a>
        <a href="/limit/sliven/50" class="btn btn-orange">50%</a>
        <a href="/limit/sliven/100" class="btn btn-green">100%</a>
        
        <form action="/schedule/sliven" method="POST" style="margin-top: 15px;">
            <input type="time" name="time_end" required>
            <input type="hidden" name="percent" value="0">
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

def set_huawei_limit(plant_id, percent):
    # Тук се интегрира твоята оригинална функция за заявка към Huawei API
    # Логване, взимане на токен и изпращане на "setPlantActPower"
    print(f"Изпращане на команда към Huawei: {plant_id} -> {percent}%")
    # За целите на теста връщаме True
    return True

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
    percent = request.form.get('percent', 0)
    
    # Слагаме веднага лимита на 0%
    set_huawei_limit(plant_name, percent)
    status_db[plant_name]['limit'] = f"{percent}%"
    status_db[plant_name]['schedule'] = f"Лимит {percent}% до {time_end} ч."
    
    # Бележка: За автоматичното вдигане в облака се ползва заден фонов процес (Celery/APScheduler), 
    # който ще добавим, когато го качим онлайн.
    
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
