from flask import Flask, render_template

from flask_cors import CORS
from models import db, User
from config import Config
from werkzeug.security import generate_password_hash
import sys
import os
import webbrowser
from threading import Timer

# Support PyInstaller frozen paths
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.abspath(os.path.dirname(__file__))

template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config.from_object(Config)
CORS(app)

db.init_app(app)

from flask_login import LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.login_page'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Ensure upload directory exists (Ignore on read-only environments like Vercel)
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except:
    pass

with app.app_context():
    try:
        db.create_all()
        # Create default admin if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin122'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
    except:
        pass

# Import routes after app initialization to avoid circular imports
from routes import main_bp
app.register_blueprint(main_bp)

try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

from threading import Thread

def start_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Start Flask in a background thread
    t = Thread(target=start_flask)
    t.daemon = True
    t.start()

    # Only start desktop window if we are on a PC and not on a server
    if HAS_WEBVIEW and getattr(sys, 'frozen', False):
        webview.create_window('Boshkash Academy', 'http://127.0.0.1:5000', width=1280, height=800)
        webview.start()
    else:
        # If on server or running via python directly, just keep the main thread alive
        import time
        while True:
            time.sleep(1)
