from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_from_directory
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL', 'rajdeepdutta104@gmail.com')
app.config['MAPTILER_API_KEY'] = os.environ.get('MAPTILER_API_KEY', '1DAJJ44xYcqv8JcwhP0L')

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
        return render_template('kiitnav.html', 
                             username=session['user'],
                             maptiler_key=app.config['MAPTILER_API_KEY'])
    else:
        return render_template('index.html')

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if email in USERS and USERS[email] == password:
        session['user'] = email
        return jsonify({
            'success': True, 
            'message': 'Login successful!',
            'user': email
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

# Logout endpoint
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# API endpoints
@app.route('/api/locations')
def get_locations():
    try:
        with open('data/locations.json', 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])

@app.route('/api/personnel')
def get_personnel():
    try:
        with open('data/personnel.json', 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])

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

# Health check
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok', 
        'authenticated': is_logged_in(),
        'app': 'KIIT Connect'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)