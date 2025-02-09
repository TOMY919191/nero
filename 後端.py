from flask import Flask, request, jsonify, render_template, send_from_directory, redirect
import os
import json
import hashlib
import pandas as pd
import base64

def image_to_base64(image):
    """將圖片轉換為 Base64"""
    return f"data:image/{image.filename.split('.')[-1]};base64,{base64.b64encode(image.read()).decode('utf-8')}"

def file_to_base64(file_path):
    """將文件轉換為 Base64"""
    if os.path.exists(file_path):
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            ext = os.path.splitext(file_path)[-1].replace('.', '')
            return f"data:image/{ext};base64,{encoded_string}"
    return None

app = Flask(__name__)

BASE_DIR = './user_settings'
DATABASE_FILE = './users_database.xlsx'
os.makedirs(BASE_DIR, exist_ok=True)

def generate_settings_id(account):
    """根據帳號生成加密 settings_id"""
    return hashlib.md5(account.encode()).hexdigest()

@app.route('/uploads/<settings_id>/<filename>')
def serve_file(settings_id, filename):
    """提供靜態文件如圖片"""
    folder = os.path.join(BASE_DIR, settings_id)
    return send_from_directory(folder, filename)

@app.route('/')
def login_page():
    """登入頁面"""
    return render_template('login.html')

@app.route('/settings')
def settings_page():
    """設定頁面"""
    settings_id = request.args.get('settings_id')
    if not settings_id:
        return redirect('/')

    settings_folder = os.path.join(BASE_DIR, settings_id)
    settings_file = os.path.join(settings_folder, 'settings.json')

    # 預設設定內容
    settings_data = {
        'name': '',
        'title': '',
        'description': '',
        'nameColor': '#000000',
        'titleColor': '#000000',
        'descriptionColor': '#000000',
        'background': '',
        'customColor': '#ffffff',
        'email': '',
        'phone': '',
        'facebook': '',
        'instagram': '',
        'avatarBase64': '',
        'backgroundImageBase64': '',
    }

    # 如果設定檔案存在，讀取內容
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings_data.update(json.load(f))

    # 確保 Base64 編碼圖片存在於設定檔
    avatar_path = os.path.join(settings_folder, 'avatar.png')
    if os.path.exists(avatar_path) and not settings_data.get('avatarBase64'):
        settings_data['avatarBase64'] = file_to_base64(avatar_path)

    background_path = os.path.join(settings_folder, 'background.png')
    if os.path.exists(background_path) and not settings_data.get('backgroundImageBase64'):
        settings_data['backgroundImageBase64'] = file_to_base64(background_path)

    # 將設定傳遞到前端
    return render_template('settings.html', settings=settings_data, settings_id=settings_id)

@app.route('/login', methods=['POST'])
def login():
    """用戶登入"""
    account = str(request.form.get('account', '')).strip()
    password = str(request.form.get('password', '')).strip()

    # 確保資料庫存在
    if not os.path.exists(DATABASE_FILE):
        return jsonify({'message': '資料庫不存在，請先註冊用戶'}), 401

    # 讀取資料庫並強制轉換類型
    df = pd.read_excel(DATABASE_FILE)
    df['帳號'] = df['帳號'].astype(str)
    df['密碼'] = df['密碼'].astype(str)

    # 驗證帳號和密碼
    user = df[(df['帳號'] == account) & (df['密碼'] == password)]
    if not user.empty:
        settings_id = user.iloc[0]['設定ID']
        return jsonify({'message': '登入成功', 'settings_id': settings_id})
    else:
        return jsonify({'message': '帳號或密碼錯誤'}), 401

@app.route('/save-settings', methods=['POST'])
def save_settings():
    """儲存設定並更新 Excel 資料庫"""
    settings_id = request.form.get('settings_id')

    # 確保資料夾存在
    settings_folder = os.path.join(BASE_DIR, settings_id)
    os.makedirs(settings_folder, exist_ok=True)

    # 儲存表單數據
    data = {
        'settings_id': settings_id,
        'name': request.form.get('name'),
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'nameColor': request.form.get('nameColor'),
        'titleColor': request.form.get('titleColor'),
        'descriptionColor': request.form.get('descriptionColor'),
        'background': request.form.get('background'),
        'customColor': request.form.get('custom_color'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'facebook': request.form.get('facebook'),
        'instagram': request.form.get('instagram'),
    }

    # 儲存大頭貼（若有上傳則覆蓋）
    avatar_file = request.files.get('avatar')
    if avatar_file:
        avatar_path = os.path.join(settings_folder, 'avatar.png')
        avatar_file.save(avatar_path)  # ⬅️ 覆蓋舊的 avatar.png
        with open(avatar_path, "rb") as img:
            data['avatarBase64'] = f"data:image/png;base64,{base64.b64encode(img.read()).decode()}"

    # 儲存背景圖片（若有上傳則覆蓋）
    background_file = request.files.get('backgroundImage')
    if background_file:
        background_path = os.path.join(settings_folder, 'background.png')
        background_file.save(background_path)  # ⬅️ 覆蓋舊的 background.png
        with open(background_path, "rb") as img:
            data['backgroundImageBase64'] = f"data:image/png;base64,{base64.b64encode(img.read()).decode()}"

    # 儲存 JSON 設定（每次覆蓋）
    settings_file = os.path.join(settings_folder, 'settings.json')
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)  # ⬅️ 覆蓋舊的 settings.json

    # 更新 Excel
    update_excel_database(data)

    # 重新生成電子名片（每次都會覆蓋）
    generate_business_card(settings_folder, data)  # ⬅️ 生成 business_card.html（覆蓋舊的）

    return redirect(f'/get-business-card/{settings_id}')


    @app.route('/get-business-card/<settings_id>', methods=['GET'])
    def get_business_card(settings_id):
        """返回電子名片 HTML"""
        card_path = os.path.join(BASE_DIR, settings_id, 'business_card.html')
        if not os.path.exists(card_path):
            return jsonify({'message': '未找到電子名片'}), 404
        return send_from_directory(os.path.dirname(card_path), 'business_card.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """處理用戶註冊"""
    if request.method == 'GET':
        # 渲染註冊頁面
        return render_template('register.html')

    # POST 方法處理註冊邏輯
    account = str(request.form.get('account', '')).strip()
    password = str(request.form.get('password', '')).strip()

    if not account or not password:
        return jsonify({'message': '帳號或密碼不可為空'}), 400

    # 確保資料庫存在，並初始化標題列
    fields = [
        '帳號', '密碼', '設定ID', '姓名', '職稱', '簡介', '字體顏色_姓名', 
        '字體顏色_職稱', '字體顏色_簡介', '背景顏色', 'Email', '電話',
        'Facebook', 'Instagram', 'YouTube', 'TikTok', 'WhatsApp',
        'Messenger', 'LINE', 'Telegram', 'PayPal', 'Weibo', 'Twitter',
        'Snapchat', 'LinkedIn', 'Reddit', 'Tumblr', 'Pinterest', 
        'Twitch', 'Vimeo', 'Patreon', 'Amazon'
    ]

    if not os.path.exists(DATABASE_FILE):
        df = pd.DataFrame(columns=fields)
    else:
        df = pd.read_excel(DATABASE_FILE)

    # 檢查帳號是否已存在
    if account in df['帳號'].astype(str).values:
        return jsonify({'message': '帳號已存在，請使用其他帳號'}), 400

    # 生成設定 ID 並添加新用戶資料
    settings_id = generate_settings_id(account)
    new_user = {field: '' for field in fields}
    new_user.update({
        '帳號': account,
        '密碼': password,
        '設定ID': settings_id,
    })
    df = pd.concat([df, pd.DataFrame([new_user])], ignore_index=True)
    df.to_excel(DATABASE_FILE, index=False)

    return jsonify({'message': '註冊成功', 'settings_id': settings_id})

def generate_business_card(folder, data):
    """生成電子名片 HTML 文件，並處理圖片轉換為 Base64"""
    
    # 將圖片轉換為 Base64 格式
    def convert_image_to_base64(image_path):
        if os.path.exists(image_path):
            with open(image_path, "rb") as img:
                encoded_string = base64.b64encode(img.read()).decode()
                ext = os.path.splitext(image_path)[-1].replace('.', '')
                return f"data:image/{ext};base64,{encoded_string}"
        return None

    # 獲取大頭貼和背景圖片的 Base64
    avatar_base64 = data.get('avatarBase64') or convert_image_to_base64(os.path.join(folder, 'avatar.png'))
    background_base64 = data.get('backgroundImageBase64') or convert_image_to_base64(os.path.join(folder, 'background.png'))
    
    # 設定背景樣式
    background_style = f'background-image: url({background_base64});' if background_base64 else f'background-color: {data.get("customColor", "#ffffff")};'

    # 支持的社交媒體字段與對應的圖示
    social_icons = {
        "Facebook": "https://upload.wikimedia.org/wikipedia/commons/4/44/Facebook_Logo.png",
        "Instagram": "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png",
        "X": "https://s3-symbol-logo.tradingview.com/twitter--600.png",
        "YouTube": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/YouTube_social_white_circle_%282017%29.svg/640px-YouTube_social_white_circle_%282017%29.svg.png",
        "LINE": "https://upload.wikimedia.org/wikipedia/commons/4/41/LINE_logo.svg",
        "LINE Official Account": "https://vos.line-scdn.net/loamkt-static/images/uploads/site_settings/d2be10c727a8be900660b078739b50a5.png"
    }

    # 動態生成社交連結 HTML
    social_links = ""
    for field, icon in social_icons.items():
        value = data.get(field.lower())
        if value:  # 如果字段有值，生成按鈕
            social_links += f"""
            <div class="social-link">
                <a href="{value}" target="_blank">
                    <img src="{icon}" alt="{field}" title="{field}" />
                </a>
            </div>
            """

    # 生成 HTML
    card_html = f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{data.get('name', '電子名片')}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                {background_style}
                color: black;
                margin: 0;
                padding: 20px;
            }}
            .card-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-start;
                min-height: 100vh;
            }}
            .avatar {{
                display: block;
                margin: 20px auto;
                width: 150px;
                height: 150px;
                border-radius: 50%;
                background-image: url({avatar_base64});
                background-size: cover;
                background-position: center;
            }}
            .name {{ font-size: 24px; font-weight: bold; margin-top: 10px; }}
            .title {{ font-size: 18px; margin-top: 5px; }}
            .description {{ font-size: 16px; margin: 15px 0; }}
            .social-links {{
                margin-top: 20px;
                width: 80%;
                display: flex;
                justify-content: center;
                gap: 10px;
            }}
            .social-link img {{
                width: 50px;
                height: 50px;
                border-radius: 50%;
                box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
            }}
        </style>
    </head>
    <body>
        <div class="card-container">
            <div class="avatar"></div>
            <div class="name">{data.get('name', '姓名')}</div>
            <div class="title">{data.get('title', '職稱')}</div>
            <div class="description">{data.get('description', '簡介內容')}</div>
            <div class="social-links">{social_links}</div>
        </div>
    </body>
    </html>
    """

    # 儲存 HTML 檔案
    with open(os.path.join(folder, 'business_card.html'), 'w', encoding='utf-8') as f:
        f.write(card_html)

def update_excel_database(data):
    """更新用戶資料至 Excel 資料庫"""
    # 獲取相關欄位
    update_fields = [
        '姓名', '職稱', '簡介', '字體顏色_姓名', 
        '字體顏色_職稱', '字體顏色_簡介', '背景顏色',
        'Email', '電話', 'Facebook', 'Instagram', 'YouTube', 
        'TikTok', 'WhatsApp', 'Messenger', 'LINE', 'Telegram',
        'PayPal', 'Weibo', 'Twitter', 'Snapchat', 'LinkedIn', 
        'Reddit', 'Tumblr', 'Pinterest', 'Twitch', 'Vimeo', 
        'Patreon', 'Amazon'
    ]

    # 確保資料庫存在
    if not os.path.exists(DATABASE_FILE):
        return jsonify({'message': '資料庫不存在，請先註冊用戶'}), 400

    # 讀取 Excel 資料
    df = pd.read_excel(DATABASE_FILE)

    # 如果設定 ID 存在，更新資料
    if data['settings_id'] in df['設定ID'].values:
        for field in update_fields:
            if field in data:
                df.loc[df['設定ID'] == data['settings_id'], field] = data[field]
    else:
        return jsonify({'message': '找不到對應的設定 ID'}), 404

    # 儲存更新後的 Excel 資料庫
    df.to_excel(DATABASE_FILE, index=False)

if __name__ == '__main__':
    app.run(debug=True)
