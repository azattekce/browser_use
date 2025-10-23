from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///browser_test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    # csrf.init_app(app)  # Geçici olarak kapatıldı
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Lütfen giriş yapın.'
    login_manager.login_message_category = 'info'
    
    # Template context processor for CSRF token
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    
    # Register blueprints
    from app.routes import main_bp, auth_bp, project_bp, test_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(project_bp, url_prefix='/projects')
    app.register_blueprint(test_bp, url_prefix='/tests')
    
    # Create database tables
    with app.app_context():
        # Ensure database directory exists for Azure File Share mount
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                print(f"Created database directory: {db_dir}")
        
        db.create_all()
        
        # Create default admin user
        from app.models import User
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_user = User(
                username='admin',
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created!")
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))