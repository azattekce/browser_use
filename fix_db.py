import sqlite3
import os

# Veritabanı dosyasının yolu
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')

print(f"Veritabanı yolu: {db_path}")

try:
    # SQLite bağlantısı
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Mevcut sütunları kontrol et
    cursor.execute("PRAGMA table_info(test_result)")
    columns = [column[1] for column in cursor.fetchall()]
    print(f"Mevcut sütunlar: {columns}")
    
    # Yeni sütunları ekle (eğer yoksa)
    new_columns = [
        "running_details TEXT",
        "stop_requested INTEGER DEFAULT 0",
        "current_step INTEGER DEFAULT 0", 
        "total_steps INTEGER DEFAULT 0"
    ]
    
    for column_def in new_columns:
        column_name = column_def.split()[0]
        if column_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE test_result ADD COLUMN {column_def}")
                print(f"✓ Sütun eklendi: {column_name}")
            except Exception as e:
                print(f"✗ Sütun eklenirken hata ({column_name}): {e}")
        else:
            print(f"→ Sütun zaten mevcut: {column_name}")
    
    conn.commit()
    conn.close()
    
    print("Veritabanı güncelleme tamamlandı!")
    
except Exception as e:
    print(f"Hata: {e}")