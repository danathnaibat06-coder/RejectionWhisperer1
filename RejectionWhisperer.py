from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# ===================== قاعدة البيانات =====================

def init_db():
    conn = sqlite3.connect('rejections.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS rejections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pr_number INTEGER,
            repo_name TEXT,
            pr_title TEXT,
            author TEXT,
            classification TEXT,
            action TEXT,
            url TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized.")

def save_rejection(pr_number, repo_name, pr_title, author, classification, action, url):
    conn = sqlite3.connect('rejections.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO rejections (pr_number, repo_name, pr_title, author, classification, action, url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (pr_number, repo_name, pr_title, author, classification, action, url))
    conn.commit()
    conn.close()
    print(f"Saved PR #{pr_number} to database.")

# ===================== تصنيف البوت =====================

AI_AGENTS = ['copilot', 'dependabot', 'devin', 'cursor', 'claude', 'codex', 'github-actions', 'renovate']

def is_ai_agent(username):
    if not username:
        return False
    username_lower = username.lower()
    for agent in AI_AGENTS:
        if agent in username_lower:
            return True
    return False

def is_silent_rejection(pr_data):
    comments = pr_data.get('comments', 0)
    review_comments = pr_data.get('review_comments', 0)
    return (comments + review_comments) == 0

def classify_pr(pr_data):
    state = pr_data.get('state', '')
    merged = pr_data.get('merged', False)
    
    if state == 'closed' and not merged:
        user = pr_data.get('user', {})
        username = user.get('login', '')
        
        if is_ai_agent(username):
            if is_silent_rejection(pr_data):
                return 'Silent AI Rejection'
            else:
                return 'AI Rejection with Comments'
        else:
            if is_silent_rejection(pr_data):
                return 'Silent Human Rejection'
            else:
                return 'Human Rejection with Comments'
    elif state == 'closed' and merged:
        return 'Merged'
    else:
        return 'Open'

# ===================== مسارات Flask =====================

@app.route('/')
def home():
    return "The Rejection Whisperer is alive."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'pull_request' not in data:
        return jsonify({"status": "ignored"}), 200
    
    pr_data = data.get('pull_request', {})
    action = data.get('action', '')
    pr_number = pr_data.get('number', '')
    pr_title = pr_data.get('title', '')
    pr_url = pr_data.get('html_url', '')
    username = pr_data.get('user', {}).get('login', '')
    repo_name = data.get('repository', {}).get('full_name', 'unknown')
    
    classification = classify_pr(pr_data)
    
    print("=" * 60)
    print(f"PR #{pr_number}: {pr_title}")
    print(f"Author: {username}")
    print(f"Action: {action}")
    print(f"Classification: {classification}")
    print(f"URL: {pr_url}")
    print("=" * 60)
    
    if classification in ['Silent AI Rejection', 'AI Rejection with Comments', 
                          'Silent Human Rejection', 'Human Rejection with Comments']:
        save_rejection(pr_number, repo_name, pr_title, username, classification, action, pr_url)
    
    return jsonify({"status": "received"}), 200

# ===================== عرض الإحصائيات (جديد) =====================

@app.route('/stats', methods=['GET'])
def stats():
    conn = sqlite3.connect('rejections.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM rejections')
    total = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT classification, COUNT(*) 
        FROM rejections 
        GROUP BY classification
    ''')
    stats = cursor.fetchall()
    
    conn.close()
    
    result = {
        "total_rejections": total,
        "by_classification": {classification: count for classification, count in stats}
    }
    return jsonify(result)

# ===================== تشغيل البوت =====================

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)