import os
import time
from flask import Flask, render_template_string, request, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# ========================= ХУАВЕЙ БОТ НАСТРОЙКИ =========================
HUAWEI_WEB_URL = "https://eu5.fusionsolar.huawei.com/"
HUAWEI_USER = "Stako123"
HUAWEI_PASS = "PV123456"

# ID на централата от уеб URL-а
PLANT_ID = "135069924" 
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
    <title>Бот Контрол на Соларни Централи</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #2c3e50; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;}
        h1 { color: #ecf0f1; font-size: 1.5rem; margin-bottom: 20px; }
        .plants-container { display: flex; flex-direction: column; gap: 20px; width: 100%; max-width: 500px; }
        .plant-card { background-color: #34495e; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center;}
        .plant-name { font-size: 1.2rem; font-weight: bold; color: #1abc9c; margin-bottom: 10px; }
        .status { font-size: 0.9rem; color: #bdc3c7; margin-bottom: 15px; }
        .last-action { font-size: 0.8rem; color: #ecf0f1; margin-top: 10px; font-style: italic; background: #c0392b; padding: 5px; border-radius: 3px; }
        .btn-group { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }
        .btn { padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; color: white; font-weight: bold; font-size: 0.9rem; text-decoration: none; transition: background-color 0.3s; flex: 1 0 calc(33.33% - 10px); max-width: 100px; text-align: center; }
        .btn-0 { background-color: #e74c3c; } .btn-0:hover { background-color: #c0392b; }
        .btn-50 { background-color: #f39c12; } .btn-50:hover { background-color: #d35400; }
        .btn-100 { background-color: #2ecc71; } .btn-100:hover { background-color: #27ae60; }
    </style>
</head>
<body>
    <h1>Бот Управление на Производството</h1>
    <div class="plants-container">
        <div class="plant-card">
            <div class="plant-name">ФТВ Сливен</div>
            <div class="status">Лимит: {{ sliven.limit }} | График: {{ sliven.schedule }}</div>
            <div class="btn-group">
                <a href="/limit/sliven/0" class="btn btn-0">0%</a>
                <a href="/limit/sliven/50" class="btn btn-50">50%</a>
                <a href="/limit/sliven/100" class="btn btn-100">100%</a>
            </div>
            <div class="last-action">{{ sliven.last_action }}</div>
        </div>
    </div>
</body>
</html>
"""

def run_browser_bot(limit_percent):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Скрит режим за работа на сървъра
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("Ботът отваря сайта на Huawei...")
        driver.get(HUAWEI_WEB_URL)
        
        # Попълване на формата за вход
        user_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], #userid")))
        pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], #password")
        login_btn = driver.find_element(By.CSS_SELECTOR, "button, #btnLogin")
        
        user_field.send_keys(HUAWEI_USER)
        pass_field.send_keys(HUAWEI_PASS)
        print("Кликване на бутона за вход...")
        login_btn.click()
        
        # Изчакваме малко да зареди вътрешната страница
        time.sleep(5)
        
        # Проверка дали сме вътре
        if "login" in driver.current_url.lower():
            return False, "Неуспешен вход. Вероятно има CAPTCHA защита на сайта."

        print("Успешен вход! Навигиране към настройките на мощността...")
        # Директно скачаме на страницата за управление на мощността чрез ID-то на централата
        driver.get(f"https://eu5.fusionsolar.huawei.com/netecowebext/pages/views/business/neteco/dms/stationControl/stationControl.html?stationId={PLANT_ID}")
        time.sleep(5)
        
        # Тук ботът вече е на страницата.
        print("Ботът зареди настройките успешно!")
        return True, "Ботът се логна и отвори настройките успешно!"
        
    except Exception as e:
        print(f"Грешка при бота: {str(e)}")
        return False, f"Бот грешка: {str(e)}"
    finally:
        driver.quit()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, sliven=status_db["sliven"])

@app.route('/limit/<plant_key>/<limit>')
def change_limit(plant_key, limit):
    status_db[plant_key]["last_action"] = "Ботът работи в момента..."
    success, message = run_browser_bot(limit)
    
    if success:
        status_db[plant_key]["limit"] = f"{limit}%"
        status_db[plant_key]["schedule"] = "Ръчно (Бот)"
        status_db[plant_key]["last_action"] = f"Последно: {message} в {time.strftime('%H:%M:%S')}"
    else:
        status_db[plant_key]["last_action"] = f"Грешка: {message}"
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
