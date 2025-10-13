from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    test_prompts = db.relationship('TestPrompt', backref='project', lazy=True, cascade='all, delete-orphan')
    
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