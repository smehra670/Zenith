from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import json, pathlib

from flask import Flask, request, render_template_string, redirect, url_for, session, send_from_directory
from mood import (
    create_spotify_client, get_recommendations, work,
    debug_spotify_setup, well, daily, posture_agent, generate_correct_form_image,diet
)
import os
from werkzeug.utils import secure_filename
import base64
import mimetypes
import json
from PIL import Image
import io


app = Flask(__name__)

app.secret_key = "dev-secret-change-me-123"

USERS_PATH = pathlib.Path("users.json")

USERS_PATH = pathlib.Path("users.json")

def _load_users():
    """
    Always return a dict of the shape:
    {
      "alice": {"password_hash": "..."},
      "bob":   {"password_hash": "..."}
    }
    Migrates older list-based formats if found.
    """
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
                migrated[key] = {
                    "password_hash": (
                        item.get("password_hash") or item.get("password") or ""
                    )
                }
            return migrated

        return {}
    except Exception as e:
        print(f"[users] Failed to read/parse users.json: {e}")
        return {}

def _save_users(data):
    """
    Write a dict safely. If a non-dict slips in, coerce to {}.
    """
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


UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


sp = create_spotify_client()


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_image_to_base64(image_path: str) -> str:
    """Convert an image file at image_path to a base64-encoded string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def validate_and_convert_image(image_path):
    """Validate image file and convert to base64 with proper MIME type."""
    try:
        if not os.path.exists(image_path):
            return False, None, None, f"File not found: {image_path}"

        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith('image/'):
            return False, None, None, f"Invalid image type: {mime_type}"

        try:
            with Image.open(image_path) as img:
                if img.mode not in ['RGB', 'RGBA']:
                    img = img.convert('RGB')

                max_size = 2048
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                img_buffer = io.BytesIO()
                format_name = 'JPEG' if mime_type == 'image/jpeg' else (img.format or 'PNG')
                if format_name.upper() == 'JPEG':
                    img.save(img_buffer, format='JPEG', quality=85)
                else:
                    img.save(img_buffer, format=format_name)
                img_buffer.seek(0)

                base64_data = base64.b64encode(img_buffer.read()).decode('utf-8')
                return True, base64_data, mime_type, None

        except Exception as img_error:
            return False, None, None, f"Invalid image file: {str(img_error)}"

    except Exception as e:
        return False, None, None, f"Error processing image: {str(e)}"

def create_anthropic_image_payload(base64_data, mime_type):
    """Create properly formatted image payload for Groq/Anthropic-style vision message."""
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime_type};base64,{base64_data}"
        }
    }

def extract_text(resp):
    """Extract assistant text from an Agent response object."""
    text = getattr(resp, "content", None) or getattr(resp, "text", None)
    if text:
        return text
    import re
    m = re.findall(r"Message\\(role='assistant', content='([^']*(?:\\\\'[^']*)*)'", str(resp))
    return (m[-1].replace("\\n", "\n").replace("\\'", "'") if m else str(resp))



MODERN_CSS = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: #0a0a1a;
        min-height: 100vh; 
        color: #fff; 
        line-height: 1.6;
        position: relative;
        overflow-x: hidden;
    }
    body::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: 
            radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.2) 0%, transparent 50%),
            radial-gradient(circle at 40% 40%, rgba(34, 197, 94, 0.15) 0%, transparent 50%);
        pointer-events: none;
        z-index: -1;
    }
    
    /* Enhanced container with max-width and centering */
    .container { 
        max-width: 1200px; 
        margin: 0 auto; 
        padding: 0 20px; 
        position: relative; 
        z-index: 1; 
    }
    
    /* Modern glass card design */
    .glass-card {
        background: rgba(15, 15, 35, 0.8); 
        backdrop-filter: blur(20px);
        border-radius: 20px; 
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem; 
        margin: 1rem 0; 
        transition: all .4s cubic-bezier(0.23, 1, 0.320, 1);
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .glass-card::before {
        content: '';
        position: absolute;
        top: -2px; left: -2px; right: -2px; bottom: -2px;
        background: linear-gradient(45deg, 
            rgba(120, 119, 198, 0.3), 
            rgba(255, 119, 198, 0.3), 
            rgba(34, 197, 94, 0.3), 
            rgba(120, 119, 198, 0.3));
        border-radius: 22px;
        z-index: -1;
        transition: all .4s ease;
        opacity: 0;
    }
    .glass-card:hover {
        transform: translateY(-8px);
        border-color: rgba(120, 119, 198, 0.4);
        box-shadow: 0 20px 60px rgba(120, 119, 198, 0.2),
                    0 0 0 1px rgba(120, 119, 198, 0.3);
    }
    .glass-card:hover::before {
        opacity: 1;
        animation: neonPulse 2s ease-in-out infinite alternate;
    }
    @keyframes neonPulse {
        0% { 
            background: linear-gradient(45deg, 
                rgba(120, 119, 198, 0.3), 
                rgba(255, 119, 198, 0.3), 
                rgba(34, 197, 94, 0.3), 
                rgba(120, 119, 198, 0.3));
        }
        100% { 
            background: linear-gradient(45deg, 
                rgba(255, 119, 198, 0.3), 
                rgba(34, 197, 94, 0.3), 
                rgba(120, 119, 198, 0.3), 
                rgba(255, 119, 198, 0.3));
        }
    }
    
    /* Top navigation bar */
    .top-nav {
        width: 100%;
        position: fixed; 
        top: 0; 
        z-index: 100;
        background: rgba(10, 10, 26, 0.95);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1rem 0;
    }
    .nav-content {
        display: flex; 
        align-items: center; 
        justify-content: space-between; 
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 2rem;
    }
    .nav-brand {
        display: flex; 
        align-items: center; 
        gap: 1rem; 
        color: #fff; 
        font-weight: 800;
        font-size: 1.3rem;
    }
    .nav-brand span:first-child {
        font-size: 1.8rem;
    }
    .nav-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(34, 197, 94, 0.2);
        border: 1px solid rgba(34, 197, 94, 0.3);
        color: #4ade80;
        padding: 0.5rem 1rem;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .nav-actions {
        display: flex; 
        gap: 1rem;
    }
    
    .nav-btn {
        padding: 0.8rem 1.5rem; 
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        background: rgba(15, 15, 35, 0.6);
        color: #fff;
        text-decoration: none;
        font-weight: 600;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }
    .nav-btn:hover {
        transform: translateY(-2px);
        border-color: rgba(120, 119, 198, 0.5);
        box-shadow: 0 8px 25px rgba(120, 119, 198, 0.2);
        background: rgba(120, 119, 198, 0.1);
    }
    .nav-btn.primary {
        background: linear-gradient(135deg, #7877c6, #ff77c6);
        border-color: rgba(120, 119, 198, 0.5);
    }
    
    /* Hero section with proper spacing for fixed nav */
    .hero { 
        text-align: center; 
        padding: 8rem 0 4rem; 
        color: white; 
        margin-top: 0;
    }
    .hero-badge {
        display: inline-flex; 
        align-items: center; 
        gap: 0.5rem;
        background: rgba(15, 15, 35, 0.6); 
        border: 1px solid rgba(120, 119, 198, 0.4);
        color: #a5a3d9; 
        padding: 0.8rem 1.5rem; 
        border-radius: 50px; 
        font-weight: 700; 
        font-size: 0.9rem;
        backdrop-filter: blur(10px);
        margin-bottom: 2rem;
        box-shadow: 0 0 20px rgba(120, 119, 198, 0.2);
    }
    .hero h1 {
        font-size: clamp(2.5rem, 5vw, 4.5rem); 
        font-weight: 900; 
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, #7877c6 0%, #ff77c6 25%, #06b6d4 50%, #10b981 75%, #7877c6 100%);
        background-size: 300% 300%;
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent;
        animation: gradientShift 6s ease-in-out infinite;
        filter: drop-shadow(0 0 20px rgba(120, 119, 198, 0.3));
    }
    .hero p {
        font-size: 1.2rem;
        color: rgba(255, 255, 255, 0.8);
        margin-bottom: 2rem;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    @keyframes gradientShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    /* 2x3 Feature grid (removed the 3 cards) */
    .feature-grid { 
        display: grid; 
        grid-template-columns: repeat(3, 1fr);
        gap: 2rem; 
        margin: 4rem 0;
        padding: 0 1rem;
    }
    @media (max-width: 1024px) {
        .feature-grid { 
            grid-template-columns: repeat(2, 1fr);
        }
    }
    @media (max-width: 640px) {
        .feature-grid { 
            grid-template-columns: 1fr;
        }
    }
    .feature-link { 
        text-decoration: none; 
        color: #fff; 
        display: block;
    }
    .feature-card {
        background: rgba(15, 15, 35, 0.8); 
        backdrop-filter: blur(20px);
        border-radius: 20px; 
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem; 
        transition: all .4s cubic-bezier(0.23, 1, 0.320, 1);
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .feature-card:hover {
        transform: translateY(-8px);
        border-color: rgba(25, 39, 82, 0.6);
        box-shadow: 0 20px 60px rgba(25, 39, 82, 0.4);
        background: rgba(25, 39, 82, 0.3);
    }
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: block;
    }
    .feature-card h3 {
        font-size: 1.4rem;
        margin-bottom: 0.8rem;
        color: #fff;
        font-weight: 700;
    }
    .feature-card p {
        color: rgba(156, 163, 175, 0.9);
        line-height: 1.6;
        flex-grow: 1;
    }
    
    /* Status badges */
    .status-badge { 
        display: inline-block; 
        padding: 0.6rem 1.2rem; 
        border-radius: 50px; 
        color: #fff; 
        margin-top: 0.8rem;
        font-weight: 700;
        font-size: 0.9rem;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(75, 85, 99, 0.4);
    }
    .status-success{ 
        background: rgba(34, 197, 94, 0.2); 
        border-color: rgba(34, 197, 94, 0.5);
        box-shadow: 0 0 20px rgba(34, 197, 94, 0.2);
    }
    .status-error{ 
        background: rgba(239, 68, 68, 0.2); 
        border-color: rgba(239, 68, 68, 0.5);
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.2);
    }
    
    /* Form styles */
    .form-container{ 
        background: rgba(15, 15, 35, 0.8); 
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1); 
        border-radius: 20px; 
        padding: 2rem; 
        margin: 2rem 0; 
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .form-group{ margin-bottom: 1.5rem; }
    .form-group label{ 
        display: flex; 
        align-items: center; 
        gap: 0.8rem; 
        color: #fff; 
        font-weight: 700; 
        font-size: 1.1rem; 
        margin-bottom: 0.5rem; 
    }
    .form-control{ 
        width: 100%; 
        padding: 1.2rem; 
        border: 1px solid rgba(255, 255, 255, 0.2); 
        border-radius: 12px; 
        background: rgba(15, 15, 35, 0.6); 
        color: #fff; 
        font-size: 1rem; 
        backdrop-filter: blur(10px); 
        transition: all 0.3s ease;
    }
    .form-control::placeholder { color: rgba(156, 163, 175, 0.6); }
    .form-control:focus {
        outline: none;
        border-color: rgba(120, 119, 198, 0.6);
        background: rgba(15, 15, 35, 0.8);
        box-shadow: 0 0 0 3px rgba(120, 119, 198, 0.1);
    }
    
    /* Button styles */
    .btn{ 
        padding: 1.2rem 2rem; 
        border: none; 
        border-radius: 12px; 
        font-weight: 800; 
        cursor: pointer; 
        transition: all 0.3s cubic-bezier(0.23, 1, 0.320, 1); 
        backdrop-filter: blur(10px); 
        position: relative;
        overflow: hidden;
        text-decoration: none;
        display: inline-block;
        text-align: center;
    }
    .btn::before {
        content: '';
        position: absolute;
        top: 0; left: -100%; right: 100%; bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: all 0.5s;
    }
    .btn:hover::before {
        left: 100%; right: -100%;
    }
    .btn:hover { transform: translateY(-3px); }
    .btn-primary{ 
        background: linear-gradient(135deg, #7877c6, #5a59a6); 
        color: #fff; 
        border: 1px solid rgba(120, 119, 198, 0.3);
        box-shadow: 0 4px 20px rgba(120, 119, 198, 0.3);
    }
    .btn-primary:hover {
        box-shadow: 0 8px 30px rgba(120, 119, 198, 0.4);
    }
    .btn-secondary{ 
        background: linear-gradient(135deg, #ff77c6, #d946ef); 
        color: #fff; 
        border: 1px solid rgba(255, 119, 198, 0.3);
        box-shadow: 0 4px 20px rgba(255, 119, 198, 0.3);
    }
    .btn-secondary:hover {
        box-shadow: 0 8px 30px rgba(255, 119, 198, 0.4);
    }
    .btn-upload{ 
        background: linear-gradient(135deg, #06b6d4, #0891b2); 
        color: #fff; 
        border: 1px solid rgba(6, 182, 212, 0.3);
        box-shadow: 0 4px 20px rgba(6, 182, 212, 0.3);
    }
    .btn-upload:hover {
        box-shadow: 0 8px 30px rgba(6, 182, 212, 0.4);
    }
    
    .error-card{ 
        background: rgba(239, 68, 68, 0.1); 
        border: 1px solid rgba(239, 68, 68, 0.3); 
        color: #fca5a5; 
        border-radius: 12px; 
        padding: 1.5rem; 
        backdrop-filter: blur(10px);
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.1);
        margin: 1rem 0;
    }

    /* ENHANCED AUTH STYLES */
    .auth-page {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        background: 
            radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.4) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 40% 40%, rgba(34, 197, 94, 0.2) 0%, transparent 50%),
            #0a0a1a;
    }
    
    .auth-container {
        width: 100%;
        max-width: 1100px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 4rem;
        align-items: center;
        margin: 0 auto;
    }
    
    @media(max-width: 900px) { 
        .auth-container { 
            grid-template-columns: 1fr; 
            gap: 2rem;
        }
        .auth-hero {
            order: 2;
        }
        .auth-form-wrapper {
            order: 1;
        }
    }
    
    .auth-hero {
        text-align: center;
        padding: 2rem;
    }
    
    .auth-hero-icon {
        font-size: 6rem;
        background: linear-gradient(135deg, #7877c6, #ff77c6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
        display: block;
        filter: drop-shadow(0 0 20px rgba(120, 119, 198, 0.5));
    }
    
    .auth-hero h1 {
        font-size: 3rem;
        font-weight: 900;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #7877c6 0%, #ff77c6 50%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .auth-hero p {
        font-size: 1.1rem;
        color: rgba(255, 255, 255, 0.7);
        line-height: 1.6;
    }
    
    .auth-form-wrapper {
        position: relative;
    }
    
    .auth-form {
        background: rgba(15, 15, 35, 0.9);
        backdrop-filter: blur(30px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 24px;
        padding: 3rem;
        box-shadow: 
            0 25px 50px rgba(0, 0, 0, 0.5),
            0 0 100px rgba(120, 119, 198, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .auth-form::before {
        content: '';
        position: absolute;
        top: -2px; left: -2px; right: -2px; bottom: -2px;
        background: linear-gradient(45deg, 
            rgba(120, 119, 198, 0.3), 
            rgba(255, 119, 198, 0.3), 
            rgba(34, 197, 94, 0.2),
            rgba(120, 119, 198, 0.3));
        border-radius: 26px;
        z-index: -1;
        opacity: 0.7;
        animation: authGlow 4s ease-in-out infinite alternate;
    }
    
    @keyframes authGlow {
        0% { opacity: 0.3; }
        100% { opacity: 0.8; }
    }
    
    .auth-header {
        text-align: center;
        margin-bottom: 2.5rem;
    }
    
    .auth-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: #fff;
        text-align: center;
    }
    
    .auth-subtitle {
        color: rgba(156, 163, 175, 0.9);
        text-align: center;
        font-size: 1rem;
    }
    
    .auth-input-group {
        position: relative;
        margin-bottom: 1.5rem;
    }
    
    .auth-input-label {
        display: block;
        color: rgba(255, 255, 255, 0.9);
        font-weight: 600;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .auth-input {
        width: 100%;
        padding: 1.3rem 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        background: rgba(15, 15, 35, 0.7);
        color: #fff;
        font-size: 1rem;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }
    
    .auth-input::placeholder {
        color: rgba(156, 163, 175, 0.5);
    }
    
    .auth-input:focus {
        outline: none;
        border-color: rgba(120, 119, 198, 0.6);
        background: rgba(15, 15, 35, 0.9);
        box-shadow: 
            0 0 0 3px rgba(120, 119, 198, 0.1),
            0 8px 25px rgba(120, 119, 198, 0.2);
        transform: translateY(-2px);
    }
    
    .auth-btn {
        width: 100%;
        padding: 1.4rem;
        border: none;
        border-radius: 16px;
        background: linear-gradient(135deg, #7877c6, #ff77c6);
        color: #fff;
        font-weight: 800;
        font-size: 1.1rem;
        cursor: pointer;
        transition: all 0.3s ease;
        margin: 2rem 0 1.5rem 0;
        box-shadow: 0 8px 30px rgba(120, 119, 198, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .auth-btn::before {
        content: '';
        position: absolute;
        top: 0; left: -100%; right: 100%; bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: all 0.6s;
    }
    
    .auth-btn:hover::before {
        left: 100%; right: -100%;
    }
    
    .auth-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 40px rgba(120, 119, 198, 0.4);
    }
    
    .auth-divider {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin: 2rem 0;
    }
    
    .auth-divider::before,
    .auth-divider::after {
        content: '';
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    }
    
    .auth-divider span {
        color: rgba(156, 163, 175, 0.7);
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    .auth-link {
        display: block;
        text-align: center;
        color: rgba(156, 163, 175, 0.9);
        text-decoration: none;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .auth-link:hover {
        color: #7877c6;
        transform: translateY(-1px);
    }
    
    .auth-link strong {
        color: #7877c6;
        font-weight: 700;
    }
    
    .social-btn {
        width: 100%;
        padding: 1.2rem;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.05);
        color: #fff;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.8rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
    }
    
    .social-btn:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(255, 255, 255, 0.3);
        transform: translateY(-2px);
    }

    /* Additional utility styles */
    .likert-row {
        display: flex;
        gap: 1rem;
        justify-content: center;
        flex-wrap: wrap;
    }
    .bubble {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #fff;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .bubble:hover {
        color: #7877c6;
    }
    .bubble input[type="radio"] {
        appearance: none;
        width: 20px;
        height: 20px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        position: relative;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .bubble input[type="radio"]:checked {
        border-color: #7877c6;
        background: #7877c6;
    }
    .bubble input[type="radio"]:checked::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: white;
    }

    .scale-info {
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: rgba(255, 255, 255, 0.8);
        text-align: center;
    }
    
    /* Upload area styles */
    .upload-area {
        border: 2px dashed rgba(255, 255, 255, 0.3);
        border-radius: 12px;
        padding: 3rem 2rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        background: rgba(15, 15, 35, 0.4);
    }
    .upload-area:hover {
        border-color: #7877c6;
        background: rgba(120, 119, 198, 0.1);
    }
    .upload-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .file-input {
        display: none;
    }
    
    /* Image preview styles */
    .image-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 2rem;
        margin: 2rem 0;
    }
    .image-preview, .generated-image {
        width: 100%;
        max-width: 400px;
        height: 300px;
        object-fit: cover;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin: 0 auto;
        display: block;
    }
    
    /* Feedback card styles */
    .feedback-card {
        background: rgba(15, 15, 35, 0.8);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .feedback-title {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        color: #fff;
        text-align: center;
    }
    
    /* Song grid and workout styles */
    .song-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 1rem;
    }
    .song-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        transition: all 0.3s ease;
    }
    .song-card:hover {
        background: rgba(255, 255, 255, 0.1);
        transform: translateY(-2px);
    }
    .song-title {
        font-weight: 600;
        color: #fff;
        margin-bottom: 0.5rem;
    }
    .spotify-link {
        color: #1db954;
        text-decoration: none;
        font-weight: 600;
    }
    .spotify-link:hover {
        color: #1ed760;
    }
    
    .workout-plan {
        color: #fff;
        line-height: 1.8;
    }
    .workout-section {
        margin-bottom: 2rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
    }
    .workout-section h3 {
        color: #7877c6;
        margin-bottom: 1rem;
        font-size: 1.3rem;
    }
    .workout-section ul {
        list-style: none;
        padding: 0;
    }
    .workout-section li {
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .workout-section li:last-child {
        border-bottom: none;
    }
    
    /* Task card styles */
    .task-card {
        text-align: center;
    }
    .task-row {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 1rem;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    .task-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #fff;
        margin: 2rem 0 1rem 0;
    }
    .badge {
        padding: 0.5rem 1rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-blue {
        background: rgba(59, 130, 246, 0.2);
        color: #93c5fd;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    .badge-green {
        background: rgba(34, 197, 94, 0.2);
        color: #86efac;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    
    /* Back link */
    .back-link {
        display: inline-block;
        color: rgba(255, 255, 255, 0.8);
        text-decoration: none;
        font-weight: 600;
        margin-top: 2rem;
        transition: all 0.3s ease;
    }
    .back-link:hover {
        color: #7877c6;
        transform: translateX(-5px);
    }

</style>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
    
        if (username == "admin" and password == "admin") or \
           (username == "demo" and password == "demo") or \
           (username == "test" and password == "test"):
            session["user"] = username
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password"
      
            return render_template_string("""
<!doctype html><html><head>
    <title>🔐 Login - Zenith</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="auth-page">
        <div class="auth-container">
            <div class="auth-hero">
                <div class="auth-hero-icon">💚</div>
                <h1>Welcome Back</h1>
                <p>Sign in to continue your wellness journey with personalized AI-powered insights, curated playlists, and health tracking.</p>
            </div>
            
            <div class="auth-form-wrapper">
                <form class="auth-form" method="POST">
                    <div class="auth-header">
                        <h2 class="auth-title">Sign In</h2>
                        <p class="auth-subtitle">Enter your credentials to access your account</p>
                    </div>
                    
                    <div class="error-card">
                        <strong>❌ Error:</strong> {{ error }}
                    </div>
                    
                    <div class="auth-input-group">
                        <label class="auth-input-label" for="username">Username</label>
                        <input 
                            type="text" 
                            id="username" 
                            name="username" 
                            class="auth-input" 
                            placeholder="Try: admin, demo, or test" 
                            required 
                            autocomplete="username"
                        >
                    </div>
                    
                    <div class="auth-input-group">
                        <label class="auth-input-label" for="password">Password</label>
                        <input 
                            type="password" 
                            id="password" 
                            name="password" 
                            class="auth-input" 
                            placeholder="Same as username" 
                            required 
                            autocomplete="current-password"
                        >
                    </div>
                    
                    <button type="submit" class="auth-btn">
                        🚀 Sign In
                    </button>
                    
                    <div class="auth-divider">
                        <span>Demo Credentials</span>
                    </div>
                    
                    <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 1rem; color: #4ade80; font-size: 0.9rem; text-align: center; margin-bottom: 1.5rem;">
                        <strong>Demo Users:</strong><br>
                        admin/admin • demo/demo • test/test
                    </div>
                    
                    <a href="{{ url_for('signup') }}" class="auth-link">
                        Don't have an account? <strong>Sign up here</strong>
                    </a>
                    
                    <a href="{{ url_for('home') }}" class="auth-link" style="margin-top: 1rem;">
                        ← Back to Home
                    </a>
                </form>
            </div>
        </div>
    </div>
</body></html>
            """, css=MODERN_CSS, error=error)
    
    return render_template_string("""
<!doctype html><html><head>
    <title>🔐 Login - Zenith</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="auth-page">
        <div class="auth-container">
            <div class="auth-hero">
                <div class="auth-hero-icon">💚</div>
                <h1>Welcome Back</h1>
                <p>Sign in to continue your wellness journey with personalized AI-powered insights, curated playlists, and health tracking.</p>
            </div>
            
            <div class="auth-form-wrapper">
                <form class="auth-form" method="POST">
                    <div class="auth-header">
                        <h2 class="auth-title">Sign In</h2>
                        <p class="auth-subtitle">Enter your credentials to access your account</p>
                    </div>
                    
                    <div class="auth-input-group">
                        <label class="auth-input-label" for="username">Username</label>
                        <input 
                            type="text" 
                            id="username" 
                            name="username" 
                            class="auth-input" 
                            placeholder="Try: admin, demo, or test" 
                            required 
                            autocomplete="username"
                        >
                    </div>
                    
                    <div class="auth-input-group">
                        <label class="auth-input-label" for="password">Password</label>
                        <input 
                            type="password" 
                            id="password" 
                            name="password" 
                            class="auth-input" 
                            placeholder="Same as username" 
                            required 
                            autocomplete="current-password"
                        >
                    </div>
                    
                    <button type="submit" class="auth-btn">
                        🚀 Sign In
                    </button>
                    
                    <div class="auth-divider">
                        <span>Demo Credentials</span>
                    </div>
                    
                    <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 1rem; color: #4ade80; font-size: 0.9rem; text-align: center; margin-bottom: 1.5rem;">
                        <strong>Demo Users:</strong><br>
                        admin/admin • demo/demo • test/test
                    </div>
                    
                    <a href="{{ url_for('signup') }}" class="auth-link">
                        Don't have an account? <strong>Sign up here</strong>
                    </a>
                    
                    <a href="{{ url_for('home') }}" class="auth-link" style="margin-top: 1rem;">
                        ← Back to Home
                    </a>
                </form>
            </div>
        </div>
    </div>
</body></html>
    """, css=MODERN_CSS)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username or not password:
            error = "Please enter both username and password."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        else:
            users = _load_users()
            if not isinstance(users, dict):
                users = {}
            if username in users:
                error = "Username already exists. Please choose another."
            else:
               
                users[username] = {
                    "password_hash": generate_password_hash(password)
                }
                _save_users(users)
                session["user"] = username
                return redirect(url_for("home"))
        
      
        html = """
<!doctype html><html><head>
    <title>📝 Sign Up - Zenith</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="container auth-container">
        <div class="auth-form">
            <h2 class="auth-title">Create Account</h2>
            <p class="auth-subtitle">Join Zenith and start your wellness journey</p>
            
            {% if error %}
                <div class="error-card" style="margin-bottom: 1.5rem;">{{ error }}</div>
            {% endif %}
            
            <form method="POST">
                <input class="auth-input" name="username" placeholder="Choose a username" required>
                <input class="auth-input" type="password" name="password" placeholder="Password (min 6 characters)" minlength="6" required>
                <button class="auth-btn" type="submit">Create Account</button>
            </form>
            
            <a class="auth-link" href="{{ url_for('login') }}">Already have an account? Log in</a>
        </div>
        
        <div class="auth-image">
            <div style="background: linear-gradient(45deg, #ff6b6b, #4ecdc4); width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-size: 4rem;">
                ✨
            </div>
        </div>
    </div>
</body></html>
        """
        return render_template_string(html, css=MODERN_CSS, error=error)
    
    
    html = """
<!doctype html><html><head>
    <title>📝 Sign Up - Zenith</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="container auth-container">
        <div class="auth-form">
            <h2 class="auth-title">Create Account</h2>
            <p class="auth-subtitle">Join Zenith and start your wellness journey</p>
            
            <form method="POST">
                <input class="auth-input" name="username" placeholder="Choose a username" required>
                <input class="auth-input" type="password" name="password" placeholder="Password (min 6 characters)" minlength="6" required>
                <button class="auth-btn" type="submit">Create Account</button>
            </form>
            
            <a class="auth-link" href="{{ url_for('login') }}">Already have an account? Log in</a>
        </div>
        
        <div class="auth-image">
            <div style="background: linear-gradient(45deg, #ff6b6b, #4ecdc4); width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-size: 4rem;">
                ✨
            </div>
        </div>
    </div>
</body></html>
    """
    return render_template_string(html, css=MODERN_CSS)



@app.route("/logout")
def logout():
    """Log out the current user by clearing their session"""
    session.pop("user", None)
    return redirect(url_for("home"))

@app.route("/")
def home():
    user = current_user()
    
    html = """
<!doctype html><html><head>
    <title>🏠 Zenith - AI Wellness Platform</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <nav class="top-nav">
        <div class="nav-content">
            <!-- Left Side -->
            <div class="nav-brand">
                <div class="brand-logo">
                    <span class="logo-icon">💚</span>
                    <span class="brand-text">ZENITH</span>
                </div>
                <div class="status-pill">
                    <div class="status-dot"></div>
                    <span class="status-text">Spotify</span>
                </div>
            </div>
            
            <!-- Center Welcome -->
            {% if user %}
            <div class="nav-welcome">
                <div class="welcome-pill">
                    <span class="welcome-icon">👋</span>
                    <span class="welcome-text">Welcome, <span class="username-highlight">{{ user }}</span></span>
                </div>
            </div>
            {% endif %}
            
            <!-- Right Actions -->
            <div class="nav-actions">
                {% if user %}
                    <a href="{{ url_for('logout') }}" class="nav-btn logout-btn">
                        <span class="btn-icon">🚪</span>
                        <span class="btn-text">Logout</span>
                    </a>
                {% else %}
                    <a href="{{ url_for('login') }}" class="nav-btn login-btn">
                        <span class="btn-icon">🔐</span>
                        <span class="btn-text">Login</span>
                    </a>
                    <a href="{{ url_for('signup') }}" class="nav-btn signup-btn">
                        <span class="btn-icon">✨</span>
                        <span class="btn-text">Sign Up</span>
                    </a>
                {% endif %}
            </div>
        </div>
    </nav>

    <style>
        /* Enhanced Navbar Container */
        .nav-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
            position: relative;
        }
        
        /* Left Brand Section */
        .nav-brand {
            display: flex;
            align-items: center;
            gap: 1.5rem;
            flex: 1;
        }
        
        .brand-logo {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }
        
        .logo-icon {
            font-size: 1.6rem;
            filter: drop-shadow(0 0 8px rgba(34, 197, 94, 0.6));
        }
        
        .brand-text {
            font-family: 'Inter', sans-serif;
            font-weight: 800;
            font-size: 1.3rem;
            letter-spacing: 1.5px;
            background: linear-gradient(135deg, #22c55e, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 15px rgba(34, 197, 94, 0.3);
        }
        
        .status-pill {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(34, 197, 94, 0.12);
            border: 1px solid rgba(34, 197, 94, 0.25);
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            backdrop-filter: blur(8px);
        }
        
        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 8px rgba(34, 197, 94, 0.8);
            animation: pulse 2.5s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(1.2); }
        }
        
        .status-text {
            color: #4ade80;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        /* Center Welcome Section */
        .nav-welcome {
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            z-index: 10;
        }
        
        .welcome-pill {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            background: rgba(15, 15, 35, 0.9);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(120, 119, 198, 0.3);
            padding: 0.8rem 1.5rem;
            border-radius: 25px;
            box-shadow: 0 4px 20px rgba(120, 119, 198, 0.2);
            position: relative;
            overflow: hidden;
        }
        
        .welcome-pill::before {
            content: '';
            position: absolute;
            top: -2px; left: -2px; right: -2px; bottom: -2px;
            background: linear-gradient(45deg, 
                rgba(120, 119, 198, 0.4), 
                rgba(255, 119, 198, 0.4), 
                rgba(34, 197, 94, 0.4), 
                rgba(120, 119, 198, 0.4));
            border-radius: 27px;
            z-index: -1;
            animation: welcomeGlow 3s ease-in-out infinite alternate;
        }
        
        @keyframes welcomeGlow {
            0% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        
        .welcome-icon {
            font-size: 1.1rem;
            animation: wave 2s ease-in-out infinite;
        }
        
        @keyframes wave {
            0%, 100% { transform: rotate(0deg); }
            25% { transform: rotate(-10deg); }
            75% { transform: rotate(10deg); }
        }
        
        .welcome-text {
            color: rgba(255, 255, 255, 0.9);
            font-size: 0.95rem;
            font-weight: 600;
            white-space: nowrap;
        }
        
        .username-highlight {
            background: linear-gradient(135deg, #7877c6, #ff77c6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
            text-transform: capitalize;
        }
        
        /* Right Actions */
        .nav-actions {
            display: flex;
            gap: 0.8rem;
            flex: 1;
            justify-content: flex-end;
        }
        
        .nav-btn {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.7rem 1.2rem;
            border-radius: 12px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 0.3s cubic-bezier(0.23, 1, 0.320, 1);
            position: relative;
            overflow: hidden;
        }
        
        .nav-btn::before {
            content: '';
            position: absolute;
            top: 0; left: -100%; right: 100%; bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
            transition: all 0.5s;
        }
        
        .nav-btn:hover::before {
            left: 100%; right: -100%;
        }
        
        .login-btn {
            background: rgba(55, 65, 81, 0.6);
            border: 1px solid rgba(156, 163, 175, 0.3);
            color: #d1d5db;
        }
        
        .login-btn:hover {
            background: rgba(55, 65, 81, 0.8);
            border-color: rgba(156, 163, 175, 0.5);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(55, 65, 81, 0.4);
        }
        
        .signup-btn {
            background: linear-gradient(135deg, #7c3aed, #a855f7);
            border: 1px solid rgba(124, 58, 237, 0.5);
            color: #fff;
            box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3);
        }
        
        .signup-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(124, 58, 237, 0.5);
        }
        
        .logout-btn {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fca5a5;
        }
        
        .logout-btn:hover {
            background: rgba(239, 68, 68, 0.25);
            border-color: rgba(239, 68, 68, 0.5);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(239, 68, 68, 0.3);
        }
        
        /* Mobile Responsive */
        @media (max-width: 1024px) {
            .nav-welcome {
                position: relative;
                left: auto;
                transform: none;
                flex: 1;
                display: flex;
                justify-content: center;
                margin: 0 1rem;
            }
            
            .nav-content {
                padding: 0 1rem;
            }
        }
        
        @media (max-width: 768px) {
            .nav-brand {
                gap: 1rem;
            }
            
            .brand-text {
                font-size: 1.1rem;
                letter-spacing: 1px;
            }
            
            .status-pill {
                padding: 0.3rem 0.6rem;
            }
            
            .status-text {
                display: none;
            }
            
            .nav-btn .btn-text {
                display: none;
            }
            
            .nav-btn {
                padding: 0.7rem;
            }
            
            .welcome-pill {
                padding: 0.6rem 1rem;
                margin: 0;
            }
            
            .welcome-text {
                font-size: 0.85rem;
            }
        }
        
        @media (max-width: 640px) {
            .nav-welcome {
                display: none;
            }
            
            .nav-content {
                justify-content: space-between;
            }
            
            .nav-brand,
            .nav-actions {
                flex: none;
            }
        }
    </style>
    
    

    <div class="container">
        <div class="hero">
            <div class="hero-badge">
                ✨ AI Wellness Companion
            </div>
            <h1>Feel better, move smarter, and soundtrack your day.</h1>
            <p>Techy, neon-glass interface with fast flows for music, workouts, posture analysis, wellbeing check-ins, and a 7-day diet planner.</p>
        </div>

        <div class="feature-grid">
            {% if user %}
                <a href="/music" class="feature-link">
                    <div class="feature-card">
                        <div class="feature-icon">🎵</div>
                        <h3>Mood Harmonizer</h3>
                        <p>AI-curated playlists by mood with one click.</p>
                    </div>
                </a>
                
                <a href="/workout" class="feature-link">
                    <div class="feature-card">
                        <div class="feature-icon">💪</div>
                        <h3>Fitness Architect</h3>
                        <p>One-day plan with sets × reps and rest.</p>
                    </div>
                </a>
                
                <a href="/posture" class="feature-link">
                    <div class="feature-card">
                        <div class="feature-icon">🏃</div>
                        <h3>Posture Coach</h3>
                        <p>Upload a photo & get form feedback.</p>
                    </div>
                </a>
                
                <a href="/wellbeing" class="feature-link">
                    <div class="feature-card">
                        <div class="feature-icon">🧠</div>
                        <h3>Well-being Survey</h3>
                        <p>5 quick answers → 7-day guidance.</p>
                    </div>
                </a>
                
                <a href="/daily" class="feature-link">
                    <div class="feature-card">
                        <div class="feature-icon">✅</div>
                        <h3>Daily Task</h3>
                        <p>One tiny action to build momentum.</p>
                    </div>
                </a>
                
                <a href="/diet" class="feature-link">
                    <div class="feature-card">
                        <div class="feature-icon">🥗</div>
                        <h3>Diet Planner</h3>
                        <p>Get a 7-day plan for cutting or bulking.</p>
                    </div>
                </a>
            {% else %}
                <div class="feature-card" style="opacity: 0.7;">
                    <div class="feature-icon">🎵</div>
                    <h3>Mood Harmonizer</h3>
                    <p>AI-curated playlists by mood with one click.</p>
                </div>
                
                <div class="feature-card" style="opacity: 0.7;">
                    <div class="feature-icon">💪</div>
                    <h3>Fitness Architect</h3>
                    <p>One-day plan with sets × reps and rest.</p>
                </div>
                
                <div class="feature-card" style="opacity: 0.7;">
                    <div class="feature-icon">🏃</div>
                    <h3>Posture Coach</h3>
                    <p>Upload a photo & get form feedback.</p>
                </div>
                
                <div class="feature-card" style="opacity: 0.7;">
                    <div class="feature-icon">🧠</div>
                    <h3>Well-being Survey</h3>
                    <p>5 quick answers → 7-day guidance.</p>
                </div>
                
                <div class="feature-card" style="opacity: 0.7;">
                    <div class="feature-icon">✅</div>
                    <h3>Daily Task</h3>
                    <p>One tiny action to build momentum.</p>
                </div>
                
                <div class="feature-card" style="opacity: 0.7;">
                    <div class="feature-icon">🥗</div>
                    <h3>Diet Planner</h3>
                    <p>Get a 7-day plan for cutting or bulking.</p>
                </div>
                
                <div class="glass-card" style="grid-column: 1 / -1; text-align: center; background: rgba(255, 119, 198, 0.05); border-color: rgba(255, 119, 198, 0.2);">
                    <h3 style="color: #ff77c6; margin-bottom: 1rem;">🔒 Login Required</h3>
                    <p style="color: rgba(255, 255, 255, 0.8); margin-bottom: 2rem;">Create an account or log in to access all wellness features</p>
                    <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                        <a href="{{ url_for('signup') }}" class="btn btn-secondary">🚀 Sign Up Free</a>
                        <a href="{{ url_for('login') }}" class="btn btn-primary">🔐 Login</a>
                    </div>
                </div>
            {% endif %}
        </div>
    </div>
</body></html>
    """
    return render_template_string(html, css=MODERN_CSS, user=user)


@app.route("/music", methods=["GET", "POST"])
@login_required  
def music():
    songs, error, selected = [], None, "happy"
    if request.method == "POST":
        selected = request.form.get("mood", "happy")
        if not sp:
            error = "🚫 Spotify not configured (.env CLIENT_ID/CLIENT_SECRET)."
        else:
            try:
                songs = get_recommendations(sp, mood=selected, limit=8) or []
                if not songs:
                    error = "🎭 No matching tracks. Try another mood."
            except Exception as e:
                error = f"🛠️ Error fetching songs: {e}"

    html = """
<!doctype html><html><head>
    <title>🎵 Mood Harmonizer - Zenith</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="container">
        <div class="hero">
            <h1>🎵 Mood Harmonizer</h1>
            <p>Let AI pick the soundtrack.</p>
        </div>
        
        <div class="form-container">
            <form method="POST">
                <div class="form-group">
                    <label>🎭 Mood</label>
                    <select name="mood" class="form-control">
                        <option value="motivational" {% if selected=='motivational' %}selected{% endif %}>🔥 Motivational</option>
                        <option value="focus" {% if selected=='focus' %}selected{% endif %}>🧠 Focus</option>
                        <option value="peaceful" {% if selected=='peaceful' %}selected{% endif %}>😌 Peaceful</option>
                        <option value="happy" {% if selected=='happy' %}selected{% endif %}>😊 Happy</option>
                    </select>
                </div>
                <button class="btn btn-primary" type="submit">🎶 Generate Playlist</button>
            </form>
        </div>

        {% if error %}
            <div class="error-card"><strong>{{ error }}</strong></div>
        {% endif %}
        
        {% if songs %}
            <div class="glass-card">
                <h2 style="color:#fff;text-align:center;margin-bottom:1rem;">Playlist</h2>
                <div class="song-grid">
                    {% for s in songs %}
                        <div class="song-card">
                            <div class="song-title">{{ s.name }}</div>
                            <div style="opacity:.85;margin:.25rem 0 .6rem 0;">by {{ s.artist }}</div>
                            <a class="spotify-link" target="_blank" href="{{ s.url }}">🎧 Listen on Spotify</a>
                        </div>
                    {% endfor %}
                </div>
            </div>
        {% endif %}
        
        <a style="color:#fff;text-decoration:none;" href="/">← Back</a>
    </div>
</body></html>
    """
    return render_template_string(html, css=MODERN_CSS, songs=songs, error=error, selected=selected)


@app.route("/workout", methods=["GET", "POST"])
@login_required 
def workout_page():
    plan, error = None, None
    selected_mood, selected_difficulty, selected_option, selected_time = "energized", "beginner", "cardio", 30

    if request.method == "POST":
        selected_mood = request.form.get("mood", "energized")
        selected_difficulty = request.form.get("difficulty", "beginner")
        selected_option = request.form.get("option", "cardio")
        selected_time = int(request.form.get("time", 30))

        try:
            prompt = (
                f"Call the workout tool with mood='{selected_mood}', difficulty='{selected_difficulty}', "
                f"option='{selected_option}', time={selected_time}. "
                f"Then provide a detailed one-day workout plan with concrete exercises and timing."
            )
            resp = work.run(prompt)
            plan = extract_text(resp)
        except Exception as e:
            error = f"🛠️ Error generating workout: {e}"

    html = """
<!doctype html><html><head>
    <title>💪 Fitness Architect - Zenith</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="container">
        <div class="hero">
            <h1>💪 Fitness Architect</h1>
            <p>AI-powered personalized workouts.</p>
        </div>

        <div class="form-container">
            <form method="POST">
                <div class="form-group">
                    <label>🎯 Current Mood</label>
                    <select name="mood" class="form-control">
                        <option value="energized" {% if selected_mood=='energized' %}selected{% endif %}>⚡ Energized</option>
                        <option value="stressed" {% if selected_mood=='stressed' %}selected{% endif %}>😤 Stressed</option>
                        <option value="tired" {% if selected_mood=='tired' %}selected{% endif %}>😴 Tired</option>
                        <option value="motivated" {% if selected_mood=='motivated' %}selected{% endif %}>🔥 Motivated</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>📈 Difficulty Level</label>
                    <select name="difficulty" class="form-control">
                        <option value="beginner" {% if selected_difficulty=='beginner' %}selected{% endif %}>🌱 Beginner</option>
                        <option value="intermediate" {% if selected_difficulty=='intermediate' %}selected{% endif %}>🏃 Intermediate</option>
                        <option value="advanced" {% if selected_difficulty=='advanced' %}selected{% endif %}>💪 Advanced</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>🎯 Workout Style</label>
                    <select name="option" class="form-control">
                        <option value="cardio" {% if selected_option=='cardio' %}selected{% endif %}>🏃 Cardio</option>
                        <option value="weight lifting" {% if selected_option=='weight lifting' %}selected{% endif %}>🏋️ Weight Lifting</option>
                        <option value="calisthenics" {% if selected_option=='calisthenics' %}selected{% endif %}>🤸 Calisthenics</option>
                        <option value="meditation" {% if selected_option=='meditation' %}selected{% endif %}>🧘 Meditation</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>⏰ Duration (minutes)</label>
                    <select name="time" class="form-control">
                        <option value="15" {% if selected_time==15 %}selected{% endif %}>15 minutes</option>
                        <option value="30" {% if selected_time==30 %}selected{% endif %}>30 minutes</option>
                        <option value="45" {% if selected_time==45 %}selected{% endif %}>45 minutes</option>
                        <option value="60" {% if selected_time==60 %}selected{% endif %}>60 minutes</option>
                    </select>
                </div>

                <button class="btn btn-primary" type="submit">🚀 Generate Workout</button>
            </form>
        </div>

        {% if error %}
            <div class="error-card"><strong>{{ error }}</strong></div>
        {% endif %}

        {% if plan %}
            <div class="glass-card">
                <h2 style="color:#fff;text-align:center;margin-bottom:1rem;">Your Personalized Workout</h2>
                <div class="workout-plan" style="white-space:pre-wrap;">{{ plan }}</div>
            </div>
        {% endif %}

        <a style="color:#fff;text-decoration:none;" href="/">← Back</a>
    </div>
</body></html>
    """
    return render_template_string(
        html,
        css=MODERN_CSS,
        plan=plan,
        error=error,
        selected_mood=selected_mood,
        selected_difficulty=selected_difficulty,
        selected_option=selected_option,
        selected_time=selected_time
    )


@app.route("/posture", methods=["GET", "POST"])
@login_required  
def posture_coach():
    feedback_text, data, error = None, None, None
    uploaded_files = []
    selected_exercise = None
    correct_form_image_url = None

    if request.method == "POST":
        selected_exercise = request.form.get("exercise", "").strip() or None

    
        files = []
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and file.filename != '':
                files = [file]

 
        valid_files = []
        for f in files:
            if f and f.filename and f.filename != '' and allowed_file(f.filename):
                valid_files.append(f)

        if not valid_files:
            error = "📸 Please select a valid image file (JPG, PNG, GIF, WebP, BMP)."
        else:
            images_payload = []
            try:
                for i, f in enumerate(valid_files[:3]):  # Max 3 images
                    fname = f"posture_analysis_{i}_{secure_filename(f.filename)}"
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
                    f.save(save_path)
                    uploaded_files.append(fname)

                    
                    success, b64_data, mime_type, error_msg = validate_and_convert_image(save_path)

                    if not success:
                        error = f"❌ Image processing failed: {error_msg}"
                        break

                    image_payload = create_anthropic_image_payload(b64_data, mime_type)
                    images_payload.append(image_payload)

                if not images_payload and not error:
                    error = "🚫 No valid images could be processed."
                elif images_payload:
                 
                    exercise_context = (
                        f"Exercise being performed: {selected_exercise}. "
                        if selected_exercise else
                        "Exercise type not specified. "
                    )
                    prompt = (
                        exercise_context +
                        "Analyze the workout form in this photo. Follow the JSON schema exactly. "
                        "Focus on: 1) Major form issues (severity ordered), 2) Injury risks, "
                        "3) Specific corrections with actionable cues and drills. "
                        "Be detailed about what you observe in the image. "
                        "Return valid JSON only - no markdown formatting or extra text."
                    )

                    try:
                        resp = posture_agent.run(prompt, images=images_payload)
                    except Exception:
                  
                        message_content = [{"type": "text", "text": prompt}]
                        message_content.extend(images_payload)
                        resp = posture_agent.run(message_content)

                    text = extract_text(resp).strip()
                    feedback_text = text

                 
                    try:
                        
                        if text.startswith('```json'):
                            text = text.replace('```json', '').replace('```', '').strip()
                        elif text.startswith('```'):
                            text = text.replace('```', '').strip()

                        data = json.loads(text)

                   
                        if data and data.get('exercise'):
                            correct_form_image_url = generate_correct_form_image(selected_exercise, data)

                    except json.JSONDecodeError:
             
                        error = "🔧 Analysis completed but response format issue. Raw feedback available below."

            except Exception as e:
                error = f"🛠️ Error processing images: {e}"

    html = """
<!doctype html><html><head>
    <title>🏃 Posture Coach - Zenith</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="container">
        <div class="hero">
            <h1>🏃 Posture Coach</h1>
            <p>Upload a workout photo for AI form analysis & perfect form visualization</p>
        </div>

        <div class="form-container">
            <form method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <label>🏋️ Exercise Name (Optional)</label>
                    <input type="text" name="exercise" class="form-control" 
                           placeholder="e.g., squats, deadlift, push-ups..." 
                           value="{{ selected_exercise or '' }}">
                </div>
                
                <div class="form-group">
                    <label>📸 Upload Workout Photo</label>
                    <div class="upload-area" onclick="document.getElementById('file-input').click();">
                        <div class="upload-icon">📷</div>
                        <div style="color: #fff; font-weight: 600;">Click to select image</div>
                        <div style="color: rgba(255,255,255,0.7); font-size: 0.9rem; margin-top: 0.5rem;">
                            Supported: JPG, PNG, GIF, WebP, BMP (max 16MB)
                        </div>
                    </div>
                    <input id="file-input" class="file-input" type="file" name="image" 
                           accept="image/*,.jpg,.jpeg,.png,.gif,.webp,.bmp" required
                           onchange="showFileName(this)">
                    <div id="file-name" style="color: #fff; margin-top: 0.5rem; font-size: 0.9rem;"></div>
                </div>
                
                <button class="btn btn-upload" type="submit">🔍 Analyze Posture</button>
            </form>
        </div>

        {% if error %}
            <div class="error-card"><strong>{{ error }}</strong></div>
        {% endif %}

        {% if uploaded_files and (data or feedback_text) %}
            <div class="glass-card">
                <h3 style="color: #fff; text-align: center; margin-bottom: 2rem;">📸 Analysis Results</h3>
                
                <div class="image-grid">
                    <div>
                        <h4 style="color: #fff; text-align: center; margin-bottom: 1rem;">Your Form</h4>
                        {% for filename in uploaded_files %}
                            <img src="{{ url_for('uploaded_file', filename=filename) }}" 
                                 class="image-preview" alt="Your workout photo">
                        {% endfor %}
                    </div>
                    
                    {% if correct_form_image_url %}
                    <div>
                        <h4 style="color: #4CAF50; text-align: center; margin-bottom: 1rem;">Perfect Form Reference</h4>
                        <img src="{{ correct_form_image_url }}" 
                             class="generated-image" alt="AI-generated correct form">
                    </div>
                    {% endif %}
                </div>
            </div>
        {% endif %}

        {% if data %}
            <div class="feedback-card">
                <div class="feedback-title">🎯 Posture Analysis Results</div>
                
                <div style="margin-bottom: 1rem;">
                    <strong>Exercise:</strong> {{ data.exercise or 'Not specified' }}<br>
                    <strong>Overall Assessment:</strong> {{ data.overall or 'No assessment provided' }}<br>
                    <strong>Confidence:</strong> {{ "%.1f%%" | format((data.confidence or 0) * 100) }}
                </div>

                {% if data.major_issues %}
                    <div style="margin-bottom: 1rem;">
                        <strong style="color: #ff6b6b;">⚠️ Major Issues:</strong>
                        <ul style="margin-left: 1rem; list-style: disc;">
                            {% for issue in data.major_issues %}
                                <li><strong>{{ issue.body_part }}:</strong> {{ issue.problem }} 
                                    <span style="color: #ff6b6b;">({{ issue.severity }})</span>
                                    {% if issue.evidence %}<br><em>Evidence: {{ issue.evidence }}</em>{% endif %}
                                </li>
                            {% endfor %}
                        </ul>
                    </div>
                {% endif %}

                {% if data.risks_if_unchanged %}
                    <div style="margin-bottom: 1rem;">
                        <strong style="color: #ffa726;">⚡ Risks if Unchanged:</strong>
                        <ul style="margin-left: 1rem; list-style: disc;">
                            {% for risk in data.risks_if_unchanged %}
                                <li>{{ risk }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                {% endif %}

                {% if data.corrections %}
                    <div style="margin-bottom: 1rem;">
                        <strong style="color: #4ecdc4;">✅ Corrections:</strong>
                        {% for correction in data.corrections %}
                            <div style="margin: 0.5rem 0; padding: 0.5rem; background: rgba(255,255,255,0.1); border-radius: 8px;">
                                <strong>{{ correction.issue_ref }}:</strong> {{ correction.fix }}
                                {% if correction.cues %}
                                    <br><strong>Cues:</strong> {{ correction.cues | join(', ') }}
                                {% endif %}
                                {% if correction.drills %}
                                    <br><strong>Drills:</strong> {{ correction.drills | join(', ') }}
                                {% endif %}
                            </div>
                        {% endfor %}
                    </div>
                {% endif %}
            </div>
        {% elif feedback_text and not data %}
            <div class="feedback-card">
                <div class="feedback-title">🎯 Posture Analysis (Raw Response)</div>
                <div style="white-space: pre-wrap;">{{ feedback_text }}</div>
            </div>
        {% endif %}

        <a style="color:#fff;text-decoration:none;" href="/">← Back</a>
    </div>

    <script>
        function showFileName(input) {
            const fileName = input.files[0] ? input.files[0].name : '';
            document.getElementById('file-name').textContent = fileName ? `Selected: ${fileName}` : '';
            
            if (fileName) {
                document.querySelector('.upload-area').style.borderColor = '#4ecdc4';
                document.querySelector('.upload-area').style.background = 'rgba(78, 205, 196, 0.1)';
            }
        }
    </script>

</body></html>
    """
    return render_template_string(
        html,
        css=MODERN_CSS,
        data=data,
        error=error,
        uploaded_files=uploaded_files,
        selected_exercise=selected_exercise,
        feedback_text=feedback_text,
        correct_form_image_url=correct_form_image_url
    )


@app.route("/wellbeing", methods=["GET", "POST"])
@login_required  # Require login for wellbeing feature
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

    html = """
<!doctype html><html><head>
    <title>🧠 Well-being Survey - Zenith</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="container">
        <div class="hero">
            <h1>🧠 Well-being Survey</h1>
            <p>5 quick questions → tailored advice.</p>
        </div>

        <div class="form-container">
            <div class="scale-info"><strong>Scale:</strong> 1=Never/Very Poor • 3=Sometimes/Fair • 5=Very Often/Excellent</div>
            <form method="POST">
                <div class="form-group">
                    <label>🧠 How often have you felt anxious or worried in the past week?</label>
                    <div class="likert-row">
                        {% for n in range(1,6) %}
                            <label class="bubble">
                                <input type="radio" name="feel" value="{{n}}" {% if n==3 %}checked{% endif %}> {{n}}
                            </label>
                        {% endfor %}
                    </div>
                </div>
                <div class="form-group">
                    <label>😞 How often have you felt down or depressed in the past week?</label>
                    <div class="likert-row">
                        {% for n in range(1,6) %}
                            <label class="bubble">
                                <input type="radio" name="down" value="{{n}}" {% if n==3 %}checked{% endif %}> {{n}}
                            </label>
                        {% endfor %}
                    </div>
                </div>
                <div class="form-group">
                    <label>😴 How would you rate your sleep quality recently?</label>
                    <div class="likert-row">
                        {% for n in range(1,6) %}
                            <label class="bubble">
                                <input type="radio" name="sleep" value="{{n}}" {% if n==3 %}checked{% endif %}> {{n}}
                            </label>
                        {% endfor %}
                    </div>
                </div>
                <div class="form-group">
                    <label>🔗 How connected do you feel to friends/family/support?</label>
                    <div class="likert-row">
                        {% for n in range(1,6) %}
                            <label class="bubble">
                                <input type="radio" name="connected" value="{{n}}" {% if n==3 %}checked{% endif %}> {{n}}
                            </label>
                        {% endfor %}
                    </div>
                </div>
                <div class="form-group">
                    <label>💥 How stressed or overwhelmed have you felt in the past week?</label>
                    <div class="likert-row">
                        {% for n in range(1,6) %}
                            <label class="bubble">
                                <input type="radio" name="stress" value="{{n}}" {% if n==3 %}checked{% endif %}> {{n}}
                            </label>
                        {% endfor %}
                    </div>
                </div>
                <button class="btn btn-primary" type="submit">✨ Get Tailored Advice</button>
            </form>
        </div>

        {% if advice %}
            <div class="glass-card">
                <h2 style="color:#fff; text-align:center; margin-bottom:1rem;">Your Personalized Guidance</h2>
                <div style="white-space:pre-wrap; color:#fff;">{{ advice }}</div>
            </div>
        {% endif %}

        <a style="color:#fff;text-decoration:none;" href="/">← Back</a>
    </div>
</body></html>
    """
    return render_template_string(html, css=MODERN_CSS, advice=advice)


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
            task = extract_text(resp).strip()

            import re
            task = re.sub(r"<think>.*?</think>", "", task, flags=re.DOTALL).strip()

            session["current_task"] = task
            msg = "🆕 New task generated!"

        elif action == "done":
            if session.get("current_task"):
                session["score"] = int(session["score"]) + 1
                session["current_task"] = ""
                msg = "✅ Great job! +1 point added."
            else:
                msg = "ℹ️ No active task to complete."

        elif action == "reset":
            session["score"] = 0
            session["current_task"] = ""
            msg = "🔄 Score and task reset."


    html = """
<!doctype html><html><head>
    <title>✅ Daily Task - Zenith</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="container">
        <div class="hero">
            <h1>✅ Daily Task</h1>
            <p>One tiny action to build momentum.</p>
        </div>

        <div class="glass-card task-card">
            <div class="task-row">
                <span class="badge badge-blue">Score: {{ score }}</span>
                {% if current_task %}
                    <span class="badge badge-green">Task Active</span>
                {% endif %}
            </div>

            <div class="task-title">Your Task</div>
            <div style="opacity:.95;">
                {% if current_task %}
                    {{ current_task }}
                {% else %}
                    No active task. Generate a new one!
                {% endif %}
            </div>

            {% if msg %}
                <div class="error-card" style="background:rgba(0,0,0,.25); border-color:rgba(255,255,255,.35);">
                    {{ msg }}
                </div>
            {% endif %}

            <form method="POST" class="task-row">
                <button class="btn btn-secondary" name="action" value="new" type="submit">🆕 New Task</button>
                <button class="btn btn-primary" name="action" value="done" type="submit">✅ Mark Done (+1)</button>
                <button class="btn" style="background:#ffffff22;color:#fff;" name="action" value="reset" type="submit">♻ Reset</button>
            </form>
        </div>

        <a style="color:#fff;text-decoration:none;" href="/">← Back</a>
    </div>
</body></html>
    """
    return render_template_string(
        html,
        css=MODERN_CSS,
        score=session.get("score", 0),
        current_task=session.get("current_task", ""),
        msg=msg
    )


@app.route("/diet", methods=["GET", "POST"])
@login_required 
def diet_page():
    plan_html, error = None, None
    goal = "cutting"  

    if request.method == "POST":
        goal = request.form.get("goal", "cutting").strip().lower()
        calories = request.form.get("calories", "").strip()
        prefs = request.form.get("prefs", "").strip()  

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
            text = extract_text(resp)
          
            plan_html = (
                text.replace("Day 1", "<b>Day 1</b>")
                    .replace("Day 2", "<b>Day 2</b>")
                    .replace("Day 3", "<b>Day 3</b>")
                    .replace("Day 4", "<b>Day 4</b>")
                    .replace("Day 5", "<b>Day 5</b>")
                    .replace("Day 6", "<b>Day 6</b>")
                    .replace("Day 7", "<b>Day 7</b>")
            )
        except Exception as e:
            error = f"🛠️ Error generating plan: {e}"

    html = """
<!doctype html><html><head>
  <title>🥗 Diet Planner - Zenith</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
  {{ css|safe }}
</head><body>
  <div class="container">
    <div class="hero">
      <h1>🥗 Diet Planner</h1>
      <p>Get a 7-day plan for cutting or bulking.</p>
    </div>

    <div class="form-container">
      <form method="POST">
        <div class="form-group">
          <label>🎯 Goal</label>
          <select name="goal" class="form-control">
            <option value="cutting" {% if goal=='cutting' %}selected{% endif %}>Cutting (fat loss)</option>
            <option value="bulking" {% if goal=='bulking' %}selected{% endif %}>Bulking (muscle gain)</option>
          </select>
        </div>

        <div class="form-group">
          <label>🔥 Target Calories (optional)</label>
          <input type="number" name="calories" class="form-control" placeholder="e.g., 2200" value="{{ request.form.get('calories','') }}">
        </div>

        <div class="form-group">
          <label>🚫 Preferences / Allergies (optional)</label>
          <input type="text" name="prefs" class="form-control" placeholder="e.g., vegetarian, no nuts, lactose-free" value="{{ request.form.get('prefs','') }}">
        </div>

        <button class="btn btn-primary" type="submit">🍽️ Generate 7-Day Plan</button>
      </form>
    </div>

    {% if error %}
      <div class="error-card"><strong>{{ error }}</strong></div>
    {% endif %}

    {% if plan_html %}
      <div class="glass-card" style="color:#fff;">
        <h2 style="text-align:center;margin-bottom:1rem;">Your Plan</h2>
        <div style="white-space:pre-wrap;">{{ plan_html|safe }}</div>
      </div>
    {% endif %}

    <a style="color:#fff;text-decoration:none;" href="/">← Back</a>
  </div>
</body></html>
    """
    return render_template_string(html, css=MODERN_CSS, plan_html=plan_html, error=error, goal=goal)



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route("/debug")
def debug():
    try:
        debug_spotify_setup()
    except Exception:
        pass
    html = """
<!doctype html><html><head>
    <title>🔧 Diagnostics</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    {{ css|safe }}
</head><body>
    <div class="container">
        <div class="hero">
            <h1>🔧 Diagnostics</h1>
        </div>
        <div class="glass-card">
            <div class="status-badge {{ 'status-success' if working else 'status-error' }}">
                {{ '✅ Spotify Working' if working else '❌ Spotify Failed' }}
            </div>
            <p style="color:#fff;opacity:.9;margin-top:.6rem;">See terminal for detailed logs.</p>
        </div>
        <a style="color:#fff;text-decoration:none;" href="/">← Back</a>
    </div>
</body></html>
    """
    return render_template_string(html, css=MODERN_CSS, working=bool(sp))



def format_workout_to_html(raw_text: str) -> str:
    """Format workout text into HTML sections"""
    if not raw_text:
        return "<p>No plan generated.</p>"

    txt = raw_text.replace("\\n", "\n")
    for mark in ("**", "__", "*"):
        txt = txt.replace(mark, "")

    lines = [l.strip(" •-\t") for l in txt.split("\n") if l.strip()]
    if not lines:
        return "<p>No plan generated.</p>"

    sections = {
        "🔥 Warm-up": [],
        "💪 Main Workout": [],
        "🧘 Cool-down": []
    }
    current = "💪 Main Workout"

    for l in lines:
        low = l.lower()
        if "warm" in low and "up" in low:
            current = "🔥 Warm-up"
            continue
        if any(k in low for k in ("cool", "down", "recovery", "stretch")):
            current = "🧘 Cool-down"
            continue
        if "main workout" in low and "cool" not in low:
            current = "💪 Main Workout"
            continue
        sections[current].append(l)

    if not any(sections[s] for s in sections):
        items = "\n".join(f"<li>{l}</li>" for l in lines)
        return f"<ul>{items}</ul>"

    html = []
    for title, items in sections.items():
        if not items: 
            continue
        html.append('<div class="workout-section">')
        html.append(f"<h3>{title}</h3>")
        html.append("<ul>")
        for it in items:
            html.append(f"<li>{it}</li>")
        html.append("</ul></div>")
    return "\n".join(html)



@app.route("/workout-v2", methods=["GET", "POST"])
@login_required
def workout_page_v2():
    plan_html, error = None, None


    form_values = {
        "mood": "",
        "difficulty": "medium",      
        "time": "30",
        "options": ["cardio"]        
    }

    if request.method == "POST":
        mood = request.form.get("mood", "").strip()
        difficulty = request.form.get("difficulty", "medium").strip()
        time_val = request.form.get("time", "30").strip()
        options_list = request.form.getlist("option") 
        option_str = ", ".join(options_list) if options_list else ""

        
        form_values = {
            "mood": mood,
            "difficulty": difficulty,
            "time": time_val,
            "options": options_list
        }

        try:
            prompt = (
                f"Call the workout tool with mood='{mood}', difficulty='{difficulty}', "
                f"option='{option_str}', time={int(time_val)}. "
                f"Then return a ONE-DAY plan with 3 sections (Warm-up, Main Workout, Cool-down). "
                f"Main Workout must list exact exercises with sets×reps or minutes and rest. "
                f"Cover ONLY styles the user selected: {option_str}. "
                f"Keep it teen-safe and include brief form cues."
            )
            resp = work.run(prompt)
            text = extract_text(resp)
            plan_html = format_workout_to_html(text)
        except Exception as e:
            error = f"🛠️ Error generating workout: {e}"

    html = """
    <!doctype html><html><head>
      <title>💪 Fitness Architect v2 - Zenith</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
      {{ css|safe }}
    </head><body><div class="container">
      <div class="hero"><h1>💪 Fitness Architect</h1><p>Personalized one-day plan with exact sets, reps, and rest.</p></div>

      <div class="form-container">
        <form method="POST">
          <div class="form-group">
            <label>🎭 Mood <span style="opacity:.7;font-weight:600;">(optional)</span></label>
            <input type="text" name="mood" class="form-control" placeholder="motivated, calm, stressed…" value="{{ form_values['mood'] }}">
          </div>

          <div class="form-group">
            <label>📈 Difficulty</label>
            <select name="difficulty" class="form-control">
              <option value="easy"   {% if form_values['difficulty']=='easy' %}selected{% endif %}>🟢 Easy</option>
              <option value="medium" {% if form_values['difficulty']=='medium' %}selected{% endif %}>🟡 Medium</option>
              <option value="hard"   {% if form_values['difficulty']=='hard' %}selected{% endif %}>🔴 Hard</option>
            </select>
          </div>

          <div class="form-group">
            <label>🏷️ Style (choose one or more)</label>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.6rem;">
              <label style="color:#fff;"><input type="checkbox" name="option" value="cardio"       {% if 'cardio' in form_values['options'] %}checked{% endif %}> 🏃 Cardio</label>
              <label style="color:#fff;"><input type="checkbox" name="option" value="weight lifting" {% if 'weight lifting' in form_values['options'] %}checked{% endif %}> 🏋️ Weight Lifting</label>
              <label style="color:#fff;"><input type="checkbox" name="option" value="calisthenics" {% if 'calisthenics' in form_values['options'] %}checked{% endif %}> 🤸 Calisthenics</label>
              <label style="color:#fff;"><input type="checkbox" name="option" value="meditation"   {% if 'meditation' in form_values['options'] %}checked{% endif %}> 🧘 Meditation</label>
            </div>
          </div>

          <div class="form-group">
            <label>⏱️ Duration (minutes)</label>
            <input type="number" min="10" max="120" step="5" name="time" class="form-control" value="{{ form_values['time'] }}">
          </div>

          <button class="btn btn-secondary" type="submit">🚀 Generate Workout</button>
        </form>
      </div>

      {% if error %}<div class="error-card"><strong>{{ error }}</strong></div>{% endif %}

      {% if plan_html %}
        <div class="glass-card">
          <h2 style="color:#fff;text-align:center;margin-bottom:1rem;">📋 Your One-Day Plan</h2>
          <div class="workout-plan">{{ plan_html|safe }}</div>
        </div>
      {% endif %}

      <a style="color:#fff;text-decoration:none;" href="/">← Return to Zenith Hub</a>
    </div></body></html>
    """
    return render_template_string(html, css=MODERN_CSS, plan_html=plan_html, error=error, form_values=form_values)
if __name__ == "__main__":
    print("✨ Zenith Wellness Platform Starting...")
    print("🏠 Home: http://127.0.0.1:5000")
    print("🔐 Login: http://127.0.0.1:5000/login")
    print("📝 Signup: http://127.0.0.1:5000/signup")
    print("🎵 Music: http://127.0.0.1:5000/music (login required)")
    print("💪 Workout: http://127.0.0.1:5000/workout (login required)")
    print("🏃 Posture: http://127.0.0.1:5000/posture (login required)")
    print("🧠 Wellbeing: http://127.0.0.1:5000/wellbeing (login required)")
    print("✅ Daily Task: http://127.0.0.1:5000/daily (login required)")
    print("🥗 Diet: http://127.0.0.1:5000/diet (login required)")
    app.run(debug=True, port=5000)

