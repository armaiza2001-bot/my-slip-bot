import telebot
import requests
import os
import threading
from flask import Flask

# ดึงค่าจาก Environment Variables ของ Render
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

# ==========================================
# 🔍 ฟังก์ชันดึงโควต้าจริงจากระบบ SlipOK
# ==========================================
def get_slipok_quota():
    url = f"https://api.slipok.com/api/line/apikey/{SLIPOK_BRANCH_ID}"
    headers = {'x-authorization': SLIPOK_API_KEY}
    try:
        # ใช้ requests.get เพื่อดึงข้อมูลโปรเจกต์ (ไม่โดนหักโควต้าสแกน)
        response = requests.get(url, headers=headers)
        result = response.json()
        if response.status_code == 200 and result.get('success'):
            # ดึงตัวเลข quota ออกมา
            return result.get('data', {}).get('quota', 0)
    except Exception as e:
        print("Error checking quota:", e)
    return None

# ==========================================
# 💬 คำสั่งเช็คโควต้า (พิมพ์ใน Telegram)
# ==========================================
@bot.message_handler(commands=['quota'])
def check_quota_command(message):
    quota = get_slipok_quota()
    if quota is not None:
        bot.reply_to(message, f"📊 โควต้าในเว็บ SlipOK ของคุณเหลือ: **{quota}** ครั้ง", parse_mode='Markdown')
    else:
        bot.reply_to(message, "⚠️ ไม่สามารถเชื่อมต่อกับระบบ SlipOK เพื่อเช็คโควต้าได้ในขณะนี้ครับ")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 ส่งรูปสลิปเข้ามาได้เลยครับ เดี๋ยวผมช่วยเช็คให้!")

# ==========================================
# 🖼️ ระบบตรวจสลิป
# ==========================================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    
    # 1. ให้บอทเช็คโควต้า SlipOK ก่อนทำอย่างอื่น
    current_quota = get_slipok_quota()
    
    # ถ้าดึงข้อมูลสำเร็จ และพบว่าโควต้าเหลือ 1 หรือน้อยกว่า ให้หยุดทำงาน
    if current_quota is not None and current_quota <= 1:
        bot.reply_to(message, "❌ **โควต้าตรวจสลิปใน SlipOK เหลือ 1 หรือหมดแล้ว!**\nบอทจะหยุดตรวจชั่วคราว กรุณาไปต่ออายุหรือเพิ่มโควต้าในเว็บ SlipOK ก่อนนะครับ", parse_mode='Markdown')
        return

    try:
        # ดึงไฟล์รูปจาก Telegram
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # ส่งไปตรวจสอบกับ API ของ SlipOK
        url = f"https://api.slipok.com/api/line/apikey/{SLIPOK_BRANCH_ID}"
        headers = {'x-authorization': SLIPOK_API_KEY}
        files = {'files': ('slip.jpg', downloaded_file, 'image/jpeg')}
        data_payload = {'log': 'true'}

        response = requests.post(url, headers=headers, files=files, data=data_payload)
        result = response.json()

        # ถ้าสลิปถูกต้อง
        if response.status_code == 200 and result.get('success'):
            data = result.get('data', {})
            sender = data.get('sender', {}).get('displayName', 'ไม่ระบุชื่อ')
            receiver = data.get('receiver', {}).get('displayName', 'ไม่ระบุชื่อ')
            amount = data.get('amount', '0.00')
            trans_date = data.get('transDate', '')
            trans_time = data.get('transTime', '')

            # จัดรูปแบบข้อความตอบกลับ
            text_reply = (
                "✅ **สลิปถูกต้อง**\n\n"
                f"👤 ผู้โอน: {sender}\n"
                f"🏦 ผู้รับ: {receiver}\n"
                f"💰 ยอดเงิน: {amount} บาท\n"
                f"📅 เวลาโอน: {trans_date} {trans_time}"
            )
            bot.reply_to(message, text_reply, parse_mode='Markdown')

        else:
            # สลิปปลอม หรือเช็คไม่ผ่าน
            err_msg = result.get('message', 'สแกน QR Code ไม่ผ่าน หรือรูปไม่ชัดเจน')
            bot.reply_to(message, f"❌ **ตรวจสลิปไม่ผ่าน!**\nเหตุผล: {err_msg}", parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"⚠️ **ไม่สามารถตรวจสอบรูปนี้ได้**\nกรุณาส่งสลิปใหม่อีกครั้งครับ", parse_mode='Markdown')

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    bot.infinity_polling()
