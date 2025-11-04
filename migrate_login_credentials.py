#!/usr/bin/env python3

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        print('Adding login credential columns to Project table...')
        
        # Add login credential fields to Project table
        db.session.execute(text('ALTER TABLE project ADD COLUMN login_enabled BOOLEAN DEFAULT 0'))
        db.session.execute(text('ALTER TABLE project ADD COLUMN login_username VARCHAR(255)'))
        db.session.execute(text('ALTER TABLE project ADD COLUMN login_password TEXT'))
        
        db.session.commit()
        print('Login credential columns added successfully!')
        print('- login_enabled: BOOLEAN (default: false)')
        print('- login_username: VARCHAR(255)')
        print('- login_password: TEXT (encrypted)')
        
    except Exception as e:
        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
            print('Login credential columns already exist, skipping...')
        else:
            print(f'Error updating database: {e}')
            db.session.rollback()
            raise e