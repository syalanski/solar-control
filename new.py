import json
from datetime import datetime
from flask import Flask, jsonify, request
import pytz
import requests

app = Flask(__name__)

bg_tz = pytz.timezone('Europe/Sofia')

schedule_config = {
    'enabled': False,
    'time_0kw': '14:00',
    'time_30kw': '14:30',
    'last_action': 'Няма активен график',
    'executed_today_0kw': False,
    'executed_today_30kw': False,
}


def send_fusionsolar_power_limit_kw(kw_value):
  url = 'https://uni003eu5.fusionsolar.huawei.com/rest/neteco/config/device/v1/config/power-control'

  payload = {
      'dn': 'NE=135329489',
      'changeValues': json.dumps([{'id': '21003', 'value': kw_value}]),
  }

  headers = {
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'Accept-Language': 'bg-BG,bg;q=0.9,en;q=0.8,de;q=0.7',
      'Connection': 'keep-alive',
      'Content-Type': 'application/x-www-form-urlencoded',
      'DNT': '1',
      'Origin': 'https://uni003eu5.fusionsolar.huawei.com',
      'Referer': (
          'https://uni003eu5.fusionsolar.huawei.com/uniportal/pvmswebsite/assets/build/cloud.html?app-id=smartpvms&instance-id=smartpvms&zone-id=region-3-a9ef73df-f438-448e-9c4e-f6439f1d52fa'
      ),
      'Sec-Fetch-Dest': 'empty',
      'Sec-Fetch-Mode': 'cors',
      'Sec-Fetch-Site': 'same-origin',
      'User-Agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,'
          ' like Gecko) Chrome/150.0.0.0 Safari/537.36'
      ),
      'X-Requested-With': 'XMLHttpRequest',
      'roarand': 'c-umbt3tbt8abudf469ek9hhg7bw9juqph7xg806kb8bnvuqtc',
      'sec-ch-ua': (
          '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"'
      ),
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'x-non-renewal-session': 'true',
      'x-timezone-offset': '180',
      'Cookie': (
          'JSESSIONID=2067FF3BEF6F4A56EE37EBFE00F00FF3;'
          ' _abck=82C3C6C60F1F1F52658ACD85E9B48609~-1~YAAQFi0UAtq2yG6aAQAApMX3fA5m4N0fpnwPdPZ8gTwth5RNKhPuPZFTR/IJ2z06RIxx81l9X3COwALNVLVeTli4j1u3x7ahO80oDi75g1ojJ/vgXzUOa1ZlKdUnpE/gFb+1rbuitSn3IBG8IqZ2indUe22Lmwksc/l5wHt058dRT3/In4G2bkMAaoMhImNAY5B3+pBEZjeK7zY6XudzNeguwi7/9aNY2Y8edpjStgZI/CZMPVhPELvr26J7ae+lQY1vrLd82O6nNnxY3JL0FFQL3JeoMCukd/6v+Q2D9sNaOmTZX3PwWazK+SASRd4ANUKa4DpclLZUYlrMRhOchNI9j99JLCLOzTKFhHE8IOcUkKpvUqetUVX4KvknZdnzcPnbr5u8FZsKhoSmbl7fUfYFK2O3mzElS+IbbbOBLlMiPLEO2Z1OH8ZVWjGDvmJYWRRGBZNtTRc=~-1~-1~-1~-1~-1;'
          ' __hau=SUPPORTE.1769679841.1365012467; locale=bg-bg;'
          ' selfSettingLanguage=true;'
          ' SSO_TGC_=TGTX--F1018898895-1244822-Ohd3Jf9tbeUVhHco2S0Awlge5v1VlbZTmNi;'
          ' x-gray-tag=common;'
          ' dp-session=x-sbvz847s7sru3xnxrxrv86mldfk57yentdhgg93xnxfsbs88nvnupf2n87rus75c9dvv1ebzuobzvxjtth5gunao6roa3y5chi9gga6lc9vxlc3wqllfrtannu6n0885;'
          ' HWWAFSESTIME=1784540277913; HWWAFSESID=2ecdc583fc03a57710a;'
          ' pageversion=0; JSESSIONID=994F6CE07407C4C1A87FDD3325E7BB90'
      ),
  }

  try:
    response = requests.post(url, headers=headers, data=payload, timeout=10)
    return response.status_code == 200, response.text
  except Exception as e:
    return False, str(e)
      
def check_and_execute_schedule():
  """Проверява дали текущото BG време е преминало заложения час"""
  if not schedule_config['enabled']:
    return 'Графикът е изключен'

  now_bg = datetime.now(bg_tz)
  current_time_str = now_bg.strftime('%H:%M')

  # Превръщаме текущото време и заложените часове в минути за лесно сравнение
  now_minutes = now_bg.hour * 60 + now_bg.minute

  # По подразбиране задаваме 0 kW / 30 kW часовете
  h0, m0 = map(int, schedule_config['time_0kw'].split(':'))
  target_0kw_minutes = h0 * 60 + m0

  h30, m30 = map(int, schedule_config['time_30kw'].split(':'))
  target_30kw_minutes = h30 * 60 + m30

  result_msg = f'Проверка в {current_time_str}: Изчаква се зададен час'

  # 1. Проверка за 0 kW: ако текущите минути са >= заложените и ДНЕС още НЕ е изпълнено
  if (
      now_minutes >= target_0kw_minutes
      and now_minutes < target_30kw_minutes
      and not schedule_config['executed_today_0kw']
  ):
    success, res = send_fusionsolar_power_limit_kw(0)
    schedule_config['executed_today_0kw'] = True
    status = 'Успешно (0 kW)' if success else f'Грешка: {res}'
    schedule_config['last_action'] = (
        f'Автоматично в {current_time_str}: {status}'
    )
    result_msg = schedule_config['last_action']
    print(f'[SCHEDULE EXECUTE] {result_msg}')

  # 2. Проверка за 30 kW: ако текущите минути са >= заложените и ДНЕС още НЕ е изпълнено
  elif (
      now_minutes >= target_30kw_minutes
      and not schedule_config['executed_today_30kw']
  ):
    success, res = send_fusionsolar_power_limit_kw(30)
    schedule_config['executed_today_30kw'] = True
    status = 'Успешно (30 kW)' if success else f'Грешка: {res}'
    schedule_config['last_action'] = (
        f'Автоматично в {current_time_str}: {status}'
    )
    result_msg = schedule_config['last_action']
    print(f'[SCHEDULE EXECUTE] {result_msg}')

  # Нулиране на флаговете нощем (след 00:00)
  if current_time_str == '00:00':
    schedule_config['executed_today_0kw'] = False
    schedule_config['executed_today_30kw'] = False

  return result_msg

@app.route('/')
def index():
  return f"""
    <!DOCTYPE html>
    <html lang="bg">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Бот Управление - ФТВ Сливен</title>
        <style>
            body {{ font-family: sans-serif; text-align: center; background: #1e293b; color: white; padding: 20px; }}
            .card {{ background: #0f172a; display: inline-block; padding: 25px; border-radius: 12px; max-width: 400px; width: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
            .btn {{ padding: 15px 30px; margin: 10px; border: none; border-radius: 8px; font-size: 20px; cursor: pointer; font-weight: bold; }}
            .b-0 {{ background: #ef4444; color: white; }}
            .b-30 {{ background: #10b981; color: white; }}
            
            /* Стилизиране на падащото меню (accordion) */
            details {{ background: #334155; border-radius: 8px; margin-top: 20px; text-align: left; overflow: hidden; }}
            summary {{ padding: 15px; font-size: 16px; font-weight: bold; cursor: pointer; background: #475569; list-style: none; display: flex; justify-content: space-between; align-items: center; }}
            summary::-webkit-details-marker {{ display: none; }}
            summary:after {{ content: '►'; font-size: 12px; }}
            details[open] summary:after {{ content: '▼'; }}
            .sched-content {{ padding: 15px; }}
            
            .input-group {{ margin: 12px 0; }}
            label {{ font-size: 14px; color: #cbd5e1; display: block; margin-bottom: 4px; }}
            input[type="time"] {{ padding: 10px; border-radius: 6px; border: 1px solid #475569; font-size: 16px; width: 93%; background: #0f172a; color: white; }}
            .save-btn {{ background: #3b82f6; color: white; padding: 12px; width: 100%; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 10px; font-weight: bold; }}
            #status {{ margin-top: 15px; font-size: 16px; font-weight: bold; color: #38bdf8; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>ФТВ Сливен</h2>
            
            <h3>Ръчно задействане</h3>
            <div>
                <button class="btn b-0" onclick="setLimit(0)">0 kW</button>
                <button class="btn b-30" onclick="setLimit(30)">30 kW</button>
            </div>

            <details>
                <summary>⏱ График на ограничението</summary>
                <div class="sched-content">
                    <div class="input-group">
                        <label>Начало (0 kW):</label>
                        <input type="time" id="time_0kw" value="{schedule_config['time_0kw']}">
                    </div>

                    <div class="input-group">
                        <label>Край (30 kW):</label>
                        <input type="time" id="time_30kw" value="{schedule_config['time_30kw']}">
                    </div>

                    <div style="margin-top: 15px;">
                        <label style="font-size: 15px; color: white; cursor: pointer;">
                            <input type="checkbox" id="sched_enable" {"checked" if schedule_config['enabled'] else ""}> 
                            Включи автоматичен график за днес
                        </label>
                    </div>

                    <button class="save-btn" onclick="saveSchedule()">Запази графика</button>
                    
                    <p style="font-size: 12px; color: #94a3b8; margin-top: 12px; margin-bottom: 0;">
                        Статус: <b>{"АКТИВЕН" if schedule_config['enabled'] else "ИЗКЛЮЧЕН"}</b><br>
                        Последно: {schedule_config['last_action']}
                    </p>
                </div>
            </details>

            <p id="status"></p>
        </div>

        <script>
        function setLimit(kw) {{
            document.getElementById('status').innerText = 'Задаване на ' + kw + ' kW...';
            fetch('/limit/sliven/' + kw)
                .then(res => res.json())
                .then(data => {{
                    document.getElementById('status').innerText = data.message || 'Готово!';
                }});
        }}

        function saveSchedule() {{
            const enabled = document.getElementById('sched_enable').checked;
            const t0 = document.getElementById('time_0kw').value;
            const t30 = document.getElementById('time_30kw').value;

            document.getElementById('status').innerText = 'Запазване...';

            fetch('/set-schedule', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ enabled: enabled, time_0kw: t0, time_30kw: t30 }})
            }})
            .then(res => res.json())
            .then(data => {{
                alert('Графикът е запазен успешно!');
                location.reload();
            }});
        }}
        </script>
    </body>
    </html>
    """


@app.route('/limit/<location>/<int:kw>')
def set_limit(location, kw):
  if kw in [0, 30]:
    success, res_text = send_fusionsolar_power_limit_kw(kw)
    if success:
      return (
          jsonify(
              {"status": "success", "message": f"Лимитът е зададен на {kw} kW"}
          ),
          200,
      )
    else:
      return jsonify({"status": "error", "message": res_text}), 500
  return jsonify({"status": "error", "message": "Невалидна стойност"}), 400


@app.route('/set-schedule', methods=['POST'])
def set_schedule():
  data = request.json
  schedule_config['enabled'] = data.get('enabled', False)
  schedule_config['time_0kw'] = data.get('time_0kw', '')
  schedule_config['time_30kw'] = data.get('time_30kw', '')

  # Нулираме флаговете при промяна на графика
  schedule_config['executed_today_0kw'] = False
  schedule_config['executed_today_30kw'] = False

  return jsonify({'status': 'success', 'message': 'Графикът е запазен'})


@app.route('/check-schedule')
def check_schedule():
  """Ендпойнт, който се вика на всеки няколко минути от UptimeRobot"""
  msg = check_and_execute_schedule()
  return jsonify({'status': 'checked', 'details': msg})


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=10000)
