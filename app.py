from flask import Flask, render_template, request, redirect, url_for, session
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

DATA_FILE = 'data.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        initial_data = {
            "users": {
                "admin@bstream.com": {"password": "AdminSecure77", "name": "Liam (Admin)", "phone": "N/A", "tier": "admin"},
                "grandpa@email.com": {"password": "GrandpaPassword123", "name": "Grandpa Joe", "phone": "239-555-0199", "tier": "bonus"}
            },
            "videos": [
                {"id": 1, "title": "Grandpa's First Video", "url": "https://www.youtube.com/embed/dQw4w9WgXcQ", "tier": "standard"}
            ],
            "comments": {} # Stores lists of comments keyed by video title/id
        }
        save_data(initial_data)
        return initial_data
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def home():
    data = load_data()
    # Ensure comments dictionary exists in older data structures
    if "comments" not in data:
        data["comments"] = {}
        save_data(data)

    if 'user' in session:
        return render_template('index.html', 
                               logged_in=True, 
                               name=session['name'], 
                               tier=session['tier'],
                               user_email=session['user'],
                               videos=data['videos'],
                               comments=data['comments'],
                               users_list=data['users']) # Sent safely for inline dashboard rendering
    return render_template('index.html', logged_in=False)

@app.route('/login', methods=['POST'])
def login():
    data = load_data()
    email = request.form.get('email', '').lower().strip()
    password = request.form.get('password', '')

    if email in data['users'] and data['users'][email]['password'] == password:
        session['user'] = email
        session['name'] = data['users'][email]['name']
        session['tier'] = data['users'][email]['tier']
        return redirect(url_for('home'))
    return redirect(url_for('home', error="invalid"))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- POST A COMMENT ---
@app.route('/add-comment', methods=['POST'])
def add_comment():
    if 'user' not in session: return "Unauthorized", 401
    data = load_data()
    
    video_title = request.form.get('video_title')
    comment_text = request.form.get('comment_text', '').strip()
    
    if comment_text and video_title:
        if video_title not in data['comments']:
            data['comments'][video_title] = []
            
        timestamp = datetime.now().strftime("%b %d, %Y at %I:%M %p")
        data['comments'][video_title].append({
            "author": session['name'],
            "text": comment_text,
            "time": timestamp
        })
        save_data(data)
    return redirect(url_for('home'))

# --- ADMIN FUNCTIONS (No /admin extension route!) ---
@app.route('/admin/add-user', methods=['POST'])
def add_user():
    if session.get('tier') != 'admin': return "Unauthorized", 403
    data = load_data()
    email = request.form.get('email', '').lower().strip()
    data['users'][email] = {
        "password": request.form.get('password'),
        "name": request.form.get('name'),
        "phone": request.form.get('phone', 'N/A'),
        "tier": request.form.get('tier')
    }
    save_data(data)
    return redirect(url_for('home', open_admin="true"))

@app.route('/admin/update-user', methods=['POST'])
def update_user():
    if session.get('tier') != 'admin': return "Unauthorized", 403
    data = load_data()
    old_email = request.form.get('old_email')
    new_email = request.form.get('new_email', '').lower().strip()
    
    if old_email in data['users']:
        user_info = data['users'].pop(old_email)
        user_info['name'] = request.form.get('name')
        user_info['password'] = request.form.get('password')
        user_info['phone'] = request.form.get('phone')
        user_info['tier'] = request.form.get('tier')
        data['users'][new_email] = user_info
        save_data(data)
    return redirect(url_for('home', open_admin="true"))

@app.route('/admin/delete-user/<email>')
def delete_user(email):
    if session.get('tier') != 'admin': return "Unauthorized", 403
    data = load_data()
    if email in data['users']:
        del data['users'][email]
        save_data(data)
    return redirect(url_for('home', open_admin="true"))

@app.route('/admin/add-video', methods=['POST'])
def add_video():
    if session.get('tier') != 'admin': return "Unauthorized", 403
    data = load_data()
    raw_url = request.form.get('url')
    
    # Converts standard links to standard working embeds automatically
    if "watch?v=" in raw_url:
        raw_url = raw_url.replace("watch?v=", "embed/")
    elif "youtu.be/" in raw_url:
        raw_url = raw_url.replace("youtu.be/", "youtube.com/embed/")

    new_id = len(data['videos']) + 1 if data['videos'] else 1
    data['videos'].append({
        "id": new_id,
        "title": request.form.get('title'),
        "url": raw_url,
        "tier": request.form.get('tier')
    })
    save_data(data)
    return redirect(url_for('home', open_admin="true"))

@app.route('/admin/delete-video/<int:video_id>')
def delete_video(video_id):
    if session.get('tier') != 'admin': return "Unauthorized", 403
    data = load_data()
    # Filter out the video with the matching id
    data['videos'] = [v for v in data['videos'] if v['id'] != video_id]
    save_data(data)
    return redirect(url_for('home', open_admin="true"))

if __name__ == '__main__':
    app.run(debug=True)
