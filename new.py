from flask import Flask, render_template, jsonify
import requests
import json

app = Flask(__name__)

# Функция, която изпраща директната API заявка към FusionSolar
def send_fusionsolar_power_limit(limit_value):
    url = "https://uni003eu5.fusionsolar.huawei.com/rest/neteco/config/device/v1/config/power-control"

    # Данните, които FusionSolar очаква за ФТВ Сливен
    payload = {
        'dn': 'NE=135329489',
        'changeValues': json.dumps([{"id": "21003", "value": limit_value}])
    }

    # Всички хедъри и валидни бисквитки от сесията ти
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'bg-BG,bg;q=0.9,en;q=0.8,de;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'DNT': '1',
        'Origin': 'https://uni003eu5.fusionsolar.huawei.com',
        'Referer': 'https://uni003eu5.fusionsolar.huawei.com/uniportal/pvmswebsite/assets/build/cloud.html?app-id=smartpvms&instance-id=smartpvms&zone-id=region-3-a9ef73df-f438-448e-9c4e-f6439f1d52fa',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'roarand': 'c-umbt3tbt8abudf469ek9hhg7bw9juqph7xg806kb8bnvuqtc',
        'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-non-renewal-session': 'true',
        'x-timezone-offset': '180',
        'Cookie': 'JSESSIONID=2067FF3BEF6F4A56EE37EBFE00F00FF3; _abck=82C3C6C60F1F1F52658ACD85E9B48609~-1~YAAQFi0UAtq2yG6aAQAApMX3fA5m4N0fpnwPdPZ8gTwth5RNKhPuPZFTR/IJ2z06RIxx81l9X3COwALNVLVeTli4j1u3x7ahO80oDi75g1ojJ/vgXzUOa1ZlKdUnpE/gFb+1rbuitSn3IBG8IqZ2indUe22Lmwksc/l5wHt058dRT3/In4G2bkMAaoMhImNAY5B3+pBEZjeK7zY6XudzNeguwi7/9aNY2Y8edpjStgZI/CZMPVhPELvr26J7ae+lQY1vrLd82O6nNnxY3JL0FFQL3JeoMCukd/6v+Q2D9sNaOmTZX3PwWazK+SASRd4ANUKa4DpclLZUYlrMRhOchNI9j99JLCLOzTKFhHE8IOcUkKpvUqetUVX4KvknZdnzcPnbr5u8FZsKhoSmbl7fUfYFK2O3mzElS+IbbbOBLlMiPLEO2Z1OH8ZVWjGDvmJYWRRGBZNtTRc=~-1~-1~-1~-1~-1; __hau=SUPPORTE.1769679841.1365012467; locale=bg-bg; selfSettingLanguage=true; SSO_TGC_=TGTX--F1018898895-1244822-Ohd3Jf9tbeUVhHco2S0Awlge5v1VlbZTmNi; x-gray-tag=common; dp-session=x-sbvz847s7sru3xnxrxrv86mldfk57yentdhgg93xnxfsbs88nvnupf2n87rus75c9dvv1ebzuobzvxjtth5gunao6roa3y5chi9gga6lc9vxlc3wqllfrtannu6n0885; HWWAFSESTIME=1784540277913; HWWAFSESID=2ecdc583fc03a57710a; pageversion=0; JSESSIONID=994F6CE07407C4C1A87FDD3325E7BB90'
    }

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        # Връща True, ако HTTP статусът е OK (200)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

# Главен път за зареждане на страницата
@app.route('/')
def index():
    return render_template('index.html')  # или както ти се казва HTML файла

# Маршрут за промяна на лимита от бутоните
@app.route('/limit/<location>/<int:percent>')
def set_limit(location, percent):
    if percent in [0, 50, 100]:
        success, res_text = send_fusionsolar_power_limit(percent)
        if success:
            return jsonify({"status": "success", "message": f"Лимитът е променен на {percent}%"}), 200
        else:
            return jsonify({"status": "error", "message": res_text}), 500
    
    return jsonify({"status": "error", "message": "Невалиден процент"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
