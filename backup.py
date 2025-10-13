import time
import os
from browser_use import Agent, ChatOpenAI
from dotenv import load_dotenv

# .env dosyasından konfigürasyonları yükle
load_dotenv()

def load_task_prompt(prompt_file_path):
    """Task prompt dosyasını okur ve URL ile birleştirir"""
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            prompt_template = file.read()
        url = os.getenv('URL', 'https://joker-test.opetcloud.net/')
        return prompt_template.format(url=url)
    except FileNotFoundError:
        print(f"HATA: {prompt_file_path} dosyası bulunamadı!")
        return None
    except Exception as e:
        print(f"Task prompt okuma hatası: {e}")
        return None

def load_config():
    """Konfigürasyon değerlerini .env dosyasından yükler"""
    return {
        'url': os.getenv('URL', 'https://joker-test.opetcloud.net/'),
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),  # OpenAI modeli (vision destekli)
        'max_steps': int(os.getenv('MAX_STEPS', 100)),
        'test_interval': int(os.getenv('TEST_INTERVAL_MINUTES', 5)),
        'headless': os.getenv('HEADLESS', 'False').lower() == 'true',
        'window_width': int(os.getenv('WINDOW_WIDTH', 1920)),
        'window_height': int(os.getenv('WINDOW_HEIGHT', 1080)),
        'implicit_wait': int(os.getenv('IMPLICIT_WAIT', 5)),
        'explicit_wait': int(os.getenv('EXPLICIT_WAIT', 10)),
        'use_vision': os.getenv('USE_VISION', 'True').lower() == 'true',
        'save_history': os.getenv('SAVE_CONVERSATION_HISTORY', 'False').lower() == 'true',
    }

# Konfigürasyonu yükle
config = load_config()

# Task description'ı dosyadan oku
current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_file = os.path.join(current_dir, 'task_prompt.txt')
task_description = load_task_prompt(prompt_file)

if not task_description:
    print("Task prompt yüklenemedi. Program sonlandırılıyor...")
    raise SystemExit(1)

if not config['api_key']:
    print("OPENAI_API_KEY bulunamadı. .env dosyasını kontrol edin.")
    raise SystemExit(1)

# OpenAI LLM'i hazırla (yalnızca OpenAI)
llm = ChatOpenAI(
    model=config['model'],
    api_key=config['api_key'],
)

# AI ajanını oluştur
print(f"Hedef URL: {config['url']}")
print(f"Max Steps: {config['max_steps']}")
print(f"Test Interval: {config['test_interval']} dakika")
print(f"Kullanılan OpenAI modeli: {config['model']}")
# Dilerseniz bu satırı güvenlik için kaldırın:
print(f"API Key ilk 20 karakter: {config['api_key'][:20]}...")

agent = Agent(
    task=task_description,
    llm=llm,  # ← yalnızca OpenAI
    max_steps=config['max_steps'],
    use_vision=config['use_vision'],           # Görsel tanıma (modeliniz desteklemeli)
    save_conversation_history=config['save_history'],
    browser_config={
        "headless": config['headless'],
        "window_size": (config['window_width'], config['window_height']),
        "page_load_strategy": "eager",
        "implicit_wait": config['implicit_wait'],
        "explicit_wait": config['explicit_wait'],
        "disable_images": False,
        "disable_javascript": False,
    },
)

# Sürekli döngü ile siteyi kontrol et
while True:
    try:
        result = agent.run_sync()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Site durumu: {result}")
    except Exception as e:
        print(f"Hata oluştu: {e}")
    print(f"Test tamamlandı. {config['test_interval']} dakika sonra tekrar başlatılacak...")
    time.sleep(config['test_interval'] * 60)
