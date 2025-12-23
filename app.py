from flask import Flask, render_template, jsonify, request, session, redirect, send_from_directory
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

load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
CORS(app)

# PWA Configuration
app.config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'jwt-secret-change-me')
app.config['PWA_NAME'] = 'KIIT Connect'
app.config['PWA_THEME_COLOR'] = '#1a237e'

# MongoDB Connection
MONGODB_URI = os.environ.get('MONGODB_URI')
client = None
users_collection = None
cafeterias_collection = None
hostels_collection = None

if MONGODB_URI:
    try:
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas!")
        
        db = client['kiit_connect']
        users_collection = db['users']
        cafeterias_collection = db['cafeterias']
        hostels_collection = db['hostels']
        print("✅ Database initialized!")
    except Exception as e:
        print(f"❌ MongoDB Error: {e}")
        client = None
else:
    print("⚠️ MONGODB_URI not found in .env")

# Helper functions
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
            # In demo mode, accept any token
            request.user = {
                'email': data.get('email', 'demo@kiit.ac.in'),
                'role': data.get('role', 'student')
            }
        except:
            return jsonify({'success': False, 'message': 'Invalid token!'}), 401
        
        return f(*args, **kwargs)
    return decorated

# ========== PWA ROUTES ==========
@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('.', 'service-worker.js'), 200, {'Content-Type': 'application/javascript'}

# ========== MAIN ROUTES ==========
@app.route('/')
def index():
    return render_template('index.html', pwa_name=app.config['PWA_NAME'])

@app.route('/dashboard')
def dashboard():
    # In demo mode, allow access without session
    if 'user_email' not in session:
        # Auto-create demo session
        session['user_email'] = 'demo@kiit.ac.in'
        session['user_name'] = 'Demo User'
    return render_template('kiitnav.html', username=session.get('user_name', 'User'))

# ========== AUTH API ==========
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    # DEMO MODE: Accept any non-empty login
    if email and password:
        # Try real MongoDB login first
        if users_collection is not None:
            user = users_collection.find_one({'email': email})
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
                session['user_email'] = email
                session['user_name'] = user.get('name', 'User')
                session['user_id'] = str(user['_id'])
                
                token = jwt.encode({
                    'email': email,
                    'user_id': str(user['_id']),
                    'role': user.get('role', 'student'),
                    'exp': datetime.utcnow().timestamp() + 86400
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
        
        # DEMO FALLBACK: Accept any login
        session['user_email'] = email
        session['user_name'] = email.split('@')[0]
        
        token = jwt.encode({
            'email': email,
            'user_id': 'demo_user',
            'role': 'student',
            'exp': datetime.utcnow().timestamp() + 86400
        }, app.config['JWT_SECRET'])
        
        return jsonify({
            'success': True,
            'message': 'Login successful! (Demo Mode)',
            'token': token,
            'user': {
                'email': email,
                'name': email.split('@')[0],
                'role': 'student'
            }
        })
    
    return jsonify({'success': False, 'message': 'Please enter email and password'}), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    name = data.get('name', email.split('@')[0])
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400
    
    # Try real MongoDB registration
    if users_collection is not None:
        if users_collection.find_one({'email': email}):
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user_data = {
            'email': email,
            'password': hashed_password,
            'name': name,
            'role': 'student',
            'created_at': datetime.utcnow(),
            'last_login': datetime.utcnow()
        }
        
        result = users_collection.insert_one(user_data)
        
        session['user_email'] = email
        session['user_name'] = name
        session['user_id'] = str(result.inserted_id)
        
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
    
    # DEMO FALLBACK: Accept registration without DB
    session['user_email'] = email
    session['user_name'] = name
    
    token = jwt.encode({
        'email': email,
        'user_id': f'demo_{email}',
        'role': 'student',
        'exp': datetime.utcnow().timestamp() + 86400
    }, app.config['JWT_SECRET'])
    
    return jsonify({
        'success': True,
        'message': 'Registration successful! (Demo Mode)',
        'token': token,
        'user': {
            'email': email,
            'name': name,
            'role': 'student'
        }
    })

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# ========== DATA API ==========
@app.route('/api/cafeterias', methods=['GET'])
@token_required
def api_cafeterias():
    # Return demo data if no MongoDB
    if cafeterias_collection is None:
        demo_cafeterias = [
            {
                'name': 'Food Court 1',
                'location': 'Campus Center',
                'cuisine': ['Indian', 'Chinese', 'Fast Food'],
                'opening_hours': '8:00 AM - 10:00 PM',
                'rating': 4.2
            },
            {
                'name': 'Cafe Coffee Day',
                'location': 'Near Library',
                'cuisine': ['Coffee', 'Snacks', 'Beverages'],
                'opening_hours': '7:00 AM - 11:00 PM',
                'rating': 4.5
            }
        ]
        return jsonify({'success': True, 'data': demo_cafeterias})
    
    cafeterias = list(cafeterias_collection.find({}))
    return jsonify({'success': True, 'data': mongo_to_json(cafeterias)})

@app.route('/api/hostels', methods=['GET'])
@token_required
def api_hostels():
    # Return demo data if no MongoDB
    if hostels_collection is None:
        demo_hostels = [
            {
                'name': 'King\'s Palace 1 (Boys)',
                'type': 'Boys',
                'capacity': 200,
                'warden': 'Dr. R. K. Patel',
                'contact': '9876543210',
                'facilities': ['WiFi', 'Gym', 'Laundry', 'AC']
            },
            {
                'name': 'Queen\'s Castle 4 (Girls)',
                'type': 'Girls',
                'capacity': 180,
                'warden': 'Dr. S. Mohanty',
                'contact': '9876543211',
                'facilities': ['WiFi', 'Gym', 'Laundry', 'AC', '24/7 Security']
            }
        ]
        return jsonify({'success': True, 'data': demo_hostels})
    
    hostels = list(hostels_collection.find({}))
    return jsonify({'success': True, 'data': mongo_to_json(hostels)})

@app.route('/api/locations', methods=['GET'])
@token_required
def api_locations():
    try:
        with open('data/locations.json', 'r') as f:
            locations = json.load(f)
        return jsonify({'success': True, 'data': locations})
    except:
        # Return demo locations
        demo_locations = [
            {'name': 'Campus 3 Academic Block', 'type': 'academic', 'lat': 20.352761, 'lng': 85.817242},
            {'name': 'Central Library', 'type': 'library', 'lat': 20.354055, 'lng': 85.816373},
            {'name': 'Food Court 1', 'type': 'cafeteria', 'lat': 20.355000, 'lng': 85.817000},
            {'name': 'King\'s Palace 1', 'type': 'hostel', 'lat': 20.354401, 'lng': 85.820217},
            {'name': 'KIIT Cricket Field', 'type': 'sports', 'lat': 20.357353, 'lng': 85.817941}
        ]
        return jsonify({'success': True, 'data': demo_locations})

@app.route('/api/personnel', methods=['GET'])
@token_required
def api_personnel():
    try:
        with open('data/personnel.json', 'r') as f:
            personnel = json.load(f)
        return jsonify({'success': True, 'data': personnel})
    except:
        # Return demo personnel
        demo_personnel = [
            {
                'title': 'Director General',
                'name': 'Prof. Sasmita Samanta',
                'office': 'Campus 3, Administrative Block',
                'room': 'DG Office, 3rd Floor',
                'campus': 'Campus 3',
                'phone': '0674-272-7777'
            },
            {
                'title': 'Dean - School of Computer Engineering',
                'name': 'Prof. Amiya Kumar Rath',
                'office': 'Campus 3',
                'room': 'Room 301, CS Building',
                'campus': 'Campus 3',
                'phone': '0674-272-8888'
            }
        ]
        return jsonify({'success': True, 'data': demo_personnel})

# ========== CHATBOT API ==========
@app.route('/api/chatbot', methods=['POST'])
@token_required
def api_chatbot():
    data = request.get_json()
    message = data.get('message', '').lower()
    
    responses = {
        'hostel': 'We have King\'s Palace (boys) and Queen\'s Castle (girls) hostels. Use the map to locate them.',
        'cafeteria': 'Food Court 1 (Campus Center) and Cafe Coffee Day (Near Library) are open 8AM-10PM.',
        'library': 'Central Library is open 8AM-10PM. KIMS Library is in Campus 6.',
        'academic': 'Academic blocks are in Campus 3, 7, 8, 12, 14, 15, 16, 17, and 25.',
        'sports': 'We have cricket field, indoor stadium, football stadium, and hockey stadium.',
        'admin': 'Administrative offices are in Campus 3. Visit for any official work.',
        'hello': 'Hello! I\'m your KIIT campus assistant. Ask me about hostels, cafeterias, or directions.',
        'help': 'I can help you find: hostels, cafeterias, libraries, academic blocks, sports facilities.'
    }
    
    response = "I'm not sure about that. Try asking about hostels, cafeterias, libraries, or directions."
    for key in responses:
        if key in message:
            response = responses[key]
            break
    
    return jsonify({
        'success': True,
        'response': response
    })

# ========== HEALTH CHECK ==========
@app.route('/api/health', methods=['GET'])
def api_health():
    db_status = 'connected' if client else 'disconnected'
    return jsonify({
        'status': 'ok',
        'database': db_status,
        'app': 'KIIT Connect',
        'pwa': True,
        'version': '1.0.0'
    })

# ========== MAIN ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True, use_reloader=False)