from app import db
from flask_login import UserMixin
from datetime import datetime
import base64
import os
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    yetki = db.Column(db.Integer, default=0)  # 0=normal user, 1=admin
    is_aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Şifreyi hash'le ve kaydet"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Şifreyi kontrol et"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        """Admin kontrolü (backward compatibility için)"""
        return self.yetki == 1
    
    @property
    def is_active(self):
        """Flask-Login için gerekli - aktif kullanıcı kontrolü"""
        return self.is_aktif
    
    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Login bilgileri - şifreli saklanır
    login_username = db.Column(db.String(300))  # Encrypted
    login_password = db.Column(db.String(300))  # Encrypted 
    login_enabled = db.Column(db.Boolean, default=False)  # Login gerekli mi?
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    test_prompts = db.relationship('TestPrompt', backref='project', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def _get_encryption_key():
        """Şifreleme anahtarını al veya oluştur"""
        key_file = 'instance/encryption.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Yeni anahtar oluştur
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def set_login_credentials(self, username, password):
        """Login bilgilerini şifreli olarak sakla"""
        if not username and not password:
            self.login_username = None
            self.login_password = None
            self.login_enabled = False
            return
            
        key = self._get_encryption_key()
        fernet = Fernet(key)
        
        if username:
            self.login_username = fernet.encrypt(username.encode()).decode()
        if password:
            self.login_password = fernet.encrypt(password.encode()).decode()
        
        self.login_enabled = True
    
    def get_login_credentials(self):
        """Login bilgilerini çöz ve döndür"""
        if not self.login_enabled or not self.login_username or not self.login_password:
            return None
            
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            
            username = fernet.decrypt(self.login_username.encode()).decode()
            password = fernet.decrypt(self.login_password.encode()).decode()
            
            return {'username': username, 'password': password}
        except Exception:
            return None
    
    def __repr__(self):
        return f'<Project {self.name}>'

class TestPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TestPrompt {self.name}>'

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    prompt_id = db.Column(db.Integer, db.ForeignKey('test_prompt.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='running')  # running, completed, failed, stopped
    project_url = db.Column(db.String(500))  # Test edilecek web sitesinin URL'si
    result_text = db.Column(db.Text)
    error_message = db.Column(db.Text)
    running_details = db.Column(db.Text)  # Gerçek zamanlı test adımları JSON formatında
    stop_requested = db.Column(db.Boolean, default=False)  # Test durdurma talebi
    current_step = db.Column(db.Integer, default=0)  # Mevcut adım sayısı
    total_steps = db.Column(db.Integer, default=0)  # Toplam adım sayısı
    execution_time = db.Column(db.Float)  # Test süresi (saniye)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    project = db.relationship('Project', backref='test_results')
    prompt = db.relationship('TestPrompt', backref='test_results')
    user = db.relationship('User', backref='test_results')
    
    def __repr__(self):
        return f'<TestResult {self.id} - {self.status}>'