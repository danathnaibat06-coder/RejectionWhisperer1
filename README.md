The Rejection Whisperer

The Rejection Whisperer is an intelligent bot designed to monitor and analyze silently rejected Pull Requests in GitHub repositories. The idea emerged from observing that many Pull Requests, especially those submitted by AI agents, are closed without any explicit feedback or reasoning. This bot aims to uncover patterns behind such silent rejections and provide actionable insights for development teams.

---

What Does the Bot Do?

- Detects Pull Requests that are closed without comments (silent rejections)
- Classifies rejections into four categories:
  - Silent AI Rejection
  - AI Rejection with Comments
  - Silent Human Rejection
  - Human Rejection with Comments
- Stores all rejection data in a structured SQLite database
- Provides real-time statistics via a REST API endpoint (/stats) and an interactive Dashboard
- Operates 24/7 as a live web service

---

Tech Stack

Python : Core programming language
Flask : Web framework for handling requests and routing
SQLite : Lightweight embedded database for data persistence
GitHub API : Webhook integration for real-time PR event listening
Render : Cloud hosting for 24/7 deployment

---

How It Works

1. GitHub sends a webhook payload to the bot whenever a Pull Request is closed
2. The bot checks whether the PR was merged or closed without merging
3. It identifies the author as either human or AI agent
4. It determines whether the PR received any comments before being closed
5. Based on these checks, the PR is classified and stored in the database
6. Statistics are made available through /stats and the Dashboard interface

---

 Detected AI Agents

copilot, dependabot, devin, cursor, claude, codex, github-actions, renovate

---

 Local Setup Instructions

1. Clone the repository:
git clone https://github.com/danthanibat06-coder/RejectionWhisperer1.git

2. Install dependencies:
pip install -r requirements.txt

3. Run the bot:
python RejectionWhisperer.py

4. Open in your browser:
http://127.0.0.1:5000

---

 Live Links

Live Bot: https://rejectionwhisperer1.onrender.com
Dashboard: https://rejectionwhisperer1.onrender.com/dashboard
Raw Stats: https://rejectionwhisperer1.onrender.com/stats

---
 Future Roadmap

- Automated weekly reports via Discord or Slack
- Graphical dashboard with data visualizations
- CSV/Excel export functionality for offline analysis
- Enhanced classification logic using NLP on PR descriptions
- Real-time notifications for high-priority rejections

---

 Author

danthanibat06-coder
GitHub: https://github.com/danthanibat06-coder

---

## Support the Project

If you find this project useful, please consider giving it a star on GitHub. Your support helps motivate continuous improvement and open-source contributions.
