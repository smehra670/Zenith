from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, render_template_string, redirect, url_for, session, send_from_directory
from mood import (
    create_spotify_client, get_recommendations, work,
    debug_spotify_setup, well, daily, posture_agent, diet,
    generate_correct_form_image
)
import os, json, pathlib, base64, mimetypes
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = "dev-secret-change-me-123"

USERS_PATH = pathlib.Path("users.json")
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


sp = create_spotify_client()


NEON_CSS = """
<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #e1e1e6;
    min-height: 100vh;
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

h1, h2, h3 {
    background: linear-gradient(45deg, #00f5ff, #ff00aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    margin-bottom: 30px;
    text-shadow: 0 0 20px rgba(0, 245, 255, 0.5);
}

h1 { font-size: 3em; margin-bottom: 10px; }
h2 { font-size: 2.5em; }
h3 { font-size: 1.8em; }

.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 25px;
    margin: 30px 0;
}

.card {
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
    border: 1px solid rgba(0, 245, 255, 0.2);
    border-radius: 15px;
    padding: 25px;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.card::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(0, 245, 255, 0.1), transparent);
    transition: left 0.5s;
}

.card:hover::before {
    left: 100%;
}

.card:hover {
    transform: translateY(-5px);
    border-color: rgba(0, 245, 255, 0.6);
    box-shadow: 0 10px 30px rgba(0, 245, 255, 0.2);
}

.card-icon {
    font-size: 3em;
    text-align: center;
    margin-bottom: 15px;
    filter: drop-shadow(0 0 10px rgba(0, 245, 255, 0.7));
}

.card-title {
    font-size: 1.3em;
    margin-bottom: 15px;
    text-align: center;
    color: #00f5ff;
    text-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
}

.card-description {
    text-align: center;
    color: #b3b3cc;
    margin-bottom: 20px;
}

.btn {
    display: inline-block;
    padding: 12px 25px;
    background: linear-gradient(45deg, #00f5ff, #ff00aa);
    border: none;
    border-radius: 25px;
    color: white;
    text-decoration: none;
    font-weight: 600;
    transition: all 0.3s ease;
    cursor: pointer;
    text-align: center;
    position: relative;
    overflow: hidden;
    margin: 5px;
    min-width: 120px;
}

.btn:hover {
    transform: scale(1.05);
    box-shadow: 0 0 25px rgba(0, 245, 255, 0.6);
    text-decoration: none;
    color: white;
}

.btn-secondary {
    background: linear-gradient(45deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
    border: 1px solid rgba(0, 245, 255, 0.3);
}

.btn-danger {
    background: linear-gradient(45deg, #ff0055, #ff6600);
}

.form-group {
    margin-bottom: 20px;
}

label {
    display: block;
    margin-bottom: 8px;
    color: #00f5ff;
    font-weight: 600;
}

input, select, textarea {
    width: 100%;
    padding: 12px 15px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(0, 245, 255, 0.3);
    border-radius: 8px;
    color: #e1e1e6;
    font-size: 16px;
    transition: all 0.3s ease;
}

input:focus, select:focus, textarea:focus {
    outline: none;
    border-color: #00f5ff;
    box-shadow: 0 0 15px rgba(0, 245, 255, 0.3);
}

.error {
    background: rgba(255, 0, 85, 0.1);
    border: 1px solid rgba(255, 0, 85, 0.3);
    color: #ff0055;
    padding: 15px;
    border-radius: 8px;
    margin: 15px 0;
    text-align: center;
}

.success {
    background: rgba(0, 255, 136, 0.1);
    border: 1px solid rgba(0, 255, 136, 0.3);
    color: #00ff88;
    padding: 15px;
    border-radius: 8px;
    margin: 15px 0;
    text-align: center;
}

.nav-links {
    text-align: center;
    margin-top: 30px;
}

.nav-links a {
    color: #b3b3cc;
    text-decoration: none;
    margin: 0 15px;
    transition: color 0.3s ease;
}

.nav-links a:hover {
    color: #00f5ff;
    text-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
}

.analysis-result {
    background: linear-gradient(145deg, rgba(0, 245, 255, 0.05), rgba(255, 0, 170, 0.05));
    border: 1px solid rgba(0, 245, 255, 0.2);
    border-radius: 15px;
    padding: 25px;
    margin: 20px 0;
    backdrop-filter: blur(10px);
}

.analysis-result h4, .analysis-result h5, .analysis-result h6 {
    background: linear-gradient(45deg, #00f5ff, #ff00aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.image-container {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    margin: 20px 0;
}

.image-box {
    flex: 1;
    min-width: 300px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(0, 245, 255, 0.2);
    border-radius: 15px;
    padding: 20px;
    text-align: center;
}

.image-box img {
    width: 100%;
    max-width: 400px;
    border-radius: 12px;
    border: 2px solid rgba(0, 245, 255, 0.3);
}

.your-form {
    border-color: rgba(255, 0, 85, 0.6) !important;
    box-shadow: 0 0 20px rgba(255, 0, 85, 0.3);
}

.reference-form {
    border-color: rgba(0, 255, 136, 0.6) !important;
    box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
}

.status-badge {
    display: inline-block;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 0.9em;
    font-weight: bold;
    margin-top: 15px;
    backdrop-filter: blur(10px);
}

.needs-work {
    background: rgba(255, 0, 85, 0.2);
    color: #ff0055;
    border: 1px solid rgba(255, 0, 85, 0.4);
}

.perfect-form {
    background: rgba(0, 255, 136, 0.2);
    color: #00ff88;
    border: 1px solid rgba(0, 255, 136, 0.4);
}

.playlist {
    list-style: none;
}

.playlist li {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(0, 245, 255, 0.2);
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
    transition: all 0.3s ease;
}

.playlist li:hover {
    background: rgba(0, 245, 255, 0.1);
    transform: translateX(5px);
}

.score-display {
    text-align: center;
    font-size: 1.5em;
    margin: 20px 0;
    padding: 20px;
    background: linear-gradient(145deg, rgba(0, 245, 255, 0.1), rgba(255, 0, 170, 0.1));
    border-radius: 15px;
    border: 1px solid rgba(0, 245, 255, 0.3);
}

.task-display {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(0, 245, 255, 0.3);
    border-radius: 10px;
    padding: 20px;
    margin: 20px 0;
    text-align: center;
    font-size: 1.2em;
}

pre {
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(0, 245, 255, 0.2);
    border-radius: 8px;
    padding: 20px;
    white-space: pre-wrap;
    overflow-x: auto;
    font-family: 'Courier New', monospace;
    color: #e1e1e6;
}

@media (max-width: 768px) {
    .container { padding: 15px; }
    h1 { font-size: 2.5em; }
    h2 { font-size: 2em; }
    .card-grid { grid-template-columns: 1fr; }
    .image-container { flex-direction: column; }
}

/* Glowing border animation */
@keyframes borderGlow {
    0%, 100% { border-color: rgba(0, 245, 255, 0.2); }
    50% { border-color: rgba(0, 245, 255, 0.6); }
}

.card {
    animation: borderGlow 3s ease-in-out infinite;
}
</style>
"""


def _load_users():
    if not USERS_PATH.exists():
        return {}
    try:
        raw = USERS_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            migrated = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                key = item.get("username") or item.get("email")
                if not key:
                    continue
                migrated[key] = {"password_hash": (item.get("password_hash") or item.get("password") or "")}
            return migrated
        return {}
    except Exception as e:
        print(f"[users] Failed to read/parse users.json: {e}")
        return {}

def _save_users(data):
    try:
        if not isinstance(data, dict):
            data = {}
        USERS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[users] Error saving users.json: {e}")

def current_user():
    return session.get("user")

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def file_to_data_url(path: str) -> str:
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"

def extract_text(resp):
    """
    Try to pull the model's text from various response shapes.
    If it's a dict/list, return pretty JSON.
    Fall back to a regex on the repr, then str(resp).
    """

    text = getattr(resp, "content", None) or getattr(resp, "text", None)
    if text:
        return text

    if isinstance(resp, (dict, list)):
        try:
            return json.dumps(resp, ensure_ascii=False, indent=2)
        except Exception:
            pass
   
    import re
    m = re.findall(r"Message\\(role='assistant', content='([^']*(?:\\\\'[^']*)*)'", str(resp))
    return (m[-1].replace("\\n", "\n").replace("\\'", "'") if m else str(resp))

def format_json_analysis(json_text):
    """Format JSON analysis into readable HTML"""
    try:
        data = json.loads(json_text)
        
        html = f"""
        <div class="analysis-result">
            <h4 style="margin-top:0;">📋 Exercise Analysis</h4>
            <p><strong>Exercise:</strong> {data.get('exercise', 'Unknown')}</p>
            <p><strong>Overall Assessment:</strong> {data.get('overall', 'No assessment provided')}</p>
            <p><strong>Confidence:</strong> {data.get('confidence', 0):.1%}</p>
        """
        
   
        issues = data.get('major_issues', [])
        if issues:
            html += """
            <h5 style="margin-top:20px;">⚠️ Form Issues</h5>
            <ul style="list-style-type:none;padding-left:0;">
            """
            for issue in issues:
                severity_color = {
                    'high': '#ff0055',
                    'medium': '#ff6600', 
                    'low': '#ffaa00'
                }.get(issue.get('severity', 'medium'), '#ff6600')
                
                html += f"""
                <li style="margin-bottom:15px;border-left:4px solid {severity_color};padding-left:15px;background:rgba(255,255,255,0.02);border-radius:0 8px 8px 0;">
                    <strong style="color:{severity_color};">{issue.get('body_part', '').title()}</strong><br>
                    <strong>Problem:</strong> {issue.get('problem', '')}<br>
                    <strong>Severity:</strong> {issue.get('severity', '').title()}<br>
                    <strong>Evidence:</strong> {issue.get('evidence', '')}
                </li>
                """
            html += "</ul>"
        
      
        risks = data.get('risks_if_unchanged', [])
        if risks:
            html += """
            <h5 style="margin-top:20px;">🚨 Potential Injury Risks</h5>
            <ul>
            """
            for risk in risks:
                html += f"<li>{risk}</li>"
            html += "</ul>"
        
     
        corrections = data.get('corrections', [])
        if corrections:
            html += """
            <h5 style="margin-top:20px;">✅ How to Fix</h5>
            """
            for i, correction in enumerate(corrections, 1):
                html += f"""
                <div style="background:rgba(0,245,255,0.05);padding:15px;margin:10px 0;border-radius:8px;border:1px solid rgba(0,245,255,0.2);">
                    <h6 style="margin-top:0;">Fix #{i}: {correction.get('issue_ref', 'General')}</h6>
                    <p><strong>Solution:</strong> {correction.get('fix', '')}</p>
                """
                
                cues = correction.get('cues', [])
                if cues:
                    html += "<p><strong>Coaching Cues:</strong></p><ul>"
                    for cue in cues:
                        html += f"<li>{cue}</li>"
                    html += "</ul>"
                
                drills = correction.get('drills', [])
                if drills:
                    html += "<p><strong>Practice Drills:</strong></p><ul>"
                    for drill in drills:
                        html += f"<li>{drill}</li>"
                    html += "</ul>"
                
                html += "</div>"
        
      
        needs = data.get('needs', [])
        if needs:
            html += """
            <h5 style="margin-top:20px;">📷 For Better Analysis</h5>
            <ul>
            """
            for need in needs:
                html += f"<li>{need}</li>"
            html += "</ul>"
        
        html += "</div>"
        return html
        
    except json.JSONDecodeError:
       
        return f"""
        <div class="analysis-result">
            <h4>📋 Analysis Results</h4>
            <pre>{json_text}</pre>
        </div>
        """
    except Exception as e:
        return f"""
        <div class="analysis-result">
            <h4>📋 Analysis Results</h4>
            <p class="error">Error formatting analysis: {str(e)}</p>
            <pre>{json_text}</pre>
        </div>
        """


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        users = _load_users()

        quick_ok = (username == password) and username in {"admin", "demo", "test"}
        db_ok = username in users and check_password_hash(users[username].get("password_hash", ""), password)

        if quick_ok or db_ok:
            session["user"] = username
            return redirect(url_for("home"))
        error = "Invalid username or password"
        return render_template_string(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Login - Zenith</title>
                {NEON_CSS}
            </head>
            <body>
                <div class="container">
                    <h1>🔐 ZENITH</h1>
                    <div class="card" style="max-width:400px;margin:0 auto;">
                        <h2 style="font-size:1.8em;">Login</h2>
                        <div class="error">{error}</div>
                        <form method="POST">
                            <div class="form-group">
                                <label>Username</label>
                                <input name="username" placeholder="admin / demo / test" required>
                            </div>
                            <div class="form-group">
                                <label>Password</label>
                                <input type="password" name="password" placeholder="same as username" required>
                            </div>
                            <div style="text-align:center;">
                                <button type="submit" class="btn">Sign In</button>
                            </div>
                        </form>
                        <div class="nav-links">
                            <a href="{url_for('signup')}">Sign up</a> • 
                            <a href="{url_for('home')}">Home</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
        """)
    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login - Zenith</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h1>🔐 ZENITH</h1>
                <div class="card" style="max-width:400px;margin:0 auto;">
                    <h2 style="font-size:1.8em;">Login</h2>
                    <form method="POST">
                        <div class="form-group">
                            <label>Username</label>
                            <input name="username" placeholder="admin / demo / test" required>
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" name="password" placeholder="same as username" required>
                        </div>
                        <div style="text-align:center;">
                            <button type="submit" class="btn">Sign In</button>
                        </div>
                    </form>
                    <div class="nav-links">
                        <a href="{url_for('signup')}">Sign up</a> • 
                        <a href="{url_for('home')}">Home</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
    """)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not username or not password:
            error = "Please enter both username and password."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        else:
            users = _load_users()
            if username in users:
                error = "Username already exists. Please choose another."
            else:
                users[username] = {"password_hash": generate_password_hash(password)}
                _save_users(users)
                session["user"] = username
                return redirect(url_for("home"))
        return render_template_string(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Sign Up - Zenith</title>
                {NEON_CSS}
            </head>
            <body>
                <div class="container">
                    <h1>✨ ZENITH</h1>
                    <div class="card" style="max-width:400px;margin:0 auto;">
                        <h2 style="font-size:1.8em;">Sign Up</h2>
                        <div class="error">{error}</div>
                        <form method="POST">
                            <div class="form-group">
                                <label>Username</label>
                                <input name="username" placeholder="Choose username" required>
                            </div>
                            <div class="form-group">
                                <label>Password</label>
                                <input type="password" name="password" placeholder="Min 6 characters" minlength="6" required>
                            </div>
                            <div style="text-align:center;">
                                <button type="submit" class="btn">Create Account</button>
                            </div>
                        </form>
                        <div class="nav-links">
                            <a href="{url_for('login')}">Login</a> • 
                            <a href="{url_for('home')}">Home</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
        """)
    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Sign Up - Zenith</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h1>✨ ZENITH</h1>
                <div class="card" style="max-width:400px;margin:0 auto;">
                    <h2 style="font-size:1.8em;">Sign Up</h2>
                    <form method="POST">
                        <div class="form-group">
                            <label>Username</label>
                            <input name="username" placeholder="Choose username" required>
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" name="password" placeholder="Min 6 characters" minlength="6" required>
                        </div>
                        <div style="text-align:center;">
                            <button type="submit" class="btn">Create Account</button>
                        </div>
                    </form>
                    <div class="nav-links">
                        <a href="{url_for('login')}">Login</a> • 
                        <a href="{url_for('home')}">Home</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
    """)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


@app.route("/")
def home():
    user = current_user()
    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Zenith - AI Wellness Platform</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h1>⚡ ZENITH</h1>
                <p style="text-align:center;font-size:1.2em;margin-bottom:40px;">
                    {'Welcome back, ' + user + '!' if user else 'AI-Powered Wellness Platform'}
                </p>
                
                {'''
                <div class="card-grid">
                    <div class="card">
                        <div class="card-icon">🎵</div>
                        <div class="card-title">Mood Harmonizer</div>
                        <div class="card-description">AI-curated playlists that match your emotional state</div>
                        <div style="text-align:center;">
                            <a href="''' + url_for('music') + '''" class="btn">Launch</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-icon">💪</div>
                        <div class="card-title">Fitness Architect</div>
                        <div class="card-description">Personalized workouts based on your mood and goals</div>
                        <div style="text-align:center;">
                            <a href="''' + url_for('workout_page') + '''" class="btn">Launch</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-icon">🏃</div>
                        <div class="card-title">Posture Coach</div>
                        <div class="card-description">AI form analysis with personalized corrections</div>
                        <div style="text-align:center;">
                            <a href="''' + url_for('posture_coach') + '''" class="btn">Launch</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-icon">🧠</div>
                        <div class="card-title">Well-being Survey</div>
                        <div class="card-description">Mental health assessment with AI-powered insights</div>
                        <div style="text-align:center;">
                            <a href="''' + url_for('wellbeing') + '''" class="btn">Launch</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-icon">✅</div>
                        <div class="card-title">Daily Task</div>
                        <div class="card-description">Quick wellness challenges to build healthy habits</div>
                        <div style="text-align:center;">
                            <a href="''' + url_for('daily_task') + '''" class="btn">Launch</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-icon">🥗</div>
                        <div class="card-title">Diet Planner</div>
                        <div class="card-description">Personalized nutrition plans for your fitness goals</div>
                        <div style="text-align:center;">
                            <a href="''' + url_for('diet_page') + '''" class="btn">Launch</a>
                        </div>
                    </div>
                </div>
                
                <div style="text-align:center;margin-top:40px;">
                    <a href="''' + url_for('logout') + '''" class="btn btn-danger">🚪 Logout</a>
                </div>
                ''' if user else '''
                <div class="card-grid">
                    <div class="card">
                        <div class="card-icon">🔐</div>
                        <div class="card-title">Get Started</div>
                        <div class="card-description">Join Zenith and unlock AI-powered wellness tools</div>
                        <div style="text-align:center;">
                            <a href="''' + url_for('login') + '''" class="btn">Login</a>
                            <a href="''' + url_for('signup') + '''" class="btn btn-secondary">Sign Up</a>
                        </div>
                    </div>
                </div>
                '''}
                
                <div style="text-align:center;margin-top:30px;">
                    <a href="{url_for('debug')}" class="btn btn-secondary">🔧 Diagnostics</a>
                </div>
            </div>
        </body>
        </html>
    """)


@app.route("/music", methods=["GET", "POST"])
@login_required
def music():
    songs, error, selected = [], None, "happy"
    if request.method == "POST":
        selected = request.form.get("mood", "happy")
        if not sp:
            error = "Spotify not configured (.env CLIENT_ID/CLIENT_SECRET)."
        else:
            try:
                songs = get_recommendations(sp, mood=selected, limit=8) or []
                if not songs:
                    error = "No matching tracks. Try another mood."
            except Exception as e:
                error = f"Error fetching songs: {e}"
    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Mood Harmonizer - Zenith</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h2>🎵 Mood Harmonizer</h2>
                <div class="card">
                    <form method="POST">
                        <div class="form-group">
                            <label>Select Your Mood</label>
                            <select name="mood">
                                <option value="motivational" {'selected' if selected=='motivational' else ''}>🔥 Motivational</option>
                                <option value="focus" {'selected' if selected=='focus' else ''}>🎯 Focus</option>
                                <option value="peaceful" {'selected' if selected=='peaceful' else ''}>🧘 Peaceful</option>
                                <option value="happy" {'selected' if selected=='happy' else ''}>😊 Happy</option>
                            </select>
                        </div>
                        <div style="text-align:center;">
                            <button type="submit" class="btn">Generate Playlist</button>
                        </div>
                    </form>
                </div>
                
                {'<div class="error">' + error + '</div>' if error else ''}
                
                {'<div class="card"><h3>🎶 Your Playlist</h3><ul class="playlist">' + ''.join([f'<li><strong>{s["name"]}</strong> — {s["artist"]}<a href="{s["url"]}" target="_blank" class="btn" style="float:right;padding:5px 15px;margin:0;">🎧 Play</a></li>' for s in songs]) + '</ul></div>' if songs else ''}
                
                <div class="nav-links">
                    <a href="{url_for('home')}">← Back to Home</a>
                </div>
            </div>
        </body>
        </html>
    """)

@app.route("/workout", methods=["GET", "POST"])
@login_required
def workout_page():
    plan, error = None, None
    sel_mood, sel_diff, sel_opt, sel_time = "energized", "beginner", "cardio", 30
    if request.method == "POST":
        sel_mood = request.form.get("mood", "energized")
        sel_diff = request.form.get("difficulty", "beginner")
        sel_opt  = request.form.get("option", "cardio")
        sel_time = int(request.form.get("time", 30))
        try:
            prompt = (
                f"Call the workout tool with mood='{sel_mood}', difficulty='{sel_diff}', "
                f"option='{sel_opt}', time={sel_time}. "
                f"Then provide a detailed one-day workout plan with concrete exercises and timing."
            )
            resp = work.run(prompt)
            plan = extract_text(resp)
        except Exception as e:
            error = f"Error generating workout: {e}"
    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Fitness Architect - Zenith</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h2>💪 Fitness Architect</h2>
                <div class="card">
                    <form method="POST">
                        <div class="form-group">
                            <label>Current Mood</label>
                            <select name="mood">
                                <option value="energized" {'selected' if sel_mood=='energized' else ''}>⚡ Energized</option>
                                <option value="stressed" {'selected' if sel_mood=='stressed' else ''}>😰 Stressed</option>
                                <option value="tired" {'selected' if sel_mood=='tired' else ''}>😴 Tired</option>
                                <option value="motivated" {'selected' if sel_mood=='motivated' else ''}>🔥 Motivated</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Fitness Level</label>
                            <select name="difficulty">
                                <option value="beginner" {'selected' if sel_diff=='beginner' else ''}>🌱 Beginner</option>
                                <option value="intermediate" {'selected' if sel_diff=='intermediate' else ''}>🏃 Intermediate</option>
                                <option value="advanced" {'selected' if sel_diff=='advanced' else ''}>💪 Advanced</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Workout Style</label>
                            <select name="option">
                                <option value="cardio" {'selected' if sel_opt=='cardio' else ''}>❤️ Cardio</option>
                                <option value="weight lifting" {'selected' if sel_opt=='weight lifting' else ''}>🏋️ Weight Lifting</option>
                                <option value="calisthenics" {'selected' if sel_opt=='calisthenics' else ''}>🤸 Calisthenics</option>
                                <option value="meditation" {'selected' if sel_opt=='meditation' else ''}>🧘 Meditation</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Duration (minutes)</label>
                            <select name="time">
                                <option value="15" {'selected' if sel_time==15 else ''}>15 min</option>
                                <option value="30" {'selected' if sel_time==30 else ''}>30 min</option>
                                <option value="45" {'selected' if sel_time==45 else ''}>45 min</option>
                                <option value="60" {'selected' if sel_time==60 else ''}>60 min</option>
                            </select>
                        </div>
                        <div style="text-align:center;">
                            <button type="submit" class="btn">Generate Workout</button>
                        </div>
                    </form>
                </div>
                
                {'<div class="error">' + error + '</div>' if error else ''}
                
                {'<div class="card"><h3>🏋️ Your Personalized Workout</h3><pre>' + plan + '</pre></div>' if plan else ''}
                
                <div class="nav-links">
                    <a href="{url_for('home')}">← Back to Home</a>
                </div>
            </div>
        </body>
        </html>
    """)



@app.route("/posture", methods=["GET", "POST"])
@login_required
def posture_coach():
    error, feedback_html, uploaded_filename, reference_image_url = None, None, None, None
    if request.method == "POST":
        action = request.form.get("action", "analyze")
        
        if action == "analyze":
            f = request.files.get("image")
            if not f or not f.filename or not allowed_file(f.filename):
                error = "Please choose a valid image (jpg, png, gif, webp, bmp)."
            else:
                try:
                    fname = "posture_" + secure_filename(f.filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
                    f.save(save_path)
                    uploaded_filename = fname

                    data_url = file_to_data_url(save_path)
                    prompt = (
                        "Analyze the workout form in this photo. Follow a strict JSON-only response. "
                        "Focus on: 1) Major form issues (ordered by severity), 2) Injury risks, "
                        "3) Specific corrections with actionable cues and drills. "
                        "Return valid JSON only. No markdown, no extra text."
                    )

                    
                    user_content = [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]

                   
                    resp = posture_agent.run(user_content)
                    feedback_text = extract_text(resp).strip()
                    
                    
                    feedback_html = format_json_analysis(feedback_text)
                    
                   
                    session["last_analysis"] = feedback_text
                    session["last_uploaded_file"] = uploaded_filename
                    session["last_reference_image"] = None  
                    
                except Exception as e:
                    error = f"Error analyzing image: {e}"
                    print(f"Full error details: {str(e)}")
        
        elif action == "generate_reference":
            
            try:
                last_analysis = session.get("last_analysis")
                if not last_analysis:
                    error = "No previous analysis found. Please analyze an image first."
                else:
                    
                    analysis_data = json.loads(last_analysis)
                    exercise_name = analysis_data.get("exercise", "exercise")
                    
                    
                    reference_image_url = generate_correct_form_image(exercise_name, analysis_data)
                    
                   
                    session["last_reference_image"] = reference_image_url
                    
                    
                    feedback_html = format_json_analysis(last_analysis)
                    uploaded_filename = session.get("last_uploaded_file")
                    
                    if not reference_image_url:
                        error = "Failed to generate reference image. Please try again."
                        
            except json.JSONDecodeError:
                error = "Could not parse analysis data. Please re-analyze your image."
            except Exception as e:
                error = f"Error generating reference image: {e}"
                print(f"Reference image error: {str(e)}")
    
    
    if request.method == "POST" and request.form.get("action") == "generate_reference":
        reference_image_url = session.get("last_reference_image")
        feedback_html = format_json_analysis(session.get("last_analysis", "{}"))
        uploaded_filename = session.get("last_uploaded_file")

    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Posture Coach - Zenith</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h2>🏃 Posture Coach</h2>
                
                <div class="card">
                    <form method="POST" enctype="multipart/form-data">
                        <div class="form-group">
                            <label>Upload Exercise Photo</label>
                            <input type="file" name="image" accept="image/*,.jpg,.jpeg,.png,.gif,.webp,.bmp" required>
                        </div>
                        <div style="text-align:center;">
                            <button type="submit" name="action" value="analyze" class="btn">📸 Analyze Form</button>
                        </div>
                    </form>
                    
                    {'''<form method="POST" style="margin-top:20px;">
                        <div style="text-align:center;">
                            <button type="submit" name="action" value="generate_reference" class="btn btn-secondary">🎯 Generate Perfect Form Reference</button>
                        </div>
                    </form>''' if feedback_html else ''}
                </div>
                
                {'<div class="error">' + error + '</div>' if error else ''}
                
                <div class="image-container">
                  {'''<div class="image-box">
                      <h3>📷 Your Form</h3>
                      <img src="''' + url_for('uploaded_file', filename=uploaded_filename) + '''" class="your-form">
                      <div class="status-badge needs-work">⚠️ Needs Analysis</div>
                    </div>''' if uploaded_filename else ''}
                  
                  {'''<div class="image-box">
                      <h3>🎯 Perfect Form Reference</h3>
                      <img src="''' + reference_image_url + '''" class="reference-form">
                      <div class="status-badge perfect-form">✅ AI-Generated Perfect Form</div>
                    </div>''' if reference_image_url else ''}
                </div>
                
                {feedback_html if feedback_html else ''}
                
                <div class="nav-links">
                    <a href="{url_for('home')}">← Back to Home</a>
                </div>
            </div>
        </body>
        </html>
    """)

@app.route("/wellbeing", methods=["GET", "POST"])
@login_required
def wellbeing():
    advice = None
    if request.method == "POST":
        feel = int(request.form.get("feel", 3))
        down = int(request.form.get("down", 3))
        sleep = int(request.form.get("sleep", 3))
        connected = int(request.form.get("connected", 3))
        stress = int(request.form.get("stress", 3))
        prompt = (
            f"Call the quiz tool with feel={feel}, down={down}, sleep={sleep}, "
            f"connected={connected}, stress={stress}. "
            f"Then provide concise, caring advice (4–6 bullets) for the next 7 days; "
            f"highlight priorities and any red flags (e.g., >=4 on down/anxiety/stress)."
        )
        resp = well.run(prompt)
        advice = extract_text(resp)
    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Well-being Survey - Zenith</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h2>🧠 Well-being Survey</h2>
                <div class="card">
                    <form method="POST">
                        <div class="form-group">
                            <label>Anxiety/Worry Level (1-5)</label>
                            <input type="number" name="feel" min="1" max="5" value="3">
                        </div>
                        <div class="form-group">
                            <label>Depression/Down Feeling (1-5)</label>
                            <input type="number" name="down" min="1" max="5" value="3">
                        </div>
                        <div class="form-group">
                            <label>Sleep Quality (1-5)</label>
                            <input type="number" name="sleep" min="1" max="5" value="3">
                        </div>
                        <div class="form-group">
                            <label>Social Connection (1-5)</label>
                            <input type="number" name="connected" min="1" max="5" value="3">
                        </div>
                        <div class="form-group">
                            <label>Stress Level (1-5)</label>
                            <input type="number" name="stress" min="1" max="5" value="3">
                        </div>
                        <div style="text-align:center;">
                            <button type="submit" class="btn">Get AI Advice</button>
                        </div>
                    </form>
                </div>
                
                {'<div class="card"><h3>💡 Your Personalized Wellness Plan</h3><pre>' + advice + '</pre></div>' if advice else ''}
                
                <div class="nav-links">
                    <a href="{url_for('home')}">← Back to Home</a>
                </div>
            </div>
        </body>
        </html>
    """)


@app.route("/daily", methods=["GET", "POST"])
@login_required
def daily_task():
    if "score" not in session:
        session["score"] = 0
    if "current_task" not in session:
        session["current_task"] = ""
    msg = None

    if request.method == "POST":
        action = request.form.get("action")
        if action == "new":
            prompt = (
                "Give ONE short actionable task (<= 15 words) that can be done at home "
                "in under 5 minutes. Difficulty about the same as 20 push-ups. "
                "Vary types (movement, breathing, stretch, tidy, hydration, sunlight, learning). "
                "Output ONLY the task text. No explanations. No reasoning. "
                "Do NOT include <think> or any hidden thoughts."
            )
            resp = daily.run(prompt)
            import re
            task = extract_text(resp).strip()
            task = re.sub(r"<think>.*?</think>", "", task, flags=re.DOTALL).strip()
            session["current_task"] = task
            msg = "New task generated!"
        elif action == "done":
            if session.get("current_task"):
                session["score"] = int(session["score"]) + 1
                session["current_task"] = ""
                msg = "Great job! +1 point."
            else:
                msg = "No active task."
        elif action == "reset":
            session["score"] = 0
            session["current_task"] = ""
            msg = "Score and task reset."

    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Daily Task - Zenith</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h2>✅ Daily Task</h2>
                
                <div class="score-display">
                    <div style="font-size:2em;">🏆</div>
                    <div>Score: <strong>{session.get('score', 0)}</strong></div>
                </div>
                
                <div class="task-display">
                    <h3>Today's Challenge</h3>
                    <p>{session.get('current_task', 'No active task. Generate a new one!')}</p>
                </div>
                
                {'<div class="success">' + msg + '</div>' if msg else ''}
                
                <div class="card">
                    <form method="POST" style="text-align:center;">
                        <button name="action" value="new" class="btn">🎲 New Task</button>
                        <button name="action" value="done" class="btn btn-secondary">✅ Mark Done (+1)</button>
                        <button name="action" value="reset" class="btn btn-danger">🔄 Reset</button>
                    </form>
                </div>
                
                <div class="nav-links">
                    <a href="{url_for('home')}">← Back to Home</a>
                </div>
            </div>
        </body>
        </html>
    """)


@app.route("/diet", methods=["GET", "POST"])
@login_required
def diet_page():
    plan_html, error = None, None
    goal = "cutting"
    if request.method == "POST":
        goal = request.form.get("goal", "cutting").strip().lower()
        calories = (request.form.get("calories") or "").strip()
        prefs = (request.form.get("prefs") or "").strip()
        try:
            prompt = (
                "You are a personalized AI nutritionist. "
                f"Goal: {goal}. "
                "Generate a 7-day meal plan. Each day must include Breakfast, Lunch, Dinner, and 2 Snacks. "
                "Give exact portion sizes and approximate macros (protein, carbs, fats, calories). "
                "Use simple, affordable foods. Variety across the week. "
                "Safe for teenagers (no extreme cuts, no supplements). "
            )
            if calories:
                prompt += f" Target about {calories} kcal/day. "
            if prefs:
                prompt += f" Respect these preferences/allergies: {prefs}. "
            resp = diet.run(prompt)
            plan_html = extract_text(resp)
        except Exception as e:
            error = f"Error generating plan: {e}"
    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Diet Planner - Zenith</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h2>🥗 Diet Planner</h2>
                <div class="card">
                    <form method="POST">
                        <div class="form-group">
                            <label>Fitness Goal</label>
                            <select name="goal">
                                <option value="cutting" {'selected' if goal=='cutting' else ''}>🔥 Cutting (Fat Loss)</option>
                                <option value="bulking" {'selected' if goal=='bulking' else ''}>💪 Bulking (Muscle Gain)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Target Calories (optional)</label>
                            <input type="number" name="calories" placeholder="e.g., 2200" value="{request.form.get('calories','')}">
                        </div>
                        <div class="form-group">
                            <label>Dietary Preferences/Allergies (optional)</label>
                            <input type="text" name="prefs" placeholder="e.g., vegetarian, no nuts, dairy-free" value="{request.form.get('prefs','')}">
                        </div>
                        <div style="text-align:center;">
                            <button type="submit" class="btn">Generate 7-Day Plan</button>
                        </div>
                    </form>
                </div>
                
                {'<div class="error">' + error + '</div>' if error else ''}
                
                {'<div class="card"><h3>📅 Your 7-Day Meal Plan</h3><pre>' + plan_html + '</pre></div>' if plan_html else ''}
                
                <div class="nav-links">
                    <a href="{url_for('home')}">← Back to Home</a>
                </div>
            </div>
        </body>
        </html>
    """)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/debug")
def debug():
    try:
        debug_spotify_setup()
    except Exception:
        pass
    working = bool(sp)
    return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Diagnostics - Zenith</title>
            {NEON_CSS}
        </head>
        <body>
            <div class="container">
                <h2>🔧 System Diagnostics</h2>
                <div class="card">
                    <h3>Status Overview</h3>
                    <p><strong>Spotify Integration:</strong> 
                        <span style="color: {'#00ff88' if working else '#ff0055'};">
                            {'✅ Connected' if working else '❌ Not Configured'}
                        </span>
                    </p>
                    <p style="color:#b3b3cc;">Check server logs for detailed information</p>
                </div>
                
                <div class="nav-links">
                    <a href="{url_for('home')}">← Back to Home</a>
                </div>
            </div>
        </body>
        </html>
    """)


if __name__ == "__main__":
    print("✨ Zenith Wellness Platform Starting...")
    print("🏠 Home:        http://127.0.0.1:5000")
    print("🔐 Login:       http://127.0.0.1:5000/login")
    print("📝 Signup:      http://127.0.0.1:5000/signup")
    print("🎵 Music:       http://127.0.0.1:5000/music (login required)")
    print("💪 Workout:     http://127.0.0.1:5000/workout (login required)")
    print("🏃 Posture:     http://127.0.0.1:5000/posture (login required)")
    print("🧠 Wellbeing:   http://127.0.0.1:5000/wellbeing (login required)")
    print("✅ Daily Task:  http://127.0.0.1:5000/daily (login required)")
    print("🥗 Diet:        http://127.0.0.1:5000/diet (login required)")
    app.run(debug=True, port=5000)
