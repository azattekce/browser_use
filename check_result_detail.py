import sqlite3
import json

def check_test_result_detail(test_id):
    conn = sqlite3.connect('instance/browser_test.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, status, result_text, running_details
        FROM test_result 
        WHERE id = ?
    ''', (test_id,))
    
    result = cursor.fetchone()
    if result:
        print(f'Test ID: {result[0]}')
        print(f'Status: {result[1]}')
        print(f'Result Text Length: {len(result[2]) if result[2] else 0}')
        print(f'Running Details Length: {len(result[3]) if result[3] else 0}')
        
        print('\n=== RESULT TEXT ===')
        if result[2]:
            print(result[2])
        else:
            print('No result text')
            
        print('\n=== RUNNING DETAILS ===')
        if result[3]:
            print(result[3])
        else:
            print('No running details')
    else:
        print('Test not found')
    
    conn.close()

if __name__ == '__main__':
    # En son tamamlanan testi kontrol et
    check_test_result_detail(24)