from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId, json_util
import os
import json
import bcrypt
from dotenv import load_dotenv
from datetime import datetime
import jwt
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Configuration
app.config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'jwt-secret-key-change-me')

# MongoDB Connection from .env
MONGODB_URI = os.environ.get('MONGODB_URI')

if not MONGODB_URI:
    print("⚠️ MONGODB_URI not found in .env file!")
    client = None
else:
    try:
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas!")
    except Exception as e:
        print(f"❌ MongoDB Connection Error: {e}")
        client = None

# Database setup
if client:
    db = client['kiit_connect']
    users_collection = db['users']
    # Collections will be empty initially
    cafeterias_collection = db['cafeterias']
    hostels_collection = db['hostels']
    print("✅ Database 'kiit_connect' ready!")
else:
    db = None
    users_collection = None
    cafeterias_collection = None
    hostels_collection = None

def mongo_to_json(data):
    return json.loads(json_util.dumps(data))

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token or not token.startswith('Bearer '):
            return jsonify({'success': False, 'message': 'Login required!'}), 401
        
        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=["HS256"])
            user = users_collection.find_one({'email': data['email']}) if users_collection else None
            if not user:
                return jsonify({'success': False, 'message': 'User not found!'}), 401
        except:
            return jsonify({'success': False, 'message': 'Invalid token!'}), 401
        
        return f(user, *args, **kwargs)
    return decorated

# ========== ROUTES ==========

# Main login page (only accessible page without login)
@app.route('/')
def index():
    # If already logged in, redirect to dashboard
    if 'user_email' in session:
        return redirect('/dashboard')
    return render_template('index.html')

# Dashboard page (protected)
@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect('/')
    return render_template('kiitnav.html', 
                         username=session.get('user_name', 'User'))

# API: Login with email/password
@app.route('/api/login', methods=['POST'])
def api_login():
    if not users_collection:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = users_collection.find_one({'email': email})
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        # Create session
        session['user_email'] = email
        session['user_name'] = user.get('name', 'User')
        session['user_id'] = str(user['_id'])
        
        # Create JWT token
        token = jwt.encode({
            'email': email,
            'user_id': str(user['_id']),
            'role': user.get('role', 'student'),
            'exp': datetime.utcnow().timestamp() + 86400  # 24 hours
        }, app.config['JWT_SECRET'])
        
        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'token': token,
            'user': {
                'email': email,
                'name': user.get('name', ''),
                'role': user.get('role', 'student')
            }
        })
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

# API: Register new user
@app.route('/api/register', methods=['POST'])
def api_register():
    if not users_collection:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')
    student_id = data.get('student_id', '')
    
    # Check if email already exists
    if users_collection.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    
    # Hash password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Create user document
    user_data = {
        'email': email,
        'password': hashed_password,
        'name': name,
        'student_id': student_id,
        'role': 'student',
        'created_at': datetime.utcnow(),
        'last_login': datetime.utcnow()
    }
    
    # Insert into database
    result = users_collection.insert_one(user_data)
    
    # Auto login after registration
    session['user_email'] = email
    session['user_name'] = name
    session['user_id'] = str(result.inserted_id)
    
    # Create JWT token
    token = jwt.encode({
        'email': email,
        'user_id': str(result.inserted_id),
        'role': 'student',
        'exp': datetime.utcnow().timestamp() + 86400
    }, app.config['JWT_SECRET'])
    
    return jsonify({
        'success': True,
        'message': 'Registration successful!',
        'token': token,
        'user': {
            'email': email,
            'name': name,
            'role': 'student'
        }
    })

# API: Logout
@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# ========== PROTECTED API ENDPOINTS ==========

# API: Get user profile (requires login)
@app.route('/api/profile', methods=['GET'])
@token_required
def api_profile(current_user):
    user_data = current_user.copy()
    user_data.pop('password', None)  # Remove password
    return jsonify({'success': True, 'data': mongo_to_json(user_data)})

# API: Get cafeterias (empty initially - requires login)
@app.route('/api/cafeterias', methods=['GET'])
@token_required
def api_cafeterias(current_user):
    if not cafeterias_collection:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    cafeterias = list(cafeterias_collection.find({}))
    return jsonify({'success': True, 'data': mongo_to_json(cafeterias)})

# API: Get hostels (empty initially - requires login)
@app.route('/api/hostels', methods=['GET'])
@token_required
def api_hostels(current_user):
    if not hostels_collection:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    hostels = list(hostels_collection.find({}))
    return jsonify({'success': True, 'data': mongo_to_json(hostels)})

# API: Add cafeteria (admin feature - requires login)
@app.route('/api/cafeterias', methods=['POST'])
@token_required
def api_add_cafeteria(current_user):
    if current_user.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    data = request.get_json()
    
    cafeteria_data = {
        'name': data.get('name'),
        'location': data.get('location'),
        'cuisine': data.get('cuisine', []),
        'opening_hours': data.get('opening_hours'),
        'rating': data.get('rating', 0),
        'created_by': current_user['_id'],
        'created_at': datetime.utcnow()
    }
    
    result = cafeterias_collection.insert_one(cafeteria_data)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

# API: Add hostel (admin feature - requires login)
@app.route('/api/hostels', methods=['POST'])
@token_required
def api_add_hostel(current_user):
    if current_user.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    data = request.get_json()
    
    hostel_data = {
        'name': data.get('name'),
        'type': data.get('type'),
        'capacity': data.get('capacity'),
        'warden': data.get('warden'),
        'contact': data.get('contact'),
        'facilities': data.get('facilities', []),
        'created_by': current_user['_id'],
        'created_at': datetime.utcnow()
    }
    
    result = hostels_collection.insert_one(hostel_data)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

# Health check
@app.route('/api/health', methods=['GET'])
def api_health():
    db_status = 'connected' if client else 'disconnected'
    return jsonify({
        'status': 'ok',
        'database': db_status,
        'authenticated': 'user_email' in session,
        'app': 'KIIT Connect'
    })

# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

# ========== MAIN ==========

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)