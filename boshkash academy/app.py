print("Starting Flask App...", flush=True)
from flask import Flask, render_template

from flask_cors import CORS
from models import db, User
from config import Config
from werkzeug.security import generate_password_hash
import os

# Fix for Vercel paths - ensure we look at the project root
base_dir = os.path.abspath(os.path.dirname(__file__))
# If running from 'api' folder (Vercel), go up one level
if os.path.basename(base_dir) == 'api':
    base_dir = os.path.dirname(base_dir)

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
            print("Default admin user created.")
    except Exception as e:
        print(f"DB Error or Read-Only Env: {e}")

# Import routes after app initialization to avoid circular imports
from routes import main_bp
app.register_blueprint(main_bp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
