import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from random import randint

app = Flask(__name__)

# 模擬存儲驗證碼
verification_codes = {}

# 配置郵件服務器
SMTP_SERVER = "smtp.gmail.com"  # 使用 Gmail 的 SMTP 服務
SMTP_PORT = 587
SMTP_EMAIL = "aiboy9527@gmail.com"  # 替換為您的郵件地址
SMTP_PASSWORD = "!Asd12345"     # 替換為您的郵件密碼

@app.route('/send-email-verification-code', methods=['POST'])
def send_email_verification_code():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'message': '電子信箱是必填的'}), 400

    # 生成六位數驗證碼
    code = str(randint(100000, 999999))
    verification_codes[email] = code

    # 構建郵件內容
    subject = "您的驗證碼"
    body = f"您的驗證碼是：{code}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_EMAIL
    msg['To'] = email

    try:
        # 發送郵件
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # 啟用 TLS 加密
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, email, msg.as_string())
        
        print(f"驗證碼已發送至：{email}")
        return jsonify({'success': True, 'message': '驗證碼已發送'})
    except Exception as e:
        print(f"發送驗證碼失敗：{e}")
        return jsonify({'success': False, 'message': '無法發送驗證碼'})

@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    email = data.get('email')
    code = data.get('code')

    if not email or not code:
        return jsonify({'success': False, 'message': '電子信箱和驗證碼是必填的'}), 400

    if verification_codes.get(email) == code:
        return jsonify({'success': True, 'message': '驗證成功'})
    else:
        return jsonify({'success': False, 'message': '驗證碼錯誤'})
