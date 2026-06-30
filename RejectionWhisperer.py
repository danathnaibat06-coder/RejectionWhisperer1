from flask import Flask, request, jsonify
import sqlite3
import os
import requests
from datetime import datetime

app = Flask(__name__)

# ===================== قاعدة البيانات =====================

def init_db():
    conn = sqlite3.connect('rejections.db')
    c = conn.cursor()
    
    # جدول الرفض الرئيسي
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
    
    # نحاول نضيف عمود reasons إذا ما كان موجود
    try:
        c.execute('ALTER TABLE rejections ADD COLUMN reasons TEXT')
        print("Added 'reasons' column to database")
    except:
        print("'reasons' column already exists")
    
    conn.commit()
    conn.close()
    print("Database initialized.")

def save_rejection(pr_number, repo_name, pr_title, author, classification, action, url, reasons):
    conn = sqlite3.connect('rejections.db')
    c = conn.cursor()
    
    reasons_text = ', '.join(reasons) if reasons else 'No reason'
    
    c.execute('''
        INSERT INTO rejections (pr_number, repo_name, pr_title, author, classification, action, url, reasons)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (pr_number, repo_name, pr_title, author, classification, action, url, reasons_text))
    
    conn.commit()
    conn.close()
    print(f"Saved PR #{pr_number} with reasons: {reasons_text}")

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

# ===================== تحليل أسباب الرفض =====================

def analyze_rejection_reason(pr_data, repo_name):
    reasons = []
    pr_body = pr_data.get('body', '').lower()
    pr_title = pr_data.get('title', '').lower()
    
    test_keywords = ['test', 'ci', 'build', 'failed', 'error', 'broken', 'failing']
    for keyword in test_keywords:
        if keyword in pr_body or keyword in pr_title:
            reasons.append("فشل في الاختبارات أو CI")
            break
    
    conflict_keywords = ['conflict', 'merge conflict', 'cannot merge', 'out of date']
    for keyword in conflict_keywords:
        if keyword in pr_body or keyword in pr_title:
            reasons.append("تعارض في الكود مع التعديلات الحالية")
            break
    
    style_keywords = ['style', 'format', 'lint', 'pep8', 'quality', 'maintainability']
    for keyword in style_keywords:
        if keyword in pr_body or keyword in pr_title:
            reasons.append("مشاكل في أسلوب الكود أو الجودة")
            break
    
    if pr_data.get('additions', 0) > 500 or pr_data.get('deletions', 0) > 500:
        reasons.append("تغيير كبير جداً (أكثر من 500 سطر)")
    
    try:
        url = f"https://api.github.com/repos/{repo_name}/pulls?state=open"
        headers = {"Accept": "application/vnd.github.v3+json"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            open_prs = response.json()
            if len(open_prs) > 10:
                reasons.append("أولوية منخفضة (الكثير من PRs مفتوحة)")
    except:
        pass
    
    if not reasons:
        reasons.append("سبب غير معروف")
    
    return reasons

# ===================== مسارات Flask =====================

@app.route('/')
def home():
    return "The Rejection Whisperer is alive."

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
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
        reasons = analyze_rejection_reason(pr_data, repo_name)
        
        print("=" * 60)
        print(f"PR #{pr_number}: {pr_title}")
        print(f"Author: {username}")
        print(f"Action: {action}")
        print(f"Classification: {classification}")
        print(f"Reasons: {', '.join(reasons)}")
        print(f"URL: {pr_url}")
        print("=" * 60)
        
        if classification in ['Silent AI Rejection', 'AI Rejection with Comments', 
                              'Silent Human Rejection', 'Human Rejection with Comments']:
            save_rejection(pr_number, repo_name, pr_title, username, classification, action, pr_url, reasons)
        
        return jsonify({"status": "received"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stats', methods=['GET'])
def stats():
    try:
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
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ===================== Dashboard =====================

@app.route('/dashboard')
def dashboard():
    try:
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
        
        # نحاول نجيب reasons، إذا ما كان العمود موجود نتعامل معه
        try:
            cursor.execute('''
                SELECT pr_title, author, classification, reasons, timestamp 
                FROM rejections 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''')
            recent = cursor.fetchall()
        except:
            cursor.execute('''
                SELECT pr_title, author, classification, timestamp 
                FROM rejections 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''')
            recent_data = cursor.fetchall()
            recent = [(title, author, classification, 'No reason data', timestamp) for title, author, classification, timestamp in recent_data]
        
        # إحصائيات الأسباب
        try:
            conn2 = sqlite3.connect('rejections.db')
            cursor2 = conn2.cursor()
            cursor2.execute('''
                SELECT reasons, COUNT(*) 
                FROM rejections 
                GROUP BY reasons
                ORDER BY COUNT(*) DESC
                LIMIT 5
            ''')
            reason_stats = cursor2.fetchall()
            conn2.close()
        except:
            reason_stats = []
        
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
                h2 {{ color: #2c3e50; margin-top: 30px; }}
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
                .badge-ai-silent {{ background: #e74c3c; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
                .badge-ai-comment {{ background: #e67e22; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
                .badge-human-silent {{ background: #3498db; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
                .badge-human-comment {{ background: #2ecc71; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
                .badge-merged {{ background: #9b59b6; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
                .badge-open {{ background: #95a5a6; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
                .reason-list {{ font-size: 13px; color: #555; max-width: 300px; }}
                .reason-tag {{
                    background: #ecf0f1;
                    padding: 6px 12px;
                    border-radius: 15px;
                    font-size: 13px;
                    margin: 3px;
                    display: inline-block;
                }}
                .reason-tag .count {{ font-weight: bold; color: #3498db; }}
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
            
            <h2>Top Reasons for Rejection</h2>
            <div style="margin-bottom: 20px;">
        '''
        
        if reason_stats:
            for reason, count in reason_stats:
                html += f'''
                    <span class="reason-tag">{reason}: <span class="count">{count}</span></span>
                '''
        else:
            html += '<span class="reason-tag">No data yet</span>'
        
        html += '''
            </div>
            
            <h2>Recent Rejections</h2>
            <table>
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Author</th>
                        <th>Classification</th>
                        <th>Reasons</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        if recent:
            for title, author, classification, reasons, timestamp in recent:
                badge_class = classification.replace(' ', '-').lower()
                reasons_display = reasons if reasons else 'No reason'
                html += f'''
                    <tr>
                        <td>{title}</td>
                        <td>{author}</td>
                        <td><span class="badge-{badge_class}">{classification}</span></td>
                        <td class="reason-list">{reasons_display}</td>
                        <td>{timestamp}</td>
                    </tr>
                '''
        else:
            html += '''
                <tr>
                    <td colspan="5" style="text-align: center; color: #95a5a6;">No rejections recorded yet.</td>
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
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
