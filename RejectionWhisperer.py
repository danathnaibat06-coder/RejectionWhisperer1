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

@app.route('/dashboard')
def dashboard():
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
    
    cursor.execute('''
        SELECT pr_title, author, classification, timestamp 
        FROM rejections 
        ORDER BY timestamp DESC 
        LIMIT 5
    ''')
    recent = cursor.fetchall()
    
    conn.close()
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rejection Whisperer - Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f5f7fa;
                color: #333;
            }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            .stats {{
                display: flex;
                gap: 20px;
                flex-wrap: wrap;
                margin: 30px 0;
            }}
            .card {{
                background: white;
                padding: 20px 30px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                flex: 1;
                min-width: 150px;
                text-align: center;
            }}
            .card h3 {{
                margin: 0;
                font-weight: normal;
                color: #7f8c8d;
                font-size: 14px;
                text-transform: uppercase;
            }}
            .card .number {{
                font-size: 36px;
                font-weight: bold;
                color: #2c3e50;
                margin: 10px 0 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                margin-top: 20px;
            }}
            th {{
                background: #3498db;
                color: white;
                padding: 12px;
                text-align: left;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #ecf0f1;
            }}
            tr:hover {{ background-color: #f8f9fa; }}
            .badge-ai-silent {{ background: #e74c3c; color: white; padding: 4px 12px; border-radius: 20px; }}
            .badge-ai-comment {{ background: #e67e22; color: white; padding: 4px 12px; border-radius: 20px; }}
            .badge-human-silent {{ background: #3498db; color: white; padding: 4px 12px; border-radius: 20px; }}
            .badge-human-comment {{ background: #2ecc71; color: white; padding: 4px 12px; border-radius: 20px; }}
            .badge-merged {{ background: #9b59b6; color: white; padding: 4px 12px; border-radius: 20px; }}
            .badge-open {{ background: #95a5a6; color: white; padding: 4px 12px; border-radius: 20px; }}
            .footer {{ margin-top: 40px; text-align: center; color: #95a5a6; font-size: 14px; }}
            .footer a {{ color: #3498db; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>Rejection Whisperer - Dashboard</h1>
        
        <div class="stats">
            <div class="card">
                <h3>Total Rejections</h3>
                <div class="number">{total}</div>
            </div>
    '''
    
    for classification, count in stats:
        html += f'''
            <div class="card">
                <h3>{classification}</h3>
                <div class="number">{count}</div>
            </div>
        '''
    
    html += '''
        </div>
        
        <h2>Recent Rejections</h2>
        <table>
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Author</th>
                    <th>Classification</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
    '''
    
    if recent:
        for title, author, classification, timestamp in recent:
            badge_class = classification.replace(' ', '-').lower()
            html += f'''
                <tr>
                    <td>{title}</td>
                    <td>{author}</td>
                    <td><span class="badge-{badge_class}">{classification}</span></td>
                    <td>{timestamp}</td>
                </tr>
            '''
    else:
        html += '''
            <tr>
                <td colspan="4" style="text-align: center; color: #95a5a6;">No rejections recorded yet.</td>
            </tr>
        '''
    
    html += '''
            </tbody>
        </table>
        
        <div class="footer">
            <p><a href="/stats">View raw JSON stats</a></p>
            <p>Powered by The Rejection Whisperer</p>
        </div>
    </body>
    </html>
    '''
    
    return html

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
