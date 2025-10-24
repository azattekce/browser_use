#!/usr/bin/env python3
from app import create_app
from app.models import Project, User
from app import db

app = create_app()

with app.app_context():
    print("=== Database Debug Info ===")
    
    # Kullanıcıları listele
    users = User.query.all()
    print(f"\nKullanıcılar ({len(users)}):")
    for user in users:
        print(f"- ID: {user.id}, Username: {user.username}, Email: {user.email}")
    
    # Projeleri listele
    projects = Project.query.all()
    print(f"\nProjeler ({len(projects)}):")
    for project in projects:
        print(f"- ID: {project.id}, Name: {project.name}, User_ID: {project.user_id}")
        try:
            print(f"  Owner: {project.owner.username}")
        except Exception as e:
            print(f"  Owner ERROR: {e}")
    
    # JOIN ile kontrol
    print("\nJOIN Kontrolü:")
    try:
        joined_projects = Project.query.join(User).all()
        print(f"JOIN başarılı: {len(joined_projects)} proje")
        for p in joined_projects:
            print(f"- {p.name} -> {p.owner.username}")
    except Exception as e:
        print(f"JOIN ERROR: {e}")