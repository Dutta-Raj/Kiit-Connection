from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_from_directory
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
app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL', 'rajdeepdutta104@gmail.com')

# Simple user database
USERS = {
    'student@kiit.ac.in': 'password123',
    'admin@kiit.ac.in': 'admin123',
    'rajdeepdutta104@gmail.com': 'admin123'
}

# Check if user is logged in
def is_logged_in():
    return 'user' in session

# Home route
@app.route('/')
def index():
    if is_logged_in():
        # User is logged in - show KIITnav interface
        return render_template('kiitnav.html', 
                             username=session['user'],
                             admin_email=app.config['ADMIN_EMAIL'],
                             firebase_config=app.config['FIREBASE_CONFIG'],
                             maptiler_key=app.config['MAPTILER_API_KEY'])
    else:
        # Not logged in - show login page
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

# Serve static files
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js'), 200, {'Content-Type': 'application/javascript'}

@app.route('/icon-<size>.png')
def icon(size):
    return send_from_directory('static', f'icon-{size}.png')

# API endpoints
@app.route('/api/locations')
def get_locations():
    try:
        with open('data/locations.json', 'r') as f:
            locations = json.load(f)
        return jsonify(locations)
    except FileNotFoundError:
        return jsonify([])

@app.route('/api/personnel')
def get_personnel():
    try:
        with open('data/personnel.json', 'r') as f:
            personnel = json.load(f)
        return jsonify(personnel)
    except FileNotFoundError:
        return jsonify([])

# Health check
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok', 
        'authenticated': is_logged_in(),
        'app': 'KIIT Connect',
        'version': '2.0.0'
    })

# Serve any other static file
@app.route('/<path:filename>')
def serve_file(filename):
    if filename in ['manifest.json', 'sw.js', 'icon-192.png', 'icon-512.png']:
        return send_from_directory('static', filename)
    return "File not found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False') == 'True'
    app.run(host='0.0.0.0', port=port, debug=debug)