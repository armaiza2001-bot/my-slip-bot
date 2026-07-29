import telebot
import requests
import io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# ==========================================
# 1. ตั้งค่าพื้นฐาน (อย่าลืมแก้ข้อมูล 3 บรรทัดนี้ให้เป็นของคุณนะครับ!)
# ==========================================
BOT_TOKEN = '8848978716:AAHC_WkcpGj8mImJ-VAJumIJbEcOIy_hhsQ'
SLIPOK_API_KEY = 'SLIPOKFRKZ2O0'
BRANCH_ID = '72620' # รหัส Branch ID ของคุณ

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# ฟังก์ชันย่อย: แปลงวันที่ให้เป็นแบบไทย (เช่น 29 ก.ค. 69)
# ==========================================
def format_thai_date(date_str):
    try:
        # สมมติวันที่มาในรูปแบบ YYYYMMDD
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        day = date_obj.day
        month_names = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
        month = month_names[date_obj.month]
        year = (date_obj.year + 543) % 100 # เอาแค่ 2 หลักท้ายของปี พ.ศ.
        return f"{day} {month} {year:02d}"
    except Exception:
        return date_str # ถ้าแปลงไม่ได้ให้คืนค่าเดิม

# ==========================================
# 2. ระบบจัดการเมื่อมีคนส่งรูปเข้ามา
# ==========================================
@bot.message_handler(content_types=['photo'])
def handle_slip(message):
    try:
        # ส่งข้อความบอกว่ากำลังโหลด
        processing_msg = bot.reply_to(message, "⏳ กำลังตรวจสอบสลิป รอสักครู่นะครับ...")

        # ดึงไฟล์รูปจาก Telegram
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # เตรียมข้อมูลส่งไปให้ SlipOK
        headers = {
            'x-authorization': SLIPOK_API_KEY
        }
        files = {'files': ('slip.jpg', downloaded_file, 'image/jpeg')}
        data = {'branchId': BRANCH_ID}
        
        # ⚠️ หมายเหตุ: URL API ตรงนี้ ให้ใช้ URL เดิมจากโค้ดที่คุณเคยใช้แล้วเวิร์คนะครับ
        api_url = 'https://api.slipok.com/api/line/apikey/xxxx' # <--- แก้ URL ตรงนี้
        response = requests.post(api_url, headers=headers, files=files, data=data) 
        result = response.json()

        # ==========================================
        # 3. ถ้าสลิปถูกต้อง -> เริ่มระบบวาดรูป
        # ==========================================
        if result.get('success'): 
            slip_data = result.get('data', {})
            
            # ดึงข้อมูลจาก SlipOK มาเก็บในตัวแปร
            sender = slip_data.get('sender', {}).get('displayName', 'ไม่ระบุ')
            receiver = slip_data.get('receiver', {}).get('displayName', 'ไม่ระบุ')
            amount = str(slip_data.get('amount', '0'))
            trans_date = slip_data.get('transDate', '20260730')
            trans_time = slip_data.get('transTime', '00:00')

            # จัดรูปแบบตัวเลขและวันที่ให้สวยงาม
            amount_formatted = "{:,.2f}".format(float(amount))
            thai_date_formatted = format_thai_date(trans_date)

            # โหลดรูปภาพพื้นหลัง (ต้องมีไฟล์นี้ใน GitHub)
            template = Image.open('template.png')
            draw = ImageDraw.Draw(template)

            # โหลดไฟล์ฟอนต์ (ต้องมีไฟล์นี้ใน GitHub)
            font = ImageFont.truetype('NotoSansThaiLooped-Medium.ttf', 40)
            font_bold = ImageFont.truetype('NotoSansThaiLooped-Medium.ttf', 55)
            font_small = ImageFont.truetype('NotoSansThaiLooped-Medium.ttf', 25)

            # -----------------------------------------------------------
            # ⚠️ พิกัด (X, Y) ด้านล่างนี้คือจุดที่บอทจะวางตัวหนังสือ 
            # คุณต้องลองแก้ตัวเลข 200, 300, 600, 150 ฯลฯ เพื่อขยับข้อความให้ตรงช่องในรูปของคุณ
            # -----------------------------------------------------------
            # วาด ยอดเงิน
            draw.text((200, 300), f"฿{amount_formatted}", font=font_bold, fill="#1B264F") 
            # วาด วันที่และเวลา
            draw.text((600, 150), f"{thai_date_formatted}, {trans_time} น.", font=font_small, fill="#888888") 
            # วาด ชื่อผู้โอน
            draw.text((600, 450), f"ผู้โอน: {sender}", font=font, fill="#555555") 
            # วาด ชื่อผู้รับ
            draw.text((600, 650), f"ผู้รับ: {receiver}", font=font, fill="#555555") 

            # ==========================================
            # 4. แปลงรูปที่วาดเสร็จแล้ว แล้วส่งกลับเข้ากลุ่ม
            # ==========================================
            img_byte_arr = io.BytesIO()
            template.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # ลบข้อความ "กำลังตรวจสอบ..." ทิ้ง เพื่อความสะอาด
            bot.delete_message(message.chat.id, processing_msg.message_id)
            # ส่งภาพใบเสร็จน่ารักๆ กลับไป
            bot.send_photo(message.chat.id, photo=img_byte_arr, reply_to_message_id=message.message_id)
        
        else:
            # กรณีสลิปปลอม หรือเช็คไม่ผ่าน
            bot.delete_message(message.chat.id, processing_msg.message_id)
            bot.reply_to(message, "❌ สลิปไม่ถูกต้อง หรือสแกนไม่พบข้อมูลครับ")

    except Exception as e:
        bot.reply_to(message, f"❌ ระบบเกิดข้อผิดพลาด: {e}")

print("🤖 บอท SlipOK ระบบวาดรูป พร้อมทำงานแล้วครับ!")
bot.polling()
