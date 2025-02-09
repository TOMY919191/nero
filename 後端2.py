from flask import Flask, request, jsonify, render_template, send_from_directory, redirect
import os
import json
import hashlib
import pandas as pd
import base64

app = Flask(__name__)

BASE_DIR = './user_settings'
DATABASE_FILE = './users_database.xlsx'
os.makedirs(BASE_DIR, exist_ok=True)

def generate_settings_id(account):
    """根據帳號生成加密 settings_id"""
    return hashlib.md5(account.encode()).hexdigest()

def file_to_base64(file_path):
    """將文件轉換為 Base64"""
    if os.path.exists(file_path):
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            ext = os.path.splitext(file_path)[-1].replace('.', '')
            return f"data:image/{ext};base64,{encoded_string}"
    return None

@app.route('/')
def home():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    account = request.form.get('account', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if password != confirm_password:
        return jsonify({'message': '❌ 密碼與確認密碼不一致'}), 400

    if not os.path.exists(DATABASE_FILE):
        df = pd.DataFrame(columns=['帳號', '密碼', '設定ID'])
        df.to_excel(DATABASE_FILE, index=False)

    df = pd.read_excel(DATABASE_FILE, dtype=str)  # 確保讀取時不變 NaN
    if '帳號' not in df.columns or '密碼' not in df.columns or '設定ID' not in df.columns:
        df = pd.DataFrame(columns=['帳號', '密碼', '設定ID'])

    if account in df['帳號'].astype(str).values:
        return jsonify({'message': '⚠ 帳號已存在'}), 400

    # ✅ 生成唯一的 `settings_id`
    settings_id = hashlib.md5(account.encode()).hexdigest()

    new_user = pd.DataFrame({'帳號': [account], '密碼': [password], '設定ID': [settings_id]})
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_excel(DATABASE_FILE, index=False)

    print(f"✅ 註冊成功：{account}，設定 ID：{settings_id}")
    return jsonify({'message': '✅ 註冊成功！'}), 200


def login_page():
    """登入頁面"""
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    """用戶登入"""
    account = request.form.get('account', '').strip()
    password = request.form.get('password', '').strip()

    try:
        # ✅ 確保資料庫存在
        if not os.path.exists(DATABASE_FILE):
            return jsonify({'success': False, 'message': '❌ 資料庫不存在，請先註冊用戶'}), 500

        # ✅ 讀取 Excel 資料庫
        df = pd.read_excel(DATABASE_FILE, dtype=str)

        # ✅ 檢查是否缺少必要欄位
        required_columns = {'帳號', '密碼', '設定ID'}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            return jsonify({'success': False, 'message': f'❌ 資料庫欄位缺失: {missing_columns}'}), 500

        # ✅ 確保 `帳號` 和 `密碼` 欄位是字串格式
        df['帳號'] = df['帳號'].astype(str)
        df['密碼'] = df['密碼'].astype(str)

        # ✅ 檢查帳號是否存在
        user = df[df['帳號'] == account]
        if user.empty:
            return jsonify({'success': False, 'message': '❌ 帳號或密碼錯誤'}), 401

        # ✅ 檢查密碼是否正確
        if user.iloc[0]['密碼'] != password:
            return jsonify({'success': False, 'message': '❌ 帳號或密碼錯誤'}), 401

        # ✅ 取得設定 ID
        settings_id = user.iloc[0]['設定ID']
        print(f"✅ 登入成功，跳轉到 /settings?settings_id={settings_id}")  # 除錯資訊
        return jsonify({'success': True, 'message': '✅ 登入成功', 'settings_id': settings_id})

    except Exception as e:
        print(f"❌ 系統錯誤 (Exception): {e}")  # ✅ 記錄完整錯誤資訊
        return jsonify({'success': False, 'message': f'❌ 系統錯誤: {str(e)}'}), 500


@app.route('/settings')
def settings_page():
    """設定頁面"""
    settings_id = request.args.get('settings_id')
    if not settings_id:
        return redirect('/')

    settings_folder = os.path.join(BASE_DIR, settings_id)
    settings_file = os.path.join(settings_folder, 'settings.json')

    # 預設設定
    settings_data = {
        'settings_id': settings_id,
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
        'x': '',
        'youtube': '',
        'line': '',
        'line_official': '',
        'avatarBase64': '',
        'backgroundImageBase64': ''
    }

    # **讀取 `settings.json`**
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings_data.update(json.load(f))

    # **讀取圖片**
    avatar_path = os.path.join(settings_folder, 'avatar.png')
    if os.path.exists(avatar_path):
        settings_data['avatarBase64'] = file_to_base64(avatar_path)

    background_path = os.path.join(settings_folder, 'background.png')
    if os.path.exists(background_path):
        settings_data['backgroundImageBase64'] = file_to_base64(background_path)

    return render_template('settings.html', settings=settings_data, settings_id=settings_id)


@app.route('/save-settings', methods=['POST'])
def save_settings():
    """儲存設定並更新設定檔"""
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
        'facebook': request.form.get('facebook', ''),
        'instagram': request.form.get('instagram', ''),
        'x': request.form.get('x', ''),
        'youtube': request.form.get('youtube', ''),
        'line': request.form.get('line', ''),
        'line_official': request.form.get('line_official', ''),
    }

    # ✅ 當背景選擇為 "custom_color"，清除背景圖片
    if data['background'] == 'custom_color':
        data['backgroundImageBase64'] = ""
    else:
        # ✅ 背景圖片
        background_file = request.files.get('backgroundImage')
        background_path = os.path.join(settings_folder, 'background.png')
        if background_file:
            background_file.save(background_path)
            data['backgroundImageBase64'] = file_to_base64(background_path)
        elif os.path.exists(background_path):  # 保留舊的背景圖
            data['backgroundImageBase64'] = file_to_base64(background_path)

    # ✅ 覆蓋舊的大頭貼
    avatar_file = request.files.get('avatar')
    avatar_path = os.path.join(settings_folder, 'avatar.png')
    if avatar_file:
        avatar_file.save(avatar_path)
        data['avatarBase64'] = file_to_base64(avatar_path)  # ✅ 轉換為 Base64
    elif os.path.exists(avatar_path):  # 保留舊的大頭貼
        data['avatarBase64'] = file_to_base64(avatar_path)

    # ✅ 儲存 JSON 設定檔
    settings_file = os.path.join(settings_folder, 'settings.json')
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 重新生成 HTML
    generate_business_card(settings_folder, data)

    print(f"✅ 設定已成功儲存，跳轉到電子名片頁面")
    return redirect(f'/get-business-card/{settings_id}')




def generate_business_card(folder, data):
    """生成電子名片 HTML 文件，確保每次覆蓋舊檔案"""

    os.makedirs(folder, exist_ok=True)

    # 確保 Base64 圖片存在
    avatar_base64 = data.get('avatarBase64') or file_to_base64(os.path.join(folder, 'avatar.png'))
    background_base64 = data.get('backgroundImageBase64') or file_to_base64(os.path.join(folder, 'background.png'))

    # ✅ 背景設定處理（修正邏輯）
    if data.get("background") == "custom_color":
        background_style = f'background-color: {data.get("customColor")};'
    elif data.get("background") == "custom_image" and background_base64:
        background_style = f'background-image: url({background_base64}); background-size: cover; background-position: center;'
    else:
        background_style = "background-color: #ffffff;"  # 預設白色

    # 設定社群連結
    social_icons = {
        "facebook": "https://upload.wikimedia.org/wikipedia/commons/4/44/Facebook_Logo.png",
        "instagram": "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png",
        "x": "https://s3-symbol-logo.tradingview.com/twitter--600.png",
        "youtube": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/YouTube_social_white_circle_%282017%29.svg/640px-YouTube_social_white_circle_%282017%29.svg.png",
        "line": "https://upload.wikimedia.org/wikipedia/commons/4/41/LINE_logo.svg",
        "line_official": "https://vos.line-scdn.net/loamkt-static/images/uploads/site_settings/d2be10c727a8be900660b078739b50a5.png"
    }

    social_links = ""
    for key, icon in social_icons.items():
        value = data.get(key, '').strip()
        if value:
            social_links += f"""
            <div class="social-link">
                <a href="{value}" target="_blank">
                    <img src="{icon}" alt="{key}" title="{key}" />
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
                {background_style}  /* ✅ 背景設定（確保顏色能正確覆蓋圖片） */
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
            .name {{
                font-size: 24px;
                font-weight: bold;
                margin-top: 10px;
                color: {data.get('nameColor', '#000000')}; 
            }}
            .title {{
                font-size: 18px;
                margin-top: 5px;
                color: {data.get('titleColor', '#000000')};
            }}
            .description {{
                font-size: 16px;
                margin: 15px 0;
                color: {data.get('descriptionColor', '#000000')};
            }}
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

    # 儲存 HTML
    card_path = os.path.join(folder, 'business_card.html')
    with open(card_path, 'w', encoding='utf-8') as f:
        f.write(card_html)

    print(f"✅ business_card.html 已成功儲存到 {card_path}")






@app.route('/get-business-card/<settings_id>')
def get_business_card(settings_id):
    """返回電子名片 HTML"""
    return send_from_directory(os.path.join(BASE_DIR, settings_id), 'business_card.html')

if __name__ == '__main__':
    app.run(debug=True)
