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
                "admin@bstream.com": {"password": "AdminSecure77", "name": "Liam (Admin)", "phone": "N/A", "tier": "admin"}
            },
            "videos": [],
            "comments": {},
            "announcements": {
                "global": [], # System-wide announcements
                "user_specific": {} # Email linked personal notifications
            },
            "maintenance_mode": False
        }
        save_data(initial_data)
        return initial_data
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
        # Ensure new keys exist if migrating older database models
        if "announcements" not in data:
            data["announcements"] = {"global": [], "user_specific": {}}
        if "maintenance_mode" not in data:
            data["maintenance_mode"] = False
        return data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def home():
    data = load_data()
    
    # MAINTENANCE OVERRIDE RULE
    if data.get('maintenance_mode', False):
        # If not logged in, or logged in as standard/bonus, show update screen
        if 'user' not in session or session.get('tier') not in ['admin', 'supervisor']:
            return render_template('index.html', logged_in=False, maintenance=True)

    if 'user' in session:
        user_email = session['user']
        global_announcements = data['announcements']['global']
        personal_announcements = data['announcements']['user_specific'].get(user_email, [])
        
        return render_template('index.html', 
                               logged_in=True, 
                               name=session['name'], 
                               tier=session['tier'],
                               user_email=user_email,
                               videos=data['videos'],
                               comments=data['comments'],
                               global_announcements=global_announcements,
                               personal_announcements=personal_announcements,
                               maintenance_state=data.get('maintenance_mode', False),
                               users_list=data['users'])
    return render_template('index.html', logged_in=False, maintenance=False)

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

# --- COMMENTS DISPATCHER ---
@app.route('/add-comment', methods=['POST'])
def add_comment():
    if 'user' not in session: return "Unauthorized", 401
    data = load_data()
    video_id = request.form.get('video_id')
    comment_text = request.form.get('comment_text', '').strip()
    
    if comment_text and video_id:
        if str(video_id) not in data['comments']:
            data['comments'][str(video_id)] = []
        timestamp = datetime.now().strftime("%b %d, %Y at %I:%M %p")
        data['comments'][str(video_id)].append({
            "author": session['name'],
            "text": comment_text,
            "time": timestamp
        })
        save_data(data)
    return redirect(url_for('home'))

# --- NEW: BROADCAST ANNOUNCEMENT DISPATCHER (Admin & Supervisor Enabled) ---
@app.route('/admin/post-announcement', methods=['POST'])
def post_announcement():
    if session.get('tier') not in ['admin', 'supervisor']: return "Unauthorized", 403
    data = load_data()
    
    scope = request.form.get('scope') # 'global' or an actual user email
    content = request.form.get('content', '').strip()
    timestamp = datetime.now().strftime("%b %d at %I:%M %p")
    
    announcement_obj = {
        "id": int(datetime.now().timestamp()),
        "sender": session['name'],
        "content": content,
        "time": timestamp
    }
    
    if scope == 'global':
        data['announcements']['global'].append(announcement_obj)
    else:
        if scope not in data['announcements']['user_specific']:
            data['announcements']['user_specific'][scope] = []
        data['announcements']['user_specific'][scope].append(announcement_obj)
        
    save_data(data)
    return redirect(url_for('home', open_admin="true"))

@app.route('/admin/clear-announcement/<scope>/<int:ann_id>')
def clear_announcement(scope, ann_id):
    if session.get('tier') not in ['admin', 'supervisor']: return "Unauthorized", 403
    data = load_data()
    
    if scope == 'global':
        data['announcements']['global'] = [a for a in data['announcements']['global'] if a['id'] != ann_id]
    elif scope in data['announcements']['user_specific']:
        data['announcements']['user_specific'][scope] = [a for a in data['announcements']['user_specific'][scope] if a['id'] != ann_id]
        
    save_data(data)
    return redirect(url_for('home', open_admin="true"))

# --- NEW: SYSTEM LOCKOUT/UPDATE TOGGLE ---
@app.route('/admin/toggle-maintenance')
def toggle_maintenance():
    if session.get('tier') not in ['admin', 'supervisor']: return "Unauthorized", 403
    data = load_data()
    data['maintenance_mode'] = not data.get('maintenance_mode', False)
    save_data(data)
    return redirect(url_for('home', open_admin="true"))

# --- IDENTITY DIRECTORY PANEL (Admin Only) ---
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

# --- ARCHIVE STREAMS MANAGEMENT (Admin & Supervisor) ---
@app.route('/admin/add-video', methods=['POST'])
def add_video():
    if session.get('tier') not in ['admin', 'supervisor']: return "Unauthorized", 403
    data = load_data()
    raw_url = request.form.get('url')
    
    if "watch?v=" in raw_url:
        raw_url = raw_url.replace("watch?v=", "embed/")
    elif "youtu.be/" in raw_url:
        raw_url = raw_url.replace("youtu.be/", "youtube.com/embed/")

    new_id = int(datetime.now().timestamp())
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
    if session.get('tier') not in ['admin', 'supervisor']: return "Unauthorized", 403
    data = load_data()
    data['videos'] = [v for v in data['videos'] if v['id'] != video_id]
    save_data(data)
    return redirect(url_for('home', open_admin="true"))

if __name__ == '__main__':
    app.run(debug=True)
