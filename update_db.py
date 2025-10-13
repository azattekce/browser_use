#!/usr/bin/env python3

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Yeni sütunları ekle
        db.session.execute(text('ALTER TABLE test_result ADD COLUMN running_details TEXT'))
        db.session.execute(text('ALTER TABLE test_result ADD COLUMN stop_requested BOOLEAN DEFAULT 0'))
        db.session.execute(text('ALTER TABLE test_result ADD COLUMN current_step INTEGER DEFAULT 0'))
        db.session.execute(text('ALTER TABLE test_result ADD COLUMN total_steps INTEGER DEFAULT 0'))
        db.session.commit()
        print('Database updated successfully!')
    except Exception as e:
        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
            print('Columns already exist, skipping...')
        else:
            print(f'Error updating database: {e}')
            db.session.rollback()