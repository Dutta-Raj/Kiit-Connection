from flask import Flask, send_file, jsonify
import os

app = Flask(__name__)

# Serve index.html for the root URL
@app.route('/')
def index():
    try:
        return send_file('index.html')
    except FileNotFoundError:
        return "index.html not found. Please check your deployment.", 404

# Serve manifest.json for PWA
@app.route('/manifest.json')
def manifest():
    try:
        return send_file('manifest.json')
    except FileNotFoundError:
        return jsonify({"error": "manifest.json not found"}), 404

# Serve service worker with correct MIME type
@app.route('/sw.js')
def service_worker():
    try:
        return send_file('sw.js'), 200, {'Content-Type': 'application/javascript'}
    except FileNotFoundError:
        return "Service worker not found", 404

# Serve icons
@app.route('/icon-<size>.png')
def icon(size):
    filename = f'icon-{size}.png'
    try:
        return send_file(filename)
    except FileNotFoundError:
        return f"Icon {filename} not found", 404

# Serve all other static files (CSS, JS, images, etc.)
@app.route('/<path:filename>')
def serve_static(filename):
    # List of allowed static files
    allowed_files = [
        'firebaserc', '_redirects', 'firestore.indexes.json',
        'firestore.rules', 'index.html.backup', 'requirements.txt',
        'Procfile', 'render.yaml', '.gitignore'
    ]
    
    # Check if file exists and is allowed
    if os.path.exists(filename):
        # Security: only serve files from current directory
        if filename in allowed_files or filename.startswith('icon-') or filename.endswith(('.png', '.jpg', '.jpeg', '.ico', '.txt', '.json')):
            return send_file(filename)
        else:
            return "Access denied", 403
    else:
        return "File not found", 404

# Health check endpoint - VERY IMPORTANT for Render
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'kiit-connect',
        'version': '1.0.0',
        'pwa_support': True,
        'endpoints': ['/', '/manifest.json', '/sw.js', '/icon-192.png', '/icon-512.png']
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Get port from environment variable (Render provides this)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app - CRITICAL for Render deployment
    app.run(
        host='0.0.0.0',  # Listen on all network interfaces
        port=port,        # Use Render's assigned port
        debug=False       # Debug MUST be False in production
    )