from datetime import datetime
import json
import os
from flask import Flask, jsonify, request
import pytz
import requests

app = Flask(__name__)

bg_tz = pytz.timezone('Europe/Sofia')

# Потребител и парола
WEB_USER = 'Stako123'
WEB_PASS = 'PV123456'

PLANTS = {
    'sliven': {
        'name': 'ФТВ Сливен',
        'dn': 'NE=135329489',
        'max_kw': 30,
        'schedule': {
            'enabled': False,
            'time_off': '14:00',
            'time_on': '14:30',
            'last_action': 'Няма активен график',
            'executed_today_off': False,
            'executed_today_on': False,
        },
    },
    'petro': {
        'name': 'ФТВ Петро',
        'dn': 'NE=135282380',
        'max_kw': 90,
        'schedule': {
            'enabled': False,
            'time_off': '14:00',
            'time_on': '14:30',
            'last_action': 'Няма активен график',
            'executed_today_off': False,
            'executed_today_on': False,
        },
    },
}


def get_web_session():
  """Създава оторизирана сесия с акаунта Stako123"""
  session = requests.Session()
  host = 'https://uni003eu5.fusionsolar.huawei.com'

  session.headers.update({
      'User-Agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
          ' (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      ),
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'bg,en;q=0.9',
      'Origin': host,
      'Referer': f'{host}/pvmswebsite/assets/build/cloud.html',
  })

  try:
    # 1. Начална страница за инициализиране на бисквитките
    session.get(f'{host}/pvmswebsite/assets/build/cloud.html', timeout=10)

    # 2. Вход през уеб формата
    login_url = f'{host}/uniload/login'
    payload = {
        'username': WEB_USER,
        'password': WEB_PASS,
        'organizationName': '',
    }

    print(
        f'[WEB LOGIN] Опит за вход като {WEB_USER} към {login_url}...',
        flush=True,
    )
    res = session.post(login_url, json=payload, timeout=10)
    print(
        f'[WEB LOGIN RESPONSE] Status: {res.status_code} | Res:'
        f' {res.text[:150]}',
        flush=True,
    )

    if res.status_code == 200 and 'html' not in res.text.lower():
      return session
    else:
      print('[WEB LOGIN FAIL] Неуспешен вход през уеб формата.', flush=True)

  except Exception as e:
    print(f'[WEB LOGIN ERROR] {str(e)}', flush=True)

  return None


def send_fusionsolar_power_limit_kw(dn_value, kw_value):
  session = get_web_session()

  if not session:
    return False, 'Грешка при автентификация на Stako123.'

  host = 'https://uni003eu5.fusionsolar.huawei.com'
  control_url = (
      f'{host}/rest/neteco/config/device/v1/config/power-control'
  )

  # Вземане на XSRF токена от бисквитките
  xsrf_token = session.cookies.get('XSRF-TOKEN') or ''

  headers = {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      'X-Requested-With': 'XMLHttpRequest',
      'X-XSRF-TOKEN': xsrf_token,
  }

  payload = {
      'dn': dn_value,
      'changeValues': json.dumps([{'id': '21003', 'value': str(kw_value)}]),
  }

  try:
    print(
        f'[DEV CONTROL] Задаване на {kw_value} kW за {dn_value}...', flush=True
    )
    res = session.post(control_url, data=payload, headers=headers, timeout=10)
    print(
        f'[DEV CONTROL RESPONSE] Status: {res.status_code} | Res:'
        f' {res.text[:150]}',
        flush=True,
    )

    if res.status_code == 200 and 'html' not in res.text.lower():
      return True, f'Зададен лимит {kw_value} kW'
    else:
      return False, f'Сървърът отхвърли командата (Status: {res.status_code})'

  except Exception as e:
    return False, f'Изключение: {str(e)}'


def check_and_execute_schedules():
  now_bg = datetime.now(bg_tz)
  current_time_str = now_bg.strftime('%H:%M')
  now_minutes = now_bg.hour * 60 + now_bg.minute
  messages = []

  for plant_id, plant in PLANTS.items():
    sched = plant['schedule']
    if not sched['enabled']:
      continue

    h0, m0 = map(int, sched['time_off'].split(':'))
    target_off = h0 * 60 + m0

    h_max, m_max = map(int, sched['time_on'].split(':'))
    target_on = h_max * 60 + m_max

    if (
        now_minutes >= target_off
        and now_minutes < target_on
        and not sched['executed_today_off']
    ):
      success, res = send_fusionsolar_power_limit_kw(plant['dn'], 0)
      sched['executed_today_off'] = True
      status = 'Успешно (0 kW)' if success else f'Грешка: {res}'
      sched['last_action'] = f'Автоматично в {current_time_str}: {status}'
      messages.append(f"{plant['name']}: {status}")

    elif now_minutes >= target_on and not sched['executed_today_on']:
      max_kw = plant['max_kw']
      success, res = send_fusionsolar_power_limit_kw(plant['dn'], max_kw)
      sched['executed_today_on'] = True
      status = f'Успешно ({max_kw} kW)' if success else f'Грешка: {res}'
      sched['last_action'] = f'Автоматично в {current_time_str}: {status}'
      messages.append(f"{plant['name']}: {status}")

    if current_time_str == '00:00':
      sched['executed_today_off'] = False
      sched['executed_today_on'] = False

  return (
      '; '.join(messages)
      if messages
      else f'Проверка в {current_time_str}: Няма активни задачи'
  )


@app.route('/')
def index():
  cards_html = ''
  for plant_id, plant in PLANTS.items():
    sched = plant['schedule']
    max_kw = plant['max_kw']

    cards_html += f"""
        <div class="card">
            <h2>{plant['name']}</h2>
            <h3>Ръчно задействане</h3>
            <div>
                <button class="btn b-0" onclick="setLimit('{plant_id}', 0)">0 kW</button>
                <button class="btn b-max" onclick="setLimit('{plant_id}', {max_kw})">{max_kw} kW</button>
            </div>
            <details>
                <summary>⏱ График на ограничението</summary>
                <div class="sched-content">
                    <div class="input-group">
                        <label>Начало (0 kW):</label>
                        <input type="time" id="time_off_{plant_id}" value="{sched['time_off']}">
                    </div>
                    <div class="input-group">
                        <label>Край ({max_kw} kW):</label>
                        <input type="time" id="time_on_{plant_id}" value="{sched['time_on']}">
                    </div>
                    <div style="margin-top: 15px;">
                        <label style="font-size: 15px; color: white; cursor: pointer;">
                            <input type="checkbox" id="sched_enable_{plant_id}" {"checked" if sched['enabled'] else ""}> 
                            Включи автоматичен график
                        </label>
                    </div>
                    <button class="save-btn" onclick="saveSchedule('{plant_id}')">Запази графика</button>
                    <p style="font-size: 12px; color: #94a3b8; margin-top: 12px; margin-bottom: 0;">
                        Статус: <b>{"АКТИВЕН" if sched['enabled'] else "ИЗКЛЮЧЕН"}</b><br>
                        Последно: {sched['last_action']}
                    </p>
                </div>
            </details>
            <p id="status_{plant_id}" class="status-p"></p>
        </div>
        """

  return f"""
    <!DOCTYPE html>
    <html lang="bg">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Управление на ФТВ</title>
        <style>
            body {{ font-family: sans-serif; text-align: center; background: #1e293b; color: white; padding: 20px; }}
            .container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }}
            .card {{ background: #0f172a; padding: 25px; border-radius: 12px; max-width: 400px; width: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
            .btn {{ padding: 15px 25px; margin: 8px; border: none; border-radius: 8px; font-size: 18px; cursor: pointer; font-weight: bold; }}
            .b-0 {{ background: #ef4444; color: white; }}
            .b-max {{ background: #10b981; color: white; }}
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
            .status-p {{ margin-top: 15px; font-size: 15px; font-weight: bold; color: #38bdf8; min-height: 20px; }}
        </style>
    </head>
    <body>
        <h1>Управление на ФТВ Централи</h1>
        <div class="container">
            {cards_html}
        </div>
        <script>
        function setLimit(plantId, kw) {{
            document.getElementById('status_' + plantId).innerText = 'Задаване на ' + kw + ' kW...';
            fetch('/limit/' + plantId + '/' + kw)
                .then(res => res.json())
                .then(data => {{
                    document.getElementById('status_' + plantId).innerText = data.message || 'Готово!';
                }});
        }}
        function saveSchedule(plantId) {{
            const enabled = document.getElementById('sched_enable_' + plantId).checked;
            const tOff = document.getElementById('time_off_' + plantId).value;
            const tOn = document.getElementById('time_on_' + plantId).value;
            document.getElementById('status_' + plantId).innerText = 'Запазване...';
            fetch('/set-schedule/' + plantId, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ enabled: enabled, time_off: tOff, time_on: tOn }})
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


@app.route('/limit/<plant_id>/<int:kw>')
def set_limit(plant_id, kw):
  if plant_id in PLANTS:
    max_kw = PLANTS[plant_id]['max_kw']
    if kw in [0, max_kw]:
      dn = PLANTS[plant_id]['dn']
      success, res_text = send_fusionsolar_power_limit_kw(dn, kw)
      if success:
        return (
            jsonify({
                'status': 'success',
                'message': (
                    f'Лимитът за {PLANTS[plant_id]["name"]} е зададен на'
                    f' {kw} kW'
                ),
            }),
            200,
        )
      else:
        return jsonify({'status': 'error', 'message': res_text}), 500
  return jsonify({'status': 'error', 'message': 'Невалидни параметри'}), 400


@app.route('/set-schedule/<plant_id>', methods=['POST'])
def set_schedule(plant_id):
  if plant_id in PLANTS:
    data = request.json
    sched = PLANTS[plant_id]['schedule']
    sched['enabled'] = data.get('enabled', False)
    sched['time_off'] = data.get('time_off', '')
    sched['time_on'] = data.get('time_on', '')
    sched['executed_today_off'] = False
    sched['executed_today_on'] = False
    return jsonify({'status': 'success', 'message': 'Графикът е запазен'})
  return jsonify({'status': 'error', 'message': 'Несъществуваща централа'}), 400


@app.route('/check-schedule')
def check_schedule():
  msg = check_and_execute_schedules()
  return jsonify({'status': 'checked', 'details': msg})


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=10000)
