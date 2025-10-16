import sys
import os
sys.path.append('.')

from app.routes import parse_agent_history

# Test verisini yükle
with open('check_result_detail.py', 'r') as f:
    content = f.read()

# Test result text'i yakala
test_result_text = """AgentHistoryList(all_results=[ActionResult(is_done=False, success=None, error=None, attachments=None, long_term_memory='Found initial url and automatically loaded it. Navigated to https://joker-test.opetcloud.net/', extracted_content='🔗 Navigated to https://joker-test.opetcloud.net/', include_extracted_content_only_once=False, metadata=None, include_in_memory=False), ActionResult(is_done=False, success=None, error=None, attachments=None, long_term_memory='Data written to file todo.md successfully.', extracted_content='Data written to file todo.md successfully.', include_extracted_content_only_once=False, metadata=None, include_in_memory=False), ActionResult(is_done=False, success=None, error=None, attachments=None, long_term_memory='Waited for 3 seconds', extracted_content='Waited for 3 seconds', include_extracted_content_only_once=False, metadata=None, include_in_memory=False), ActionResult(is_done=False, success=None, error=None, attachments=None, long_term_memory="Input 'jokercloudtstusr@opetonline.onmicrosoft.com' into element 1.", extracted_content="Input 'jokercloudtstusr@opetonline.onmicrosoft.com' into element 1.", include_extracted_content_only_once=False, metadata={'input_x': 954.6217651367188, 'input_y': 257.2636329318436}, include_in_memory=False), ActionResult(is_done=False, success=None, error=None, attachments=None, long_term_memory=None, extracted_content='Clicked element', include_extracted_content_only_once=False, metadata={'click_x': 1076.63330078125, 'click_y': 389.2646789550781, 'new_tab_opened': False}, include_in_memory=False), ActionResult(is_done=True, success=True, error=None, attachments=[], long_term_memory='Task completed: True - Belirtilen web sitesine başarıyla giriş yapıldı. (Successfully logged into the specified website.)', extracted_content='Belirtilen web sitesine başarıyla giriş yapıldı. (Successfully logged into the specified website.)', include_extracted_content_only_once=False, metadata=None, include_in_memory=False)]"""

# Parse et
steps = parse_agent_history(test_result_text)

print(f"Toplam {len(steps)} adım bulundu:")
print()

for i, step in enumerate(steps[:10], 1):  # İlk 10 adımı göster
    print(f"=== ADIM {i} ===")
    print(f"Tip: {step['action_type']}")
    print(f"İçerik: {step['details'].get('extracted_content', '')}")
    print(f"Hafıza: {step['details'].get('long_term_memory', '')}")
    print(f"Başarı: {step['details'].get('success', 'Bilinmiyor')}")
    print(f"Tamamlandı: {step['details'].get('is_done', False)}")
    print()