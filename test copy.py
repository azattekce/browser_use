import time
import os
from browser_use import Agent
from dotenv import load_dotenv

# .env dosyasından konfigürasyonları yükle
load_dotenv()

def load_task_prompt(prompt_file_path):
    """Task prompt dosyasını okur ve URL ile birleştirir"""
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            prompt_template = file.read()
        
        # URL'yi .env dosyasından al
        url = os.getenv('URL')
        
        # Template'i URL ile doldur
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
        'url': os.getenv('URL'),
        'api_key': os.getenv('OPENAI_API_KEY'),
        'gemini_api_key': os.getenv('GEMINI_API_KEY'),
        'max_steps': int(os.getenv('MAX_STEPS', 100)),
        'test_interval': int(os.getenv('TEST_INTERVAL_MINUTES', 5)),
        'headless': os.getenv('HEADLESS', 'False').lower() == 'true',
        'window_width': int(os.getenv('WINDOW_WIDTH', 1920)),
        'window_height': int(os.getenv('WINDOW_HEIGHT', 1080)),
        'implicit_wait': int(os.getenv('IMPLICIT_WAIT', 5)),
        'explicit_wait': int(os.getenv('EXPLICIT_WAIT', 10)),
        # LLM Configuration
        'llm_provider': os.getenv('LLM_PROVIDER', 'gemini'),
        'llm_model': os.getenv('LLM_MODEL', 'gemini-flash-latest')
    }

def get_llm_config(config):
    """LLM provider'a göre dinamik konfigürasyon oluşturur"""
    provider = config['llm_provider'].lower()
    model = config['llm_model']
    
    if provider == 'openai':
        if not config['api_key']:
            raise ValueError("OpenAI kullanımı için OPENAI_API_KEY gerekli!")
        return {
            "provider": "openai",
            "api_key": config['api_key'],
            "model": model
        }
    elif provider == 'gemini':
        if not config['gemini_api_key']:
            print("UYARI: GEMINI_API_KEY bulunamadı, Browser-Use default Gemini kullanılacak")
            return None  # Browser-Use default'unu kullan
        return {
            "provider": "gemini",
            "api_key": config['gemini_api_key'],
            "model": model
        }
    elif provider == 'anthropic':
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_key:
            raise ValueError("Anthropic kullanımı için ANTHROPIC_API_KEY gerekli!")
        return {
            "provider": "anthropic", 
            "api_key": anthropic_key,
            "model": model
        }
    else:
        print(f"UYARI: Bilinmeyen provider '{provider}', Browser-Use default kullanılacak")
        return None

# Konfigürasyonu yükle
config = load_config()

# Task description'ı dosyadan oku (tam yol ile)
current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_file = os.path.join(current_dir, 'task_prompt.txt')
task_description = load_task_prompt(prompt_file)

if not task_description:
    print("Task prompt yüklenemedi. Program sonlandırılıyor...")
    exit(1)

# LLM konfigürasyonunu dinamik olarak oluştur
try:
    llm_config = get_llm_config(config)
except ValueError as e:
    print(f"LLM Konfigürasyon Hatası: {e}")
    exit(1)

# AI ajanını dinamik konfigürasyon ile oluştur
print(f"Hedef URL: {config['url']}")
print(f"Max Steps: {config['max_steps']}")
print(f"Test Interval: {config['test_interval']} dakika")
print(f"LLM Provider: {config['llm_provider']}")
print(f"LLM Model: {config['llm_model']}")

# Dinamik LLM konfigürasyonu ile Agent oluştur
browser_config = {
    "headless": config['headless'],
    "window_size": (config['window_width'], config['window_height']),
    "page_load_strategy": "eager",  # Sayfa yüklemeyi hızlandır
    "implicit_wait": config['implicit_wait'],
    "explicit_wait": config['explicit_wait'],
    "disable_images": False,  # Görselleri devre dışı bırak (hız için)
    "disable_javascript": False  # JS'i devre dışı bırakma (site çalışmaz)
}

if llm_config:
    print(f"Kullanılan LLM: {llm_config['provider']} - {llm_config['model']}")
    agent = Agent(
        task=task_description,
        llm_config=llm_config,
        max_steps=config['max_steps'],
        use_vision=True,
        save_conversation_history=False,
        browser_config=browser_config
    )
else:
    print("Browser-Use default LLM kullanılıyor (Gemini Flash Latest)")
    agent = Agent(
        task=task_description,
        max_steps=config['max_steps'],
        use_vision=True,
        save_conversation_history=False,
        browser_config=browser_config
    )

# Sürekli döngü ile siteyi kontrol et
while True:
    try:
        # AI ajanını çalıştır ve sonucu al
        result = agent.run_sync()  # ❌ artık parametre yok
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Site durumu: {result}")
    except Exception as e:
        print(f"Hata oluştu: {e}")
    
    print(f"Test tamamlandı. {config['test_interval']} dakika sonra tekrar başlatılacak...")
    
    # Konfigürasyondan gelen bekleme süresi
    time.sleep(config['test_interval'] * 60)  # dakikayı saniyeye çevir
