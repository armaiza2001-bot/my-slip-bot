import telebot
import requests
import os
import threading
import io
from flask import Flask
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN = os.environ.get('BOT_TOKEN')
SLIPOK_BRANCH_ID = os.environ.get('SLIPOK_BRANCH_ID')
SLIPOK_API_KEY = os.environ.get('SLIPOK_API_KEY')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 สวัสดีครับ! ดึงผมเข้ากลุ่มแล้วส่งรูปสลิปโอนเงินมาได้เลย เดี๋ยวผมช่วยตรวจสอบให้")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        url = f"https://api.slipok.com/api/line/apikey/{SLIPOK_BRANCH_ID}"
        headers = {'x-authorization': SLIPOK_API_KEY}
        files = {'files': ('slip.jpg', downloaded_file, 'image/jpeg')}
        data_payload = {'log': 'true'}

        response = requests.post(url, headers=headers, files=files, data=data_payload)
        result = response.json()

        if response.status_code == 200 and result.get('success'):
            data = result.get('data', {})
            sender = data.get('sender', {}).get('displayName', 'ไม่ระบุชื่อ')
            receiver = data.get('receiver', {}).get('displayName', 'ไม่ระบุชื่อ')
            amount = data.get('amount', '0.00')
            trans_date = data.get('transDate', '')
            trans_time = data.get('transTime', '')

            # -----------------------------------------
            # ระบบวาดรูปลง Template
            # -----------------------------------------
            try:
                # 1. เปิดรูปภาพ Template
                template = Image.open('template.png')
                draw = ImageDraw.Draw(template)

                # 2. โหลดฟอนต์ (ตัวเลข 40 และ 60 คือขนาดฟอนต์ ปรับได้ตามชอบ)
                font = ImageFont.truetype('NotoSansThaiLooped-Medium.ttf', 40)
                font_amount = ImageFont.truetype('NotoSansThaiLooped-Medium.ttf', 70) 

                # 3. วาดข้อความ (ตัวเลข 100, 200 คือพิกัด แกนแนวนอน, แกนแนวตั้ง)
                draw.text((100, 150), f"฿{amount}", font=font_amount, fill="#1B264F")
                draw.text((100, 300), f"ผู้โอน: {sender}", font=font, fill="#555555")
                draw.text((100, 400), f"ผู้รับ: {receiver}", font=font, fill="#555555")
                draw.text((100, 500), f"{trans_date} เวลา {trans_time}", font=font, fill="#888888")

                # 4. เตรียมไฟล์รูปเพื่อส่ง
                img_byte_arr = io.BytesIO()
                template.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                # 5. ส่งรูปกลับไปในกลุ่ม
                bot.send_photo(message.chat.id, photo=img_byte_arr, reply_to_message_id=message.message_id)

            except Exception as img_e:
                bot.reply_to(message, f"❌ เจอข้อผิดพลาดตอนวาดรูป: {img_e}")

        else:
            err_msg = result.get('message', 'สแกน QR Code ไม่ผ่าน หรือรูปไม่ชัดเจน')
            bot.reply_to(message, f"❌ **ตรวจสลิปไม่ผ่าน!**\nเหตุผล: {err_msg}", parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"⚠️ **ไม่สามารถตรวจสอบรูปนี้ได้**\nระบบมองไม่เห็น QR Code, สลิปโดนตัดขอบ, หรือเซิร์ฟเวอร์ขัดข้อง กรุณาส่งสลิปใหม่อีกครั้งครับ", parse_mode='Markdown')

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    bot.infinity_polling()
