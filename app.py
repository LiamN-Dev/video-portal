from flask import Flask, render_template, request, redirect, url_for, session
import os
import json

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
            "videos": []
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
    if 'user' in session:
        return render_template('index.html', 
                               logged_in=True, 
                               name=session['name'], 
                               tier=session['tier'],
                               videos=data['videos'])
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

# --- ADMIN DASHBOARD ---
@app.route('/admin')
def admin_dashboard():
    if session.get('tier') != 'admin':
        return "Access Denied: Admin Clearance Required", 403
    data = load_data()
    return render_template('admin.html', users=data['users'], videos=data['videos'])

# Route to Add a New User
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
    return redirect(url_for('admin_dashboard'))

# Route to Modify an Existing User (Edits Emails, Passwords, Phone, and Tiers)
@app.route('/admin/update-user', methods=['POST'])
def update_user():
    if session.get('tier') != 'admin': return "Unauthorized", 403
    data = load_data()
    
    old_email = request.form.get('old_email')
    new_email = request.form.get('new_email', '').lower().strip()
    
    # If the admin changed the email string, remove the old key safely
    if old_email in data['users']:
        user_info = data['users'].pop(old_email)
        
        # Pull the values directly out of the editable row fields
        user_info['name'] = request.form.get('name')
        user_info['password'] = request.form.get('password')
        user_info['phone'] = request.form.get('phone')
        user_info['tier'] = request.form.get('tier')
        
        # Re-insert under the new email key
        data['users'][new_email] = user_info
        save_data(data)
        
    return redirect(url_for('admin_dashboard'))

# Route to Remove a User Entirely
@app.route('/admin/delete-user/<email>')
def delete_user(email):
    if session.get('tier') != 'admin': return "Unauthorized", 403
    data = load_data()
    if email in data['users']:
        del data['users'][email]
        save_data(data)
    return redirect(url_for('admin_dashboard'))

# Route to Publish Video Frames
@app.route('/admin/add-video', methods=['POST'])
def add_video():
    if session.get('tier') != 'admin': return "Unauthorized", 403
    data = load_data()
    raw_url = request.form.get('url')
    if "watch?v=" in raw_url:
        raw_url = raw_url.replace("watch?v=", "embed/")
    data['videos'].append({
        "title": request.form.get('title'),
        "url": raw_url,
        "tier": request.form.get('tier')
    })
    save_data(data)
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
