from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import os
import secrets
from datetime import datetime, timedelta
import base64
from io import BytesIO

app = Flask(__name__)

# Создаем директорию для временных файлов
TEMP_DIR = 'temp_photos'
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def get_db():
    conn = sqlite3.connect('dating_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/profiles')
def get_profiles():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, name, country, city FROM users WHERE gender = "female" AND is_verified = 1')
    profiles = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'id': profile['user_id'],
        'name': profile['name'],
        'country': profile['country'],
        'city': profile['city']
    } for profile in profiles])

@app.route('/api/profile/<int:profile_id>')
def get_profile(profile_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (profile_id,))
    profile = cursor.fetchone()
    conn.close()
    
    if profile:
        return jsonify({
            'id': profile['user_id'],
            'name': profile['name'],
            'country': profile['country'],
            'city': profile['city'],
            'birthdate': profile['birthdate'],
            'telegram': profile['telegram']
        })
    return jsonify({'error': 'Profile not found'}), 404

@app.route('/api/photos/<int:profile_id>')
def get_photos(profile_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT photos FROM users WHERE user_id = ?', (profile_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return jsonify({'error': 'Photos not found'}), 404
    
    # Создаем временные URL для фотографий
    photo_ids = result['photos'].split(',')
    temp_urls = []
    
    for photo_id in photo_ids:
        # Генерируем уникальный токен
        token = secrets.token_urlsafe(32)
        temp_urls.append(f'/temp/{token}')
        
        # Сохраняем информацию о временном URL
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO temp_photos (token, photo_id, expires_at)
            VALUES (?, ?, ?)
        ''', (token, photo_id, datetime.now() + timedelta(minutes=5)))
        conn.commit()
        conn.close()
    
    return jsonify({'photos': temp_urls})

@app.route('/temp/<token>')
def get_temp_photo(token):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT photo_id, expires_at 
        FROM temp_photos 
        WHERE token = ? AND expires_at > datetime('now')
    ''', (token,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return 'Photo expired or not found', 404
    
    # Получаем фото из базы данных бота
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT photos FROM users WHERE user_id = ?', (result['photo_id'],))
    photos = cursor.fetchone()['photos'].split(',')
    conn.close()
    
    # Отправляем первое фото
    return send_file(BytesIO(base64.b64decode(photos[0])), mimetype='image/jpeg')

if __name__ == '__main__':
    # Создаем таблицу для временных URL
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_photos (
            token TEXT PRIMARY KEY,
            photo_id TEXT,
            expires_at DATETIME
        )
    ''')
    conn.commit()
    conn.close()
    
    app.run(debug=True) 