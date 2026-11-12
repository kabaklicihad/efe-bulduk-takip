import os
import json
import requests
from curl_cffi import requests as cffi_requests

API_URL = "https://winningcircle.io"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
DURUM_DOSYASI = "durum.json"

def telegram_mesaj_gonder(mesaj):
    url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mesaj, "parse_mode": "HTML"}
    requests.post(url, json=payload, timeout=10)

def pozisyon_anahtari(pos):
    return f"{pos['account']}_{pos['instId']}_{pos['side']}"

def kontrol_et():
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://winningcircle.io",
        "Origin": "https://winningcircle.io"
    }

    try:
        # Gerçek bir Chrome tarayıcısı gibi istek atar (Cloudflare engelini aşar)
        response = cffi_requests.get(
            API_URL,
            headers=headers,
            impersonate="chrome120",
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"API HTTP Hatası: {response.status_code} - Yanıt: {response.text[:200]}")
            return
            
        data = response.json()
    except Exception as e:
        print(f"Veri çekme veya JSON hatası: {e}")
        return

    if not data.get("ok"):
        print("API 'ok: false' döndürdü.")
        return

    mevcut_pozisyonlar = {pozisyon_anahtari(p): p for p in data.get("positions", [])}
    mevcut_gecmis = data.get("history", [])

    if os.path.exists(DURUM_DOSYASI):
        with open(DURUM_DOSYASI, "r", encoding="utf-8") as f:
            eski_durum = json.load(f)
        bilinen_pozisyonlar = eski_durum.get("positions", {})
        bilinen_gecmis_idler = set(eski_durum.get("history_ids", []))
        ilk_calisma = False
    else:
        bilinen_pozisyonlar = {}
        bilinen_gecmis_idler = set()
        ilk_calisma = True

    if ilk_calisma:
        telegram_mesaj_gonder("🤖 <b>GitHub Actions Takip Sistemi Başlatıldı!</b>")
    else:
        # 1. Yeni açılan veya miktarı değişen pozisyonlar
        for anahtar, pos in mevcut_pozisyonlar.items():
            yon = "🟢 LONG" if pos["side"].lower() == "long" else "🔴 SHORT"
            hesap = "Manuel" if pos["account"] == "manual" else "Bot"

            if anahtar not in bilinen_pozisyonlar:
                mesaj = (
                    f"🚨 <b>YENİ İŞLEM AÇILDI ({hesap})</b>\n\n"
                    f"<b>Parite:</b> {pos['instId']}\n"
                    f"<b>Yön:</b> {yon} ({pos['lever']}x)\n"
                    f"<b>Giriş:</b> {pos['avgPx']}\n"
                    f"<b>Büyüklük:</b> ${pos['notionalUsd']:,.2f}"
                )
                telegram_mesaj_gonder(mesaj)
            elif pos["pos"] != bilinen_pozisyonlar[anahtar]["pos"]:
                eski_pos = bilinen_pozisyonlar[anahtar]
                mesaj = (
                    f"🔄 <b>POZİSYON GÜNCELLENDİ ({hesap})</b>\n\n"
                    f"<b>Parite:</b> {pos['instId']} ({yon})\n"
                    f"<b>Eski:</b> {eski_pos['pos']} ➡️ <b>Yeni:</b> {pos['pos']}\n"
                    f"<b>Yeni Ort. Giriş:</b> {pos['avgPx']}"
                )
                telegram_mesaj_gonder(mesaj)

        # 2. Geçmişe yeni düşen (kapanan) işlemler
        for item in reversed(mevcut_gecmis):
            if item["id"] not in bilinen_gecmis_idler:
                pnl = item.get("pnl", 0)
                pnl_oran = item.get("pnlRatio", 0)
                durum_ikon = "✅ KÂR" if pnl >= 0 else "❌ ZARAR"
                hesap = "Manuel" if item["account"] == "manual" else "Bot"

                mesaj = (
                    f"📊 <b>İŞLEM KAPANDI ({hesap})</b>\n\n"
                    f"<b>Parite:</b> {item['instId']} ({item['side'].upper()} - {item['lever']}x)\n"
                    f"<b>Giriş:</b> {item['avgPx']} ➡️ <b>Çıkış:</b> {item['closePx']}\n"
                    f"<b>Sonuç:</b> {durum_ikon}: <b>${pnl:,.2f}</b> (%{pnl_oran:.2f})"
                )
                telegram_mesaj_gonder(mesaj)

    yeni_durum = {
        "positions": mevcut_pozisyonlar,
        "history_ids": [item["id"] for item in mevcut_gecmis]
    }
    with open(DURUM_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(yeni_durum, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    kontrol_et()
