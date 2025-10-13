from app import create_app, db
from app.models import User, Project, TestPrompt, TestResult
import os

# Flask uygulamasını oluştur
app = create_app()

with app.app_context():
    # Mevcut veritabanını sil ve yeniden oluştur
    db.drop_all()
    db.create_all()
    
    # Default admin kullanıcısını oluştur
    import getpass
    username = getpass.getuser()
    
    admin_user = User.query.filter_by(username=username).first()
    if not admin_user:
        admin_user = User(username=username, is_admin=True)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin kullanıcı oluşturuldu: {username}")
    else:
        print(f"Admin kullanıcı zaten mevcut: {username}")
    
    print("Veritabanı yeniden oluşturuldu!")