from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_from_directory
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration from environment variables
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this-in-production')
app.config['FIREBASE_CONFIG'] = {
    'apiKey': os.environ.get('FIREBASE_API_KEY', 'AIzaSyAvdVw_yOQtxvSd9MTU_hRz1AD6RDCaQ0A'),
    'authDomain': os.environ.get('FIREBASE_AUTH_DOMAIN', 'navigator-4a29d.firebaseapp.com'),
    'projectId': os.environ.get('FIREBASE_PROJECT_ID', 'navigator-4a29d'),
    'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'navigator-4a29d.firebasestorage.app'),
    'messagingSenderId': os.environ.get('FIREBASE_MESSAGING_SENDER_ID', '670551267892'),
    'appId': os.environ.get('FIREBASE_APP_ID', '1:670551267892:web:3c7f7a66c53f262adcc861')
}
app.config['MAPTILER_API_KEY'] = os.environ.get('MAPTILER_API_KEY', '1DAJJ44xYcqv8JcwhP0L')
app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL', 'rajdeepdutta104@gmail.com')

# Simple user database (in production, use Firebase authentication)
USERS = {
    'student@kiit.ac.in': 'password123',
    'admin@kiit.ac.in': 'admin123',
    'rajdeepdutta104@gmail.com': 'admin123'
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
                             admin_email=app.config['ADMIN_EMAIL'],
                             firebase_config=app.config['FIREBASE_CONFIG'],
                             maptiler_key=app.config['MAPTILER_API_KEY'])
    else:
        # Not logged in - show login/landing page
        return render_template('index.html')

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
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
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js'), 200, {'Content-Type': 'application/javascript'}

@app.route('/icon-<size>.png')
def icon(size):
    return send_from_directory('static', f'icon-{size}.png')

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
                {"name": "Campus 3 Academic Block", "lat": 20.352761729599813, "lng": 85.81724230083005},
                {"name": "Campus 7 Academic Block", "lat": 20.350520271622248, "lng": 85.82070018739302}
            ],
            'hostels': [
                {"name": "King's Palace 1", "lat": 20.35440136062493, "lng": 85.82021742698775},
                {"name": "Queen's Castle 1", "lat": 20.352478588914085, "lng": 85.81809212225603}
            ],
            'cafeterias': [
                {"name": "Main Cafeteria", "lat": 20.354055, "lng": 85.816373}
            ],
            'libraries': [
                {"name": "Central Library", "lat": 20.354055008292377, "lng": 85.81637333664973}
            ],
            'sports': [
                {"name": "Cricket Field", "lat": 20.357353810053166, "lng": 85.81794109873883}
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
        'app': 'KIIT Connect',
        'version': '2.0.0',
        'admin_email': app.config['ADMIN_EMAIL']
    })

# Serve any other static file
@app.route('/<path:filename>')
def serve_file(filename):
    if filename in ['manifest.json', 'sw.js', 'icon-192.png', 'icon-512.png']:
        return send_from_directory('static', filename)
    return "File not found", 404

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': 'The requested resource was not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error', 'message': 'An internal server error occurred'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)