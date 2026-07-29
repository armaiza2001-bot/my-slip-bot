import telebot
import requests
import os
import threading
from flask import Flask

# ดึงค่าจาก Environment Variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
SLIPOK_BRANCH_ID = os.environ.get('SLIPOK_BRANCH_ID')
SLIPOK_API_KEY = os.environ.get('SLIPOK_API_KEY')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ==========================================
# ⚙️ ระบบโควต้าแบบกำหนดเอง (แอดมินคุม)
# ==========================================
# ⚠️ ใส่ Telegram ID ของคุณที่นี่ เพื่อให้คุณสั่งเติมโควต้าได้คนเดียว
ADMIN_ID = 1297140269 

# ตั้งค่าโควต้าเริ่มต้น
current_quota = 100 

@app.route('/')
def home():
    return "Bot is running!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 💬 คำสั่งจัดการโควต้า 
# ==========================================
@bot.message_handler(commands=['quota'])
def check_quota(message):
    bot.reply_to(message, f"📊 โควต้าตรวจสลิปปัจจุบัน: {current_quota} ครั้ง")

@bot.message_handler(commands=['addquota'])
def add_quota(message):
    global current_quota
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ครับ")
        return
    try:
        amount = int(message.text.split()[1])
        current_quota += amount
        if current_quota < 1:
            current_quota = 1 # บังคับไม่ให้ต่ำกว่า 1
        bot.reply_to(message, f"✅ เติมโควต้าให้ {amount} ครั้ง\n📊 โควต้าปัจจุบัน: {current_quota} ครั้ง")
    except:
        bot.reply_to(message, "⚠️ รูปแบบผิดครับ ต้องพิมพ์ตัวเลขด้วย เช่น: /addquota 50")

@bot.message_handler(commands=['setquota'])
def set_quota(message):
    global current_quota
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ครับ")
        return
    try:
        amount = int(message.text.split()[1])
        if amount < 1:
            amount = 1 # บังคับไม่ให้ต่ำกว่า 1
        current_quota = amount
        bot.reply_to(message, f"✅ ตั้งค่าโควต้าใหม่เป็น {current_quota} ครั้งเรียบร้อย")
    except:
        bot.reply_to(message, "⚠️ รูปแบบผิดครับ ต้องพิมพ์ตัวเลขด้วย เช่น: /setquota 100")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 ส่งรูปสลิปเข้ามาได้เลยครับ เดี๋ยวผมช่วยเช็คให้!")

# ==========================================
# 🖼️ ระบบตรวจสลิป
# ==========================================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    global current_quota

    # 1. เช็คโควต้าก่อน: ถ้าเท่ากับ 1 (หรือน้อยกว่า) บอทจะไม่ทำงาน
    if current_quota <= 1:
        bot.reply_to(message, "❌ **บอทหยุดทำงาน!**\nโควต้าการสแกนอยู่ที่ 1 กรุณาให้แอดมินเพิ่มโควต้าเพื่อใช้งานต่อครับ", parse_mode='Markdown')
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

            # 2. หักโควต้าเมื่อสแกนสำเร็จ
            current_quota -= 1
            if current_quota < 1:
                current_quota = 1 # กันเหนียวไม่ให้ต่ำกว่า 1

            # จัดรูปแบบข้อความตอบกลับ
            text_reply = (
                "✅ **สลิปถูกต้อง**\n\n"
                f"👤 ผู้โอน: {sender}\n"
                f"🏦 ผู้รับ: {receiver}\n"
                f"💰 ยอดเงิน: {amount} บาท\n"
                f"📅 เวลาโอน: {trans_date} {trans_time}\n"
                f"*(เหลือโควต้าใช้งานได้อีก {current_quota - 1} รูป)*"
            )
            bot.reply_to(message, text_reply, parse_mode='Markdown')

        else:
            # สลิปปลอม หรือเช็คไม่ผ่าน (ไม่หักโควต้า)
            err_msg = result.get('message', 'สแกน QR Code ไม่ผ่าน หรือรูปไม่ชัดเจน')
            bot.reply_to(message, f"❌ **ตรวจสลิปไม่ผ่าน!**\nเหตุผล: {err_msg}", parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"⚠️ **ไม่สามารถตรวจสอบรูปนี้ได้**\nกรุณาส่งสลิปใหม่อีกครั้งครับ", parse_mode='Markdown')

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    bot.infinity_polling()
