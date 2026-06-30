from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "The Rejection Whisperer is alive."

@app.route('/dashboard')
def dashboard():
    return "<h1>Dashboard</h1><p>Simple version - working!</p>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
