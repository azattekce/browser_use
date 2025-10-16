import sys
import os
sys.path.append('.')

from app.routes import parse_agent_history
import sqlite3

def test_with_real_data():
    conn = sqlite3.connect('instance/browser_test.db')
    cursor = conn.cursor()
    
    # En son tamamlanan testi al
    cursor.execute('''
        SELECT id, result_text
        FROM test_result 
        WHERE status = 'completed' AND result_text IS NOT NULL
        ORDER BY created_at DESC 
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    if result:
        test_id, result_text = result
        print(f"Test ID: {test_id}")
        print(f"Result text length: {len(result_text)}")
        
        # Parse et
        steps = parse_agent_history(result_text)
        
        print(f"\nToplam {len(steps)} adım bulundu:")
        print("=" * 60)
        
        for i, step in enumerate(steps, 1):
            print(f"{i:2d}. {step['action_type']}")
            if step['details'].get('extracted_content'):
                content = step['details']['extracted_content']
                if len(content) > 80:
                    content = content[:77] + "..."
                print(f"    İçerik: {content}")
            
            if step['details'].get('success') is not None:
                success_icon = "✅" if step['details']['success'] else "❌"
                print(f"    Durum: {success_icon}")
            
            if step['details'].get('is_done'):
                print(f"    🏁 Tamamlandı")
            print()
    else:
        print("Hiç test sonucu bulunamadı!")
    
    conn.close()

if __name__ == '__main__':
    test_with_real_data()