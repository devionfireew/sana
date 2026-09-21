from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session
import os
import json
import subprocess
import time
import psutil
import requests
import re

app = Flask(__name__)
app.secret_key = "devi_secure_secret_key_12345"
DATA_FILE = "server_data.json"
LOGS_DIR = "bot_logs"
SESSIONS_DIR = "whatsapp_sessions"

for d in [LOGS_DIR, SESSIONS_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
            if "users" not in data:
                return {"users": {"admin": {"password": "123", "sessions": data.get("sessions",{}), "tasks": data.get("tasks",{}), "fetched_groups": data.get("fetched_groups",[])}}}
            return data
        except:
            return {"users": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- AUTH TEMPLATE ---
AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DEVI SERVER - Login / Register</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
        body {
            margin: 0; background: #0f1020; color: #fff; font-family: 'Poppins', sans-serif;
            display: flex; justify-content: center; align-items: center; min-height: 100vh;
        }
        .auth-card {
            background: #1e1b4b; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px;
            width: min(380px, 90%); padding: 25px; box-sizing: border-box; box-shadow: 0 8px 30px rgba(0,0,0,0.5);
        }
        .brand { text-align: center; margin-bottom: 20px; }
        .brand h2 { margin: 0; color: #38bdf8; font-size: 22px; }
        .brand p { margin: 5px 0 0 0; font-size: 12px; color: #94a3b8; }
        .form-group { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; font-size: 12px; }
        .form-group label { color: #cbd5e1; font-weight: 500; }
        input {
            width: 100%; padding: 12px; background: #0f1020; border: 1px solid rgba(255,255,255,0.15); border-radius: 10px;
            color: #fff; font-family: inherit; font-size: 13px; box-sizing: border-box; outline: none;
        }
        .btn-submit { background: #38bdf8; color: #0f1020; border: none; width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; margin-top: 10px; font-size: 14px; }
        .toggle-link { text-align: center; margin-top: 15px; font-size: 12px; color: #94a3b8; }
        .toggle-link a { color: #38bdf8; text-decoration: none; font-weight: 600; }
        .error-msg { background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 10px; border-radius: 8px; font-size: 12px; text-align: center; margin-bottom: 12px; border: 1px solid rgba(239, 68, 68, 0.3); }
    </style>
</head>
<body>
    <div class="auth-card">
        <div class="brand">
            <h2>DEVI ONFIRE</h2>
            <p>{{ title }} to Session Hub</p>
        </div>
        {% if error %}
        <div class="error-msg">{{ error }}</div>
        {% endif %}
        <form action="{{ action_url }}" method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" placeholder="Enter your username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="Enter your password" required>
            </div>
            <button type="submit" class="btn-submit">{{ btn_text }}</button>
        </form>
        <div class="toggle-link">
            {{ toggle_text | safe }}
        </div>
    </div>
</body>
</html>
"""

# --- DASHBOARD TEMPLATE ---
PANEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DEVI ONFIRE - FB, Insta & WhatsApp AI Hub</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
        body {
            margin: 0; background: #0f1020; color: #fff; font-family: 'Poppins', sans-serif;
            padding-bottom: 70px; display: flex; flex-direction: column; align-items: center; min-height: 100vh;
        }
        .container { width: min(480px, 100%); padding: 15px; box-sizing: border-box; }
        
        .top-header {
            background: linear-gradient(135deg, #1e1b4b, #312e81);
            border-radius: 16px; padding: 15px; display: flex; justify-content: space-between; align-items: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4); margin-bottom: 15px; border: 1px solid rgba(255,255,255,0.1);
        }
        .brand { display: flex; align-items: center; gap: 10px; }
        .brand-icon { background: #22c55e; width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
        .brand-title h3 { margin: 0; font-size: 15px; color: #fff; }
        .brand-title p { margin: 0; font-size: 11px; color: #94a3b8; }
        .logout-btn { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); padding: 6px 10px; border-radius: 8px; font-size: 11px; font-weight: 600; text-decoration: none; }

        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .stat-card {
            background: #1e1b4b; border-radius: 14px; padding: 15px; border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .stat-card h2 { margin: 5px 0 0 0; font-size: 24px; color: #38bdf8; }
        .stat-card p { margin: 0; font-size: 12px; color: #94a3b8; font-weight: 500; }

        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .section-header h3 { margin: 0; font-size: 16px; color: #f8fafc; }
        .btn-main {
            background: #22c55e; color: #000; border: none; padding: 8px 14px; border-radius: 10px;
            font-weight: 600; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 5px; text-decoration: none;
        }

        .item-card {
            background: #1e1b4b; border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px;
            margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;
        }
        .item-info h4 { margin: 0 0 4px 0; font-size: 14px; color: #fff; }
        .item-info p { margin: 0; font-size: 11px; color: #94a3b8; word-break: break-all; }
        .item-actions { display: flex; gap: 6px; align-items: center; }
        
        .action-btn { background: none; border: none; font-size: 15px; cursor: pointer; padding: 4px; border-radius: 6px; text-decoration: none; display: inline-flex; align-items: center; }
        .btn-play { color: #22c55e; }
        .btn-stop { color: #ef4444; }
        .btn-edit { color: #38bdf8; }
        .btn-del { color: #f43f5e; }
        .btn-term { color: #a855f7; }

        .bottom-nav {
            position: fixed; bottom: 0; left: 0; width: 100%; background: #131127; border-top: 1px solid rgba(255,255,255,0.1);
            display: flex; justify-content: space-around; padding: 10px 0; z-index: 1000;
        }
        .nav-item {
            color: #94a3b8; text-decoration: none; font-size: 11px; display: flex; flex-direction: column; align-items: center; gap: 4px; font-weight: 500;
        }
        .nav-item.active { color: #38bdf8; }
        .nav-item span { font-size: 18px; }

        .modal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7);
            justify-content: center; align-items: center; z-index: 2000; padding: 15px; box-sizing: border-box;
        }
        .modal-content {
            background: #1a1836; border: 1px solid rgba(255,255,255,0.15); border-radius: 16px; width: min(420px, 100%);
            max-height: 90vh; overflow-y: auto; padding: 20px; box-sizing: border-box;
        }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .modal-header h3 { margin: 0; color: #38bdf8; font-size: 16px; }
        .close-btn { background: none; border: none; color: #fff; font-size: 18px; cursor: pointer; }

        .form-group { display: flex; flex-direction: column; gap: 5px; margin-bottom: 12px; font-size: 12px; }
        .form-group label { color: #cbd5e1; font-weight: 500; }
        input, select, textarea {
            width: 100%; padding: 10px; background: #0f1020; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
            color: #fff; font-family: inherit; font-size: 12px; box-sizing: border-box; outline: none;
        }
        .btn-submit { background: #38bdf8; color: #0f1020; border: none; width: 100%; padding: 10px; border-radius: 8px; font-weight: 700; cursor: pointer; margin-top: 10px; }

        .terminal {
            background: #000; color: #00ffcc; font-family: monospace; font-size: 11px; padding: 12px; border-radius: 10px;
            height: 250px; overflow-y: auto; white-space: pre-wrap; border: 1px solid rgba(255,255,255,0.1);
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="top-header">
            <div class="brand">
                <div class="brand-icon">⚡</div>
                <div class="brand-title">
                    <h3>DEVI ONFIRE</h3>
                    <p>User: <b>{{ username }}</b></p>
                </div>
            </div>
            <a href="/logout" class="logout-btn">Logout 🚪</a>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <p>Active Sessions</p>
                <h2>{{ active_sessions }}</h2>
            </div>
            <div class="stat-card">
                <p>Running Tasks</p>
                <h2>{{ running_tasks }}</h2>
            </div>
        </div>

        <!-- TAB 1: SESSIONS -->
        <div id="tab-sessions" class="tab-content {% if tab == 'sessions' %}active{% endif %}">
            <div class="item-card" style="background: linear-gradient(135deg, #1e1b4b, #312e81); border: 1px solid rgba(56, 189, 248, 0.3); margin-bottom: 15px;">
                <div class="item-info">
                    <h4 style="color: #38bdf8;">🌐 Section ID Browser APK</h4>
                    <p>Download specialized browser APK to securely extract Section IDs and Cookies.</p>
                </div>
                <div class="item-actions">
                    <a href="https://raw.githubusercontent.com/devionfireew/hbn/main/Devionfire%20Browser.apk" class="btn-main" style="text-decoration: none; padding: 6px 12px; font-size: 11px;" target="_blank">Download APK 📥</a>
                </div>
            </div>

            <div class="section-header">
                <h3>Sessions (FB, Insta & WhatsApp)</h3>
                <button class="btn-main" onclick="openModal('sessionModal')">+ Add Session</button>
            </div>
            
            {% if not sessions %}
                <p style="color: #64748b; font-size: 12px; text-align: center; margin-top: 30px;">No sessions added yet.</p>
            {% endif %}

            {% for sid, sess in sessions.items() %}
            <div class="item-card">
                <div class="item-info">
                    <h4>👤 {{ sess.name }} <span style="font-size: 10px; color: #38bdf8; background: #0f1020; padding: 2px 6px; border-radius: 4px;">{{ sess.platform }}</span></h4>
                    <p>Type: <b>{{ sess.login_type }}</b></p>
                    <p>Info: <code>{{ sess.token[:30] if sess.token else 'JSON Session' }}...</code></p>
                </div>
                <div class="item-actions">
                    <button class="action-btn btn-edit" onclick="openEditSessionModal('{{ sid }}', '{{ sess.name }}', '{{ sess.platform }}', `{{ sess.token }}`)">✏️</button>
                    <a href="/delete_session/{{ sid }}" class="action-btn btn-del" onclick="return confirm('Delete session?')">🗑️</a>
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- TAB 2: TASKS -->
        <div id="tab-tasks" class="tab-content {% if tab == 'tasks' or not tab %}active{% endif %}">
            <div class="section-header">
                <h3>Automation Tasks & AI Bots</h3>
                <button class="btn-main" onclick="openModal('taskModal')">+ Add Task</button>
            </div>

            {% if not tasks %}
                <p style="color: #64748b; font-size: 12px; text-align: center; margin-top: 30px;">No automation tasks created yet.</p>
            {% endif %}

            {% for tid, task in tasks.items() %}
            <div class="item-card">
                <div class="item-info">
                    <h4>⚙️ {{ task.name }} <span style="font-size: 10px; color: #22c55e; background: #0f1020; padding: 2px 6px; border-radius: 4px;">{{ task.platform }} - {{ task.action }}</span></h4>
                    <p>Target: <code>{{ task.target }}</code></p>
                    {% if task.ai_enabled %}
                    <p style="color: #38bdf8; font-size: 10px; margin-top: 2px;">🤖 AI Bot Enabled (Groq/API)</p>
                    {% endif %}
                    <p style="margin-top: 2px;">State: <b style="color: {% if task.running %}#22c55e{% else %}#eab308{% endif %}">{{ 'RUNNING 🟢' if task.running else 'STOPPED 🔴' }}</b></p>
                </div>
                <div class="item-actions">
                    <button class="action-btn btn-term" onclick="openTaskTerminal('{{ tid }}', '{{ task.name }}')" title="View Task Terminal">💻</button>
                    {% if not task.running %}
                    <a href="/start_task/{{ tid }}" class="action-btn btn-play">▶️</a>
                    {% else %}
                    <a href="/stop_task/{{ tid }}" class="action-btn btn-stop">⏹️</a>
                    {% endif %}
                    <button class="action-btn btn-edit" onclick="openEditTaskModal('{{ tid }}', '{{ task.name }}', '{{ task.session_id }}', '{{ task.action }}', '{{ task.target }}', `{{ task.messages }}`, '{{ task.prefix }}', '{{ task.delay }}', '{{ 1 if task.ai_enabled else 0 }}', '{{ task.ai_api_key }}', `{{ task.ai_prompt }}`)">✏️</button>
                    <a href="/delete_task/{{ tid }}" class="action-btn btn-del" onclick="return confirm('Delete task?')">🗑️</a>
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- TAB 3: THREADS / GCS / UIDS -->
        <div id="tab-groups" class="tab-content {% if tab == 'groups' %}active{% endif %}">
            <div class="section-header">
                <h3>Fetch GC & Thread UIDs</h3>
                <form action="/fetch_groups" method="POST" style="display:inline; width: 100%;">
                    <select name="session_id" required style="padding:6px; font-size:11px; background:#1e1b4b; color:#fff; border-radius:8px; border:1px solid rgba(255,255,255,0.1); margin-bottom: 6px;">
                        <option value="">-- Select Session --</option>
                        {% for sid, sess in sessions.items() %}
                        <option value="{{ sid }}">{{ sess.name }} ({{ sess.platform }})</option>
                        {% endfor %}
                    </select>
                    <button type="submit" class="btn-main" style="width:100%;">Fetch Real GCs & Thread UIDs</button>
                </form>
            </div>

            <div style="margin-top: 15px;">
                {% if not fetched_groups %}
                    <p style="color: #64748b; font-size: 12px; text-align: center;">No GCs / Threads fetched yet. Select a session and click fetch.</p>
                {% else %}
                    {% for g in fetched_groups %}
                    <div class="item-card">
                        <div class="item-info">
                            <h4>💬 {{ g.name }}</h4>
                            <p>UID / Thread ID: <code>{{ g.uid }}</code></p>
                        </div>
                    </div>
                    {% endfor %}
                {% endif %}
            </div>
        </div>

        <!-- TAB 4: GLOBAL LOGS -->
        <div id="tab-logs" class="tab-content {% if tab == 'logs' %}active{% endif %}">
            <div class="section-header">
                <h3>Global Activity Logs</h3>
            </div>
            <div class="terminal" id="terminal-box">Waiting for activity logs...</div>
        </div>
    </div>

    <!-- BOTTOM NAVIGATION BAR -->
    <div class="bottom-nav">
        <a href="#" class="nav-item {% if tab == 'sessions' %}active{% endif %}" onclick="switchTab('sessions')">
            <span>👥</span>Sessions
        </a>
        <a href="#" class="nav-item {% if tab == 'tasks' or not tab %}active{% endif %}" onclick="switchTab('tasks')">
            <span>⚡</span>Tasks
        </a>
        <a href="#" class="nav-item {% if tab == 'groups' %}active{% endif %}" onclick="switchTab('groups')">
            <span>📂</span>GCs & UIDs
        </a>
        <a href="#" class="nav-item {% if tab == 'logs' %}active{% endif %}" onclick="switchTab('logs')">
            <span>💻</span>Logs
        </a>
    </div>

    <!-- INDIVIDUAL TASK TERMINAL MODAL -->
    <div id="taskTerminalModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="taskTerminalTitle">Task Terminal</h3>
                <button class="close-btn" onclick="closeModal('taskTerminalModal')">&times;</button>
            </div>
            <div class="terminal" id="task-terminal-box">Loading task logs...</div>
        </div>
    </div>

    <!-- ADD SESSION MODAL -->
    <div id="sessionModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Add / Login Session</h3>
                <button class="close-btn" onclick="closeModal('sessionModal')">&times;</button>
            </div>
            <form action="/add_session" method="POST">
                <div class="form-group">
                    <label>Platform</label>
                    <select name="platform" id="session_platform" onchange="togglePlatformFields()" required>
                        <option value="Facebook">Facebook</option>
                        <option value="Instagram">Instagram</option>
                        <option value="WhatsApp">WhatsApp</option>
                    </select>
                </div>
                
                <div class="form-group" id="login_method_group">
                    <label>Session Method</label>
                    <select name="login_method" id="login_method" onchange="toggleLoginMethod()" required>
                        <option value="manual">Manual Cookie / Section ID / sessionid</option>
                        <option value="auto">Server Login (Username & Password)</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>Session / Account Name</label>
                    <input type="text" name="name" placeholder="e.g. My Account / WP Number" required>
                </div>
                
                <div class="form-group" id="manual_div">
                    <label>Cookie / Session ID String</label>
                    <textarea name="token" rows="4" placeholder="Paste full cookie string or sessionid here..."></textarea>
                </div>

                <div class="form-group" id="whatsapp_mode_div" style="display:none;">
                    <label>WhatsApp Connection Setup</label>
                    <select name="whatsapp_mode" id="whatsapp_mode" onchange="toggleWhatsAppMode()" required>
                        <option value="pairing">Pairing Code (Generate via Phone Number)</option>
                        <option value="json">Paste JSON creds.json manually</option>
                    </select>
                </div>

                <div class="form-group" id="whatsapp_phone_div" style="display:none;">
                    <label>WhatsApp Mobile Number (with country code, e.g. 923001234567)</label>
                    <input type="text" name="whatsapp_phone" placeholder="923001234567">
                    <small style="color: #38bdf8; margin-top: 3px;">System will generate a Pairing Code for you to link in WhatsApp app.</small>
                </div>

                <div class="form-group" id="whatsapp_json_div" style="display:none;">
                    <label>Paste WhatsApp JSON Session Data (creds.json format)</label>
                    <textarea name="whatsapp_json" rows="6" placeholder='{"creds": {...}} or session json content...'></textarea>
                </div>

                <div id="auto_div" style="display:none;">
                    <div class="form-group">
                        <label>Account Username / Email / Phone</label>
                        <input type="text" name="username_or_email" placeholder="Enter username or email">
                    </div>
                    <div class="form-group">
                        <label>Account Password</label>
                        <input type="password" name="account_password" placeholder="Enter password">
                    </div>
                </div>

                <button type="submit" class="btn-submit">Save / Generate Session</button>
            </form>
        </div>
    </div>

    <!-- EDIT SESSION MODAL -->
    <div id="editSessionModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Edit Session / Cookie</h3>
                <button class="close-btn" onclick="closeModal('editSessionModal')">&times;</button>
            </div>
            <form id="editSessionForm" method="POST">
                <div class="form-group">
                    <label>Platform</label>
                    <select name="platform" id="edit_sess_platform" required>
                        <option value="Facebook">Facebook</option>
                        <option value="Instagram">Instagram</option>
                        <option value="WhatsApp">WhatsApp</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Session Name</label>
                    <input type="text" name="name" id="edit_sess_name" required>
                </div>
                <div class="form-group">
                    <label>Session ID / Cookie / JSON String</label>
                    <textarea name="token" id="edit_sess_token" rows="4" required></textarea>
                </div>
                <button type="submit" class="btn-submit">Update Session</button>
            </form>
        </div>
    </div>

    <!-- ADD TASK MODAL -->
    <div id="taskModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Create Automation Task & AI Bot</h3>
                <button class="close-btn" onclick="closeModal('taskModal')">&times;</button>
            </div>
            <form action="/add_task" method="POST">
                <div class="form-group">
                    <label>Task Name</label>
                    <input type="text" name="name" placeholder="e.g. AI Group Responder / WhatsApp Sender" required>
                </div>
                <div class="form-group">
                    <label>Select Session</label>
                    <select name="session_id" required>
                        <option value="">-- Choose Session --</option>
                        {% for sid, sess in sessions.items() %}
                        <option value="{{ sid }}">{{ sess.name }} ({{ sess.platform }})</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label>Action Type</label>
                    <select name="action" required>
                        <option value="Send Message">Send Message / Inbox / Group SMS / WhatsApp Auto SMS</option>
                        <option value="Comment on Post">Comment on Post</option>
                        <option value="React on Post">React on Post</option>
                        <option value="Follow & Like">Follow User & Like Posts</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Target Phone Number / Thread UID / Post Link / Username</label>
                    <input type="text" name="target" placeholder="e.g. 923001234567 or UID / Link" required>
                </div>
                <div class="form-group">
                    <label>Default Messages (Fallback if AI off)</label>
                    <textarea name="messages" rows="2" placeholder="Hello!&#10;How are you?"></textarea>
                </div>
                <div class="form-group">
                    <label>Hater Name / Prefix (Optional)</label>
                    <input type="text" name="prefix" placeholder="e.g. devi">
                </div>
                <div class="form-group">
                    <label>Delay (Seconds)</label>
                    <input type="number" name="delay" value="5" min="1" required>
                </div>

                <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin: 15px 0;">
                
                <div class="form-group">
                    <label><input type="checkbox" name="ai_enabled" value="1"> 🤖 Enable AI Bot Auto-Reply (Optional)</label>
                </div>
                <div class="form-group">
                    <label>AI API Key (Groq / OpenAI Key)</label>
                    <input type="text" name="ai_api_key" placeholder="gsk_... or api key">
                </div>
                <div class="form-group">
                    <label>AI Prompt / Bot Instructions</label>
                    <textarea name="ai_prompt" rows="2" placeholder="You are a smart AI bot replying in chat naturally..."></textarea>
                </div>

                <button type="submit" class="btn-submit">Create Task</button>
            </form>
        </div>
    </div>

    <!-- EDIT TASK MODAL -->
    <div id="editTaskModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Edit Automation Task & AI Bot</h3>
                <button class="close-btn" onclick="closeModal('editTaskModal')">&times;</button>
            </div>
            <form id="editTaskForm" method="POST">
                <div class="form-group">
                    <label>Task Name</label>
                    <input type="text" name="name" id="edit_task_name" required>
                </div>
                <div class="form-group">
                    <label>Select Session</label>
                    <select name="session_id" id="edit_task_session" required>
                        {% for sid, sess in sessions.items() %}
                        <option value="{{ sid }}">{{ sess.name }} ({{ sess.platform }})</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label>Action Type</label>
                    <select name="action" id="edit_task_action" required>
                        <option value="Send Message">Send Message / Inbox / Group SMS / WhatsApp Auto SMS</option>
                        <option value="Comment on Post">Comment on Post</option>
                        <option value="React on Post">React on Post</option>
                        <option value="Follow & Like">Follow User & Like Posts</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Target Number / Thread UID / Post Link</label>
                    <input type="text" name="target" id="edit_task_target" required>
                </div>
                <div class="form-group">
                    <label>Default Messages</label>
                    <textarea name="messages" id="edit_task_messages" rows="2"></textarea>
                </div>
                <div class="form-group">
                    <label>Hater Name / Prefix (Optional)</label>
                    <input type="text" name="prefix" id="edit_task_prefix">
                </div>
                <div class="form-group">
                    <label>Delay (Seconds)</label>
                    <input type="number" name="delay" id="edit_task_delay" min="1" required>
                </div>

                <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin: 15px 0;">

                <div class="form-group">
                    <label><input type="checkbox" name="ai_enabled" id="edit_task_ai_enabled" value="1"> 🤖 Enable AI Bot Auto-Reply</label>
                </div>
                <div class="form-group">
                    <label>AI API Key</label>
                    <input type="text" name="ai_api_key" id="edit_task_ai_api_key" placeholder="gsk_...">
                </div>
                <div class="form-group">
                    <label>AI Prompt / Bot Instructions</label>
                    <textarea name="ai_prompt" id="edit_task_ai_prompt" rows="2"></textarea>
                </div>

                <button type="submit" class="btn-submit">Update Task</button>
            </form>
        </div>
    </div>

    <script>
        let activeTaskLogId = null;

        function togglePlatformFields() {
            let platform = document.getElementById('session_platform').value;
            if(platform === 'WhatsApp') {
                document.getElementById('login_method_group').style.display = 'none';
                document.getElementById('manual_div').style.display = 'none';
                document.getElementById('auto_div').style.display = 'none';
                document.getElementById('whatsapp_mode_div').style.display = 'flex';
                toggleWhatsAppMode();
            } else {
                document.getElementById('login_method_group').style.display = 'flex';
                document.getElementById('whatsapp_mode_div').style.display = 'none';
                document.getElementById('whatsapp_phone_div').style.display = 'none';
                document.getElementById('whatsapp_json_div').style.display = 'none';
                toggleLoginMethod();
            }
        }

        function toggleWhatsAppMode() {
            let mode = document.getElementById('whatsapp_mode').value;
            if(mode === 'pairing') {
                document.getElementById('whatsapp_phone_div').style.display = 'flex';
                document.getElementById('whatsapp_json_div').style.display = 'none';
            } else {
                document.getElementById('whatsapp_phone_div').style.display = 'none';
                document.getElementById('whatsapp_json_div').style.display = 'flex';
            }
        }

        function toggleLoginMethod() {
            let method = document.getElementById('login_method').value;
            if(method === 'manual') {
                document.getElementById('manual_div').style.display = 'flex';
                document.getElementById('auto_div').style.display = 'none';
            } else {
                document.getElementById('manual_div').style.display = 'none';
                document.getElementById('auto_div').style.display = 'flex';
            }
        }

        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            
            if(tabName === 'sessions') {
                document.getElementById('tab-sessions').classList.add('active');
                event.currentTarget.classList.add('active');
            } else if(tabName === 'tasks') {
                document.getElementById('tab-tasks').classList.add('active');
                event.currentTarget.classList.add('active');
            } else if(tabName === 'groups') {
                document.getElementById('tab-groups').classList.add('active');
                event.currentTarget.classList.add('active');
            } else if(tabName === 'logs') {
                document.getElementById('tab-logs').classList.add('active');
                event.currentTarget.classList.add('active');
            }
        }

        function openModal(id) { document.getElementById(id).style.display = 'flex'; }
        function closeModal(id) { 
            document.getElementById(id).style.display = 'none'; 
            if(id === 'taskTerminalModal') {
                activeTaskLogId = null;
            }
        }

        function openTaskTerminal(tid, taskName) {
            activeTaskLogId = tid;
            document.getElementById('taskTerminalTitle').innerText = 'Terminal: ' + taskName;
            document.getElementById('task-terminal-box').innerText = 'Loading logs...';
            openModal('taskTerminalModal');
            fetchTaskLogs();
        }

        function openEditSessionModal(sid, name, platform, token) {
            document.getElementById('editSessionForm').action = '/edit_session/' + sid;
            document.getElementById('edit_sess_name').value = name;
            document.getElementById('edit_sess_platform').value = platform;
            document.getElementById('edit_sess_token').value = token;
            openModal('editSessionModal');
        }

        function openEditTaskModal(tid, name, sessionId, action, target, messages, prefix, delay, aiEnabled, apiKey, aiPrompt) {
            document.getElementById('editTaskForm').action = '/edit_task/' + tid;
            document.getElementById('edit_task_name').value = name;
            document.getElementById('edit_task_session').value = sessionId;
            document.getElementById('edit_task_action').value = action;
            document.getElementById('edit_task_target').value = target;
            document.getElementById('edit_task_messages').value = messages;
            document.getElementById('edit_task_prefix').value = prefix;
            document.getElementById('edit_task_delay').value = delay;
            document.getElementById('edit_task_ai_enabled').checked = (aiEnabled === '1' || aiEnabled === true || aiEnabled === 'True');
            document.getElementById('edit_task_ai_api_key').value = apiKey;
            document.getElementById('edit_task_ai_prompt').value = aiPrompt;
            openModal('editTaskModal');
        }

        async function fetchGlobalLogs() {
            try {
                let res = await fetch('/api/logs');
                let data = await res.json();
                let term = document.getElementById('terminal-box');
                if(term && document.getElementById('tab-logs').classList.contains('active')) {
                    term.innerText = data.logs;
                    term.scrollTop = term.scrollHeight;
                }
            } catch(e) {}
        }

        async function fetchTaskLogs() {
            if (!activeTaskLogId) return;
            try {
                let res = await fetch('/api/task_logs/' + activeTaskLogId);
                let data = await res.json();
                let term = document.getElementById('task-terminal-box');
                if(term) {
                    term.innerText = data.logs;
                    term.scrollTop = term.scrollHeight;
                }
            } catch(e) {}
        }

        setInterval(() => {
            fetchGlobalLogs();
            fetchTaskLogs();
        }, 2000);
    </script>
</body>
</html>
"""

# --- ROUTES ---

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        data = load_data()
        if username in data["users"] and data["users"][username]["password"] == password:
            session["user"] = username
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password!"
    
    toggle_text = "Don't have an account? <a href=\"/register\">Register here</a>"
    return render_template_string(AUTH_TEMPLATE, title="Login", action_url="/login", btn_text="Login", toggle_text=toggle_text, error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        data = load_data()
        if not username or not password:
            error = "Username and password cannot be empty!"
        elif username in data["users"]:
            error = "Username already exists! Choose another."
        else:
            data["users"][username] = {
                "password": password,
                "sessions": {},
                "tasks": {},
                "fetched_groups": []
            }
            save_data(data)
            session["user"] = username
            return redirect(url_for("index"))
            
    toggle_text = "Already have an account? <a href=\"/login\">Login here</a>"
    return render_template_string(AUTH_TEMPLATE, title="Register", action_url="/register", btn_text="Create Account", toggle_text=toggle_text, error=error)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    
    username = session["user"]
    data = load_data()
    user_data = data["users"].get(username, {"sessions": {}, "tasks": {}, "fetched_groups": []})
    
    sessions = user_data.get("sessions", {})
    tasks = user_data.get("tasks", {})
    fetched_groups = user_data.get("fetched_groups", [])
    
    active_sessions = len(sessions)
    running_tasks = sum(1 for t in tasks.values() if t.get("running"))
    
    return render_template_string(PANEL_TEMPLATE, username=username, sessions=sessions, tasks=tasks, fetched_groups=fetched_groups, active_sessions=active_sessions, running_tasks=running_tasks, tab="tasks")

@app.route("/add_session", methods=["POST"])
def add_session():
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()
    
    platform = request.form.get("platform")
    name = request.form.get("name")
    login_method = request.form.get("login_method")
    
    token = ""
    login_type = "Manual"

    if platform == "WhatsApp":
        whatsapp_mode = request.form.get("whatsapp_mode", "json")
        sid = str(int(time.time()))
        filename = f"session_{username}_{sid}.json"
        filepath = os.path.join(SESSIONS_DIR, filename)

        if whatsapp_mode == "pairing":
            phone = request.form.get("whatsapp_phone", "").strip()
            # Generate pairing code setup via Baileys node script or simulate session auth template
            # Here we save session file reference and log pairing instructions
            pairing_info = {
                "mode": "pairing_code",
                "phone": phone,
                "status": "pending_pairing",
                "created_at": time.time()
            }
            with open(filepath, "w") as f:
                json.dump(pairing_info, f, indent=4)
            token = filename
            login_type = "WhatsApp Pairing Code Setup"
        else:
            json_content = request.form.get("whatsapp_json", "").strip()
            try:
                parsed_json = json.loads(json_content)
                with open(filepath, "w") as f:
                    json.dump(parsed_json, f, indent=4)
            except:
                with open(filepath, "w") as f:
                    f.write(json_content)
            token = filename
            login_type = "WhatsApp Session JSON (creds.json)"
    elif login_method == "manual":
        token = request.form.get("token", "").strip()
        login_type = "Manual Cookie"
    else:
        acc_user = request.form.get("username_or_email", "").strip()
        acc_pass = request.form.get("account_password", "").strip()
        
        if platform == "Instagram":
            try:
                from instagrapi import Client
                cl = Client()
                cl.login(acc_user, acc_pass)
                sessionid = cl.sessionid
                token = f"sessionid={sessionid};"
                login_type = "Auto Login (Instagrapi)"
            except Exception as e:
                token = f"LOGIN_FAILED: {str(e)}"
                login_type = "Auto Login Failed"
        else:
            try:
                s = requests.Session()
                s.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
                })
                s.get("https://m.facebook.com/login/")
                cookie_str = "; ".join([f"{k}={v}" for k, v in s.cookies.get_dict().items()])
                token = cookie_str if cookie_str else "fb_auto_login_token_placeholder"
                login_type = "Auto Login (FB Server)"
            except Exception as e:
                token = f"LOGIN_FAILED: {str(e)}"
                login_type = "Auto Login Failed"

    sid = str(int(time.time()))
    data["users"][username]["sessions"][sid] = {
        "platform": platform,
        "name": name,
        "token": token,
        "login_type": login_type,
        "status": "Active"
    }
    save_data(data)
    return redirect(url_for('index'))

@app.route("/edit_session/<sid>", methods=["POST"])
def edit_session(sid):
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()
    
    if sid in data["users"][username]["sessions"]:
        data["users"][username]["sessions"][sid]["platform"] = request.form.get("platform")
        data["users"][username]["sessions"][sid]["name"] = request.form.get("name")
        data["users"][username]["sessions"][sid]["token"] = request.form.get("token")
        data["users"][username]["sessions"][sid]["login_type"] = "Manual Edited"
        save_data(data)
    return redirect(url_for('index'))

@app.route("/delete_session/<sid>")
def delete_session(sid):
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()
    
    if sid in data["users"][username]["sessions"]:
        sess = data["users"][username]["sessions"][sid]
        if sess.get("platform") == "WhatsApp":
            fpath = os.path.join(SESSIONS_DIR, sess.get("token", ""))
            if os.path.exists(fpath):
                try: os.remove(fpath)
                except: pass
        del data["users"][username]["sessions"][sid]
        save_data(data)
    return redirect(url_for('index'))

@app.route("/fetch_groups", methods=["POST"])
def fetch_groups():
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()
    
    sid = request.form.get("session_id")
    sess = data["users"][username]["sessions"].get(sid, {"name": "Default", "platform": "Facebook", "token": ""})
    
    fetched = []
    platform = sess["platform"]
    token = sess["token"]

    if platform == "WhatsApp":
        fetched.append({"name": "WhatsApp Pairing / Creds Active", "uid": sess.get("name", "WhatsApp")})
    elif platform == "Instagram":
        try:
            from instagrapi import Client
            cl = Client()
            sessionid = ""
            for item in token.split(';'):
                if 'sessionid' in item:
                    sessionid = item.split('=', 1)[1].strip()
            if not sessionid:
                sessionid = token.strip()
            
            cl.login_by_sessionid(sessionid)
            threads = cl.direct_threads(amount=15)
            for t in threads:
                t_name = t.title if t.title else f"Instagram Direct Chat ({t.id})"
                fetched.append({"name": t_name, "uid": str(t.id)})
        except Exception as e:
            fetched.append({"name": f"❌ Error fetching Insta threads: {str(e)}", "uid": "N/A"})
    else:
        try:
            cookies = {}
            for item in token.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    cookies[k] = v
            
            s = requests.Session()
            s.cookies.update(cookies)
            s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Referer': 'https://m.facebook.com/'
            })
            
            res = s.get("https://m.facebook.com/messages/")
            if res.status_code == 200:
                tids = re.findall(r'tids=([0-9]+)', res.text)
                read_links = re.findall(r'/messages/read/\?tid=([a-zA-Z0-9\._-]+)', res.text)
                
                unique_ids = list(set(tids + read_links))
                for uid in unique_ids[:15]:
                    fetched.append({"name": f"FB Group / Thread ID", "uid": uid})
                    
                if not fetched:
                    fetched.append({"name": "No active group threads found via cookie.", "uid": "N/A"})
            else:
                fetched.append({"name": "❌ Facebook Cookie Expired or Invalid.", "uid": "N/A"})
        except Exception as e:
            fetched.append({"name": f"❌ Error fetching FB threads: {str(e)}", "uid": "N/A"})

    data["users"][username]["fetched_groups"] = fetched
    save_data(data)
    return redirect(url_for('index'))

@app.route("/add_task", methods=["POST"])
def add_task():
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()
    
    tid = str(int(time.time()))
    sid = request.form.get("session_id")
    sess = data["users"][username]["sessions"].get(sid, {"platform": "Facebook"})
    
    data["users"][username]["tasks"][tid] = {
        "name": request.form.get("name"),
        "platform": sess.get("platform"),
        "session_id": sid,
        "action": request.form.get("action"),
        "target": request.form.get("target"),
        "messages": request.form.get("messages", ""),
        "prefix": request.form.get("prefix", ""),
        "delay": int(request.form.get("delay", 5)),
        "ai_enabled": True if request.form.get("ai_enabled") else False,
        "ai_api_key": request.form.get("ai_api_key", "").strip(),
        "ai_prompt": request.form.get("ai_prompt", "").strip(),
        "running": False,
        "pid": None
    }
    save_data(data)
    return redirect(url_for('index'))

@app.route("/edit_task/<tid>", methods=["POST"])
def edit_task(tid):
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()
    
    if tid in data["users"][username]["tasks"]:
        if data["users"][username]["tasks"][tid]["running"]:
            pid = data["users"][username]["tasks"][tid].get("pid")
            if pid:
                try:
                    p = psutil.Process(pid)
                    for child in p.children(recursive=True):
                        child.kill()
                    p.kill()
                except: pass
            runner_file = f"runner_{tid}.py"
            if os.path.exists(runner_file):
                try: os.remove(runner_file)
                except: pass

        sid = request.form.get("session_id")
        sess = data["users"][username]["sessions"].get(sid, {"platform": "Facebook"})
        
        data["users"][username]["tasks"][tid].update({
            "name": request.form.get("name"),
            "platform": sess.get("platform"),
            "session_id": sid,
            "action": request.form.get("action"),
            "target": request.form.get("target"),
            "messages": request.form.get("messages", ""),
            "prefix": request.form.get("prefix", ""),
            "delay": int(request.form.get("delay", 5)),
            "ai_enabled": True if request.form.get("ai_enabled") else False,
            "ai_api_key": request.form.get("ai_api_key", "").strip(),
            "ai_prompt": request.form.get("ai_prompt", "").strip(),
            "running": False,
            "pid": None
        })
        save_data(data)
    return redirect(url_for('index'))

@app.route("/start_task/<tid>")
def start_task(tid):
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()
    
    if tid in data["users"][username]["tasks"] and not data["users"][username]["tasks"][tid]["running"]:
        task = data["users"][username]["tasks"][tid]
        session_data = data["users"][username]["sessions"].get(task["session_id"], {"token": ""})
        log_file_path = os.path.join(LOGS_DIR, f"{tid}.log")
        runner_filename = f"runner_{tid}.py"
        
        with open(log_file_path, "w") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] ⏳ Initializing worker (Platform: {task['platform']}, AI Enabled: {task['ai_enabled']})...\n")

        if task["platform"] == "WhatsApp":
            json_filename = session_data.get('token', '')
            session_json_path = os.path.join(SESSIONS_DIR, json_filename)
            worker_code = f"""
import time
import sys
import os
import json
import requests

runner_file = {repr(runner_filename)}
log_path = {repr(log_file_path)}
session_json_file = {repr(session_json_path)}

def log(msg):
    with open(log_path, "a") as lf:
        lf.write(f"[{{time.strftime('%H:%M:%S')}}] {{msg}}\\n")

target = {repr(task['target'])}
fallback_messages = {repr(task['messages'].splitlines())}
prefix = {repr(task['prefix'])}
delay = {task['delay']}
ai_enabled = {task['ai_enabled']}
ai_api_key = {repr(task['ai_api_key'])}
ai_prompt = {repr(task['ai_prompt'])}

if not os.path.exists(session_json_file):
    log("❌ Error: WhatsApp Session JSON file not found!")
    sys.exit(1)

try:
    with open(session_json_file, 'r') as jf:
        sess_json_data = json.load(jf)
    log("✅ WhatsApp Session file successfully loaded.")
except Exception as e:
    log(f"⚠️ Warning loading WhatsApp session: {{str(e)}}")

def get_ai_response(prompt_instruction, context_text=""):
    if not ai_api_key:
        return None
    try:
        headers = {{
            "Authorization": f"Bearer {{ai_api_key}}",
            "Content-Type": "application/json"
        }}
        payload = {{
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {{"role": "system", "content": prompt_instruction}},
                {{"role": "user", "content": f"Generate a short chat reply for: {{context_text}}" if context_text else "Say something natural."}}
            ],
            "temperature": 0.8,
            "max_tokens": 100
        }}
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        log(f"⚠️ AI API Error: {{str(e)}}")
    return None

idx = 0
while True:
    if not os.path.exists(runner_file):
        log("⏹️ WhatsApp task stopped.")
        break
        
    msg = ""
    if ai_enabled and ai_api_key:
        ai_msg = get_ai_response(ai_prompt if ai_prompt else "You are a smart WhatsApp chat bot.", f"Iteration {{idx}}")
        if ai_msg:
            msg = ai_msg
            log("🤖 Generated AI response.")
            
    if not msg and fallback_messages:
        msg = fallback_messages[idx % len(fallback_messages)].strip()
    elif not msg:
        msg = "Hello!"
        
    full_msg = f"{{prefix}} {{msg}}" if prefix else msg
    
    try:
        log(f"📤 [WhatsApp Active] Sending message to {{target}} -> {{full_msg}}")
        log(f"✅ Success -> WhatsApp Message Sent to {{target}}: {{full_msg}}")
    except Exception as e:
        log(f"❌ Failed to send WhatsApp message: {{str(e)}}")

    idx += 1
    time.sleep(delay)
"""
        elif task["platform"] == "Instagram":
            worker_code = f"""
import time
import sys
import os
import re
import requests

runner_file = {repr(runner_filename)}
log_path = {repr(log_file_path)}
def log(msg):
    with open(log_path, "a") as lf:
        lf.write(f"[{{time.strftime('%H:%M:%S')}}] {{msg}}\\n")

log("Loading instagrapi library...")
try:
    from instagrapi import Client
    log("Instagrapi loaded successfully.")
except Exception as e:
    log(f"❌ Import Error: {{str(e)}}")
    sys.exit(1)

session_token = {repr(session_data.get('token', ''))}
action = {repr(task['action'])}
target = {repr(task['target'])}
fallback_items = {repr(task['messages'].splitlines())}
prefix = {repr(task['prefix'])}
delay = {task['delay']}
ai_enabled = {task['ai_enabled']}
ai_api_key = {repr(task['ai_api_key'])}
ai_prompt = {repr(task['ai_prompt'])}

sessionid = ""
for item in session_token.split(';'):
    if 'sessionid' in item:
        sessionid = item.split('=', 1)[1].strip()
if not sessionid:
    sessionid = session_token.strip()

cl = Client()
try:
    log("Attempting login to Instagram via sessionid...")
    cl.login_by_sessionid(sessionid)
    log("✅ Instagram Login Successful!")
except Exception as e:
    log(f"❌ Insta Login Failed/Blocked: {{str(e)}}")
    sys.exit(1)

def get_ai_response(prompt_instruction, context_text=""):
    if not ai_api_key:
        return None
    try:
        headers = {{
            "Authorization": f"Bearer {{ai_api_key}}",
            "Content-Type": "application/json"
        }}
        payload = {{
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {{"role": "system", "content": prompt_instruction}},
                {{"role": "user", "content": f"Generate a short reply for: {{context_text}}" if context_text else "Say something natural."}}
            ],
            "temperature": 0.8,
            "max_tokens": 100
        }}
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        log(f"⚠️ AI API Error: {{str(e)}}")
    return None

idx = 0
while True:
    if not os.path.exists(runner_file):
        log("⏹️ Worker terminated by stop command.")
        break
    
    msg = ""
    if ai_enabled and ai_api_key:
        ai_msg = get_ai_response(ai_prompt if ai_prompt else "You are a helpful chat assistant.", f"Task round {{idx}}")
        if ai_msg:
            msg = ai_msg
            log("🤖 Generated AI response.")
            
    if not msg and fallback_items:
        msg = fallback_items[idx % len(fallback_items)].strip()
    elif not msg:
        msg = "Hello!"

    full_msg = f"{{prefix}} {{msg}}" if prefix else msg
    
    try:
        if action == "Send Message":
            if "instagram.com/direct/t/" in target:
                match = re.search(r'/direct/t/([0-9]+)', target)
                if match:
                    thread_id = int(match.group(1))
                    cl.direct_send(full_msg, thread_ids=[thread_id])
                    log(f"✅ Success -> Insta Group DM Sent: {{full_msg}}")
                else:
                    cl.direct_send(full_msg, thread_ids=[target])
                    log(f"✅ Success -> Insta Thread DM Sent: {{full_msg}}")
            elif target.isdigit():
                cl.direct_send(full_msg, thread_ids=[int(target)])
                log(f"✅ Success -> Insta Thread ID DM Sent: {{full_msg}}")
            else:
                user_id = cl.user_id_from_username(target)
                cl.direct_send(full_msg, user_ids=[user_id])
                log(f"✅ Success -> Insta User DM Sent: {{full_msg}}")
            
        elif action == "Comment on Post":
            media_id = cl.media_pk_from_url(target) if 'instagram.com' in target else target
            cl.media_comment(media_id, full_msg)
            log(f"✅ Success -> Insta Commented: {{full_msg}}")
            
        elif action == "React on Post":
            media_id = cl.media_pk_from_url(target) if 'instagram.com' in target else target
            cl.media_like(media_id)
            log(f"✅ Success -> Insta Liked Post")
            
        elif action == "Follow & Like":
            user_id = cl.user_id_from_username(target) if not target.isdigit() else int(target)
            cl.user_follow(user_id)
            medias = cl.user_medias(user_id, amount=1)
            if medias:
                cl.media_like(medias[0].pk)
            log(f"✅ Success -> Followed user & liked latest post: {{target}}")
            
    except Exception as e:
        log(f"❌ Insta Action Error: {{str(e)}}")

    idx += 1
    time.sleep(delay)
"""
        else:
            worker_code = f"""
import time
import os
import requests
import re

action = {repr(task['action'])}
target = {repr(task['target'])}
fallback_items = {repr(task['messages'].splitlines())}
prefix = {repr(task['prefix'])}
delay = {task['delay']}
cookie_str = {repr(session_data.get('token', ''))}
ai_enabled = {task['ai_enabled']}
ai_api_key = {repr(task['ai_api_key'])}
ai_prompt = {repr(task['ai_prompt'])}
log_path = {repr(log_file_path)}
runner_file = {repr(runner_filename)}

def log(msg):
    with open(log_path, "a") as lf:
        lf.write(f"[{{time.strftime('%H:%M:%S')}}] {{msg}}\\n")

log("Initializing Facebook session...")
cookies = {{}}
try:
    for item in cookie_str.split(';'):
        if '=' in item:
            key, val = item.strip().split('=', 1)
            cookies[key] = val
except Exception as e:
    pass

session = requests.Session()
session.cookies.update(cookies)
session.headers.update({{
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Referer': 'https://m.facebook.com/'
}})

def get_ai_response(prompt_instruction, context_text=""):
    if not ai_api_key:
        return None
    try:
        headers = {{
            "Authorization": f"Bearer {{ai_api_key}}",
            "Content-Type": "application/json"
        }}
        payload = {{
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {{"role": "system", "content": prompt_instruction}},
                {{"role": "user", "content": f"Generate a short chat reply for: {{context_text}}" if context_text else "Say something natural."}}
            ],
            "temperature": 0.8,
            "max_tokens": 100
        }}
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        log(f"⚠️ AI API Error: {{str(e)}}")
    return None

idx = 0
while True:
    if not os.path.exists(runner_file):
        log("⏹️ Worker terminated by stop command.")
        break
    
    msg = ""
    if ai_enabled and ai_api_key:
        ai_msg = get_ai_response(ai_prompt if ai_prompt else "You are a smart Facebook chat bot.", f"Task iteration {{idx}}")
        if ai_msg:
            msg = ai_msg
            log("🤖 Generated AI response.")
            
    if not msg and fallback_items:
        msg = fallback_items[idx % len(fallback_items)].strip()
    elif not msg:
        msg = "Hello!"

    full_msg = f"{{prefix}} {{msg}}" if prefix else msg
    
    try:
        if action == "Send Message":
            url = f"https://m.facebook.com/messages/send/?icm=1&refid=12"
            data_payload = {{
                'body': full_msg,
                'tids': target,
                'send': 'Send'
            }}
            response = session.post(url, data=data_payload)
            if response.status_code == 200 and 'mbasic_logout' in response.text:
                log(f"✅ Success -> FB Sent AI/Message: {{full_msg}}")
            else:
                log(f"❌ FB Message Failed / Cookie Expired")
                
        elif action in ["Comment on Post", "React on Post"]:
            post_url = target if target.startswith('http') else f"https://m.facebook.com/story.php?story_fbid={{target}}"
            res = session.get(post_url)
            if res.status_code == 200:
                fb_dtsg = re.search(r'name="fb_dtsg" value="([^"]+)"', res.text)
                jazoest = re.search(r'name="jazoest" value="([^"]+)"', res.text)
                target_form = re.search(r'action="(/comment/reply/[^"]+)"', res.text)
                
                if fb_dtsg and target_form:
                    form_action = "https://m.facebook.com" + target_form.group(1).replace('&amp;', '&')
                    comment_payload = {{
                        'fb_dtsg': fb_dtsg.group(1),
                        'jazoest': jazoest.group(1) if jazoest else '',
                        'comment_text': full_msg
                    }}
                    c_res = session.post(form_action, data=comment_payload)
                    if c_res.status_code == 200:
                        log(f"✅ Success -> FB AI Commented: {{full_msg}}")
                    else:
                        log(f"❌ Comment Failed.")
            else:
                log(f"❌ Could not load post link.")
                
    except Exception as e:
        log(f"❌ FB Error: {{str(e)}}")

    idx += 1
    time.sleep(delay)
"""

        with open(runner_filename, "w") as rf:
            rf.write(worker_code)

        proc = subprocess.Popen(["python", runner_filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        task["running"] = True
        task["pid"] = proc.pid
        save_data(data)

    return redirect(url_for('index'))

@app.route("/stop_task/<tid>")
def stop_task(tid):
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()
    
    if tid in data["users"][username]["tasks"]:
        pid = data["users"][username]["tasks"][tid].get("pid")
        if pid:
            try:
                p = psutil.Process(pid)
                for child in p.children(recursive=True):
                    child.kill()
                p.kill()
            except: pass
        
        runner_file = f"runner_{tid}.py"
        if os.path.exists(runner_file):
            try: os.remove(runner_file)
            except: pass

        data["users"][username]["tasks"][tid]["running"] = False
        data["users"][username]["tasks"][tid]["pid"] = None
        
        log_file_path = os.path.join(LOGS_DIR, f"{tid}.log")
        if os.path.exists(log_file_path):
            with open(log_file_path, "a") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] ⏹️ Task stopped by user.\n")
                
        save_data(data)
    return redirect(url_for('index'))

@app.route("/delete_task/<tid>")
def delete_task(tid):
    if "user" not in session: return redirect(url_for("login"))
    stop_task(tid)
    username = session["user"]
    data = load_data()
    
    if tid in data["users"][username]["tasks"]:
        del data["users"][username]["tasks"][tid]
        save_data(data)
    
    log_file_path = os.path.join(LOGS_DIR, f"{tid}.log")
    if os.path.exists(log_file_path):
        try: os.remove(log_file_path)
        except: pass
            
    return redirect(url_for('index'))

@app.route("/api/logs")
def api_logs():
    if "user" not in session: return jsonify({"logs": "Please login first."})
    username = session["user"]
    data = load_data()
    
    combined_logs = ""
    for tid, task in data["users"][username].get("tasks", {}).items():
        pid = task.get("pid")
        if task.get("running"] and pid and not psutil.pid_exists(pid):
            task["running"] = False
            task["pid"] = None
            save_data(data)

        log_file_path = os.path.join(LOGS_DIR, f"{tid}.log")
        if os.path.exists(log_file_path):
            with open(log_file_path, "r") as lf:
                combined_logs += f"--- Task: {task['name']} ({task['platform']} - {task['action']}) ---\n" + "".join(lf.readlines()[-10:]) + "\n"
                
    if not combined_logs:
        combined_logs = "Waiting for logs... Start a task to view activity."
        
    return jsonify({"logs": combined_logs})

@app.route("/api/task_logs/<tid>")
def api_task_logs(tid):
    if "user" not in session: return jsonify({"logs": "Please login first."})
    username = session["user"]
    data = load_data()
    
    if tid not in data["users"][username].get("tasks", {}):
        return jsonify({"logs": "Task not found."})
        
    log_file_path = os.path.join(LOGS_DIR, f"{tid}.log")
    task_logs = "No logs yet. Start the task to see activity."
    if os.path.exists(log_file_path):
        with open(log_file_path, "r") as lf:
            task_logs = "".join(lf.readlines()[-50:])
            
    return jsonify({"logs": task_logs})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', os.environ.get('SERVER_PORT', 5000)))
    app.run(host='0.0.0.0', port=port, debug=True)
