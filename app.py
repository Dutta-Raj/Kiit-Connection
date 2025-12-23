from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration from environment variables
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
app.config['FIREBASE_CONFIG'] = {
    'apiKey': os.environ.get('FIREBASE_API_KEY'),
    'authDomain': os.environ.get('FIREBASE_AUTH_DOMAIN'),
    'projectId': os.environ.get('FIREBASE_PROJECT_ID'),
    'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET'),
    'messagingSenderId': os.environ.get('FIREBASE_MESSAGING_SENDER_ID'),
    'appId': os.environ.get('FIREBASE_APP_ID')
}
app.config['MAPTILER_API_KEY'] = os.environ.get('MAPTILER_API_KEY')
app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL', 'riddhipdas@gmail.com')

# Simple user database (in production, use Firebase authentication)
USERS = {
    'student@kiit.ac.in': 'password123',
    'admin@kiit.ac.in': 'admin123',
    os.environ.get('ADMIN_EMAIL', 'riddhipdas@gmail.com'): 'admin123'  # Your admin email
}

# Check if user is logged in
def is_logged_in():
    return 'user' in session

# Home route - shows login or KIITnav based on auth
@app.route('/')
def index():
    if is_logged_in():
        # User is logged in - show KIITnav interface
        return render_template('kiitnav.html', 
                             username=session['user'],
                             firebase_config=app.config['FIREBASE_CONFIG'],
                             maptiler_key=app.config['MAPTILER_API_KEY'])
    else:
        # Not logged in - show login/landing page
        return render_template('index.html')

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if email in USERS and USERS[email] == password:
        session['user'] = email
        session['is_admin'] = (email == app.config['ADMIN_EMAIL'])
        return jsonify({
            'success': True, 
            'message': 'Login successful!',
            'user': email,
            'is_admin': session['is_admin']
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

# Logout endpoint
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('is_admin', None)
    return redirect(url_for('index'))

# PWA assets
@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js'), 200, {'Content-Type': 'application/javascript'}

@app.route('/icon-<size>.png')
def icon(size):
    return app.send_static_file(f'icon-{size}.png')

# API endpoint for your KIITnav data
@app.route('/api/locations')
def get_locations():
    try:
        with open('data/locations.json', 'r') as f:
            locations = json.load(f)
        return jsonify(locations)
    except FileNotFoundError:
        # Return sample data if file doesn't exist
        return jsonify({
            'academic': [
                {"name": "Campus 3 Academic Block", "lat": 20.296059, "lng": 85.824539},
                {"name": "Campus 7 Academic Block", "lat": 20.297000, "lng": 85.825000}
            ],
            'hostels': [
                {"name": "King's Palace 1", "lat": 20.354401, "lng": 85.820217},
                {"name": "Queen's Castle 1", "lat": 20.352478, "lng": 85.818092}
            ],
            'cafeterias': [
                {"name": "Main Cafeteria", "lat": 20.295000, "lng": 85.823000}
            ],
            'libraries': [
                {"name": "Central Library", "lat": 20.354055, "lng": 85.816373}
            ],
            'sports': [
                {"name": "Cricket Field", "lat": 20.357353, "lng": 85.817941}
            ]
        })

@app.route('/api/personnel')
def get_personnel():
    try:
        with open('data/personnel.json', 'r') as f:
            personnel = json.load(f)
        return jsonify(personnel)
    except FileNotFoundError:
        # Return sample personnel data
        return jsonify([
            {
                "title": "Director General",
                "name": "Prof. Sasmita Samanta",
                "office": "Campus 3, Administrative Block",
                "room": "DG Office, 3rd Floor",
                "campus": "Campus 3",
                "phone": "0674-272-7777",
                "lat": 20.3555,
                "lng": 85.8188
            },
            {
                "title": "Dean - School of Computer Engineering",
                "name": "Prof. Amiya Kumar Rath",
                "office": "Campus 3",
                "room": "Room 301, CS Building",
                "campus": "Campus 3",
                "phone": "0674-272-8888",
                "lat": 20.3555,
                "lng": 85.8188
            }
        ])

# Health check
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok', 
        'authenticated': is_logged_in(),
        'app': os.environ.get('APP_NAME', 'KIIT Connect'),
        'debug': os.environ.get('DEBUG', 'False') == 'True'
    })

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False') == 'True'
    app.run(host='0.0.0.0', port=port, debug=debug)