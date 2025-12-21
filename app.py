from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/manifest.json')
def manifest():
    return send_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_file('sw.js'), 200, {'Content-Type': 'application/javascript'}

@app.route('/icon-<size>.png')
def icon(size):
    return send_file(f'icon-{size}.png')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
