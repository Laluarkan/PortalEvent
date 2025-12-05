import requests
from django.conf import settings

def send_telegram_message(message):
    """
    Fungsi untuk mengirim notifikasi ke Telegram Admin
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    
    # URL API Telegram
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown", # Agar bisa pakai huruf tebal/miring
    }

    try:
        response = requests.post(url, data=payload)
        # Cek respon untuk debugging (opsional)
        print(f"Status Telegram: {response.json()}") 
        return True
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")
        return False