from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user, login_user, logout_user
from app import db
from app.models import User, Project, TestPrompt, TestResult
from app.forms import ProjectForm, TestPromptForm, RunTestForm, RunSingleTestForm, LoginForm
import os
import getpass
import threading
import time
import asyncio
import json
import json
from datetime import datetime

# Blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
project_bp = Blueprint('project', __name__)
test_bp = Blueprint('test', __name__)

# Ana sayfa
@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    else:
        return redirect(url_for('auth.login'))

# Dashboard
@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Kullanıcının proje sayısı
    total_projects = Project.query.filter_by(user_id=current_user.id).count()
    
    # Son test sonuçları (5 adet)
    recent_tests = TestResult.query.join(TestPrompt).join(Project).filter(
        Project.user_id == current_user.id
    ).order_by(TestResult.created_at.desc()).limit(5).all()
    
    # Başarılı test sayısı (son 30 gün)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    successful_tests = TestResult.query.join(TestPrompt).join(Project).filter(
        Project.user_id == current_user.id,
        TestResult.status == 'completed',
        TestResult.created_at >= thirty_days_ago
    ).count()
    
    # Çalışan test sayısı
    running_tests = TestResult.query.join(TestPrompt).join(Project).filter(
        Project.user_id == current_user.id,
        TestResult.status == 'running'
    ).count()
    
    return render_template('dashboard.html', 
                         total_projects=total_projects,
                         recent_tests=recent_tests,
                         successful_tests=successful_tests,
                         running_tests=running_tests)

# Giriş
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    import os
    form = LoginForm()
    
    if form.validate_on_submit():
        # Kullanıcı adını al (Windows'dan veya environment'dan)
        windows_username = os.getenv('USERNAME') or os.getenv('USER') or os.getenv('DOCKER_USER') or 'docker_user'
        if not windows_username:
            flash('Kullanıcı adı alınamadı!', 'error')
            return render_template('auth/login.html', form=form)
        
        # Kullanıcıyı bul veya oluştur
        user = User.query.filter_by(username=windows_username).first()
        
        if not user:
            # Yeni kullanıcı oluştur
            user = User(username=windows_username)
            # Admin kullanıcısını belirle (isteğe bağlı)
            if windows_username.lower() in ['administrator', 'admin']:
                user.is_admin = True
            db.session.add(user)
            db.session.commit()
            flash(f'Kullanıcı {windows_username} ile yeni hesap oluşturuldu!', 'success')
        
        login_user(user)
        flash(f'Kullanıcı {windows_username} olarak giriş yapıldı!', 'success')
        return redirect(url_for('main.dashboard'))
    
    # GET request için kullanıcı adını al
    windows_username = os.getenv('USERNAME') or os.getenv('USER') or os.getenv('DOCKER_USER') or 'docker_user'
    return render_template('auth/login.html', form=form, windows_user=windows_username)

# Çıkış
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# Proje listesi
@project_bp.route('/projects')
@login_required
def list_projects():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('projects/list.html', projects=projects)

# Yeni proje
@project_bp.route('/project/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            url=form.url.data,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(project)
        db.session.commit()
        flash('Proje başarıyla oluşturuldu!', 'success')
        return redirect(url_for('project.list_projects'))
    
    return render_template('projects/add.html', form=form)

# Proje detayı
@project_bp.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        flash('Bu projeyi görme yetkiniz yok!', 'error')
        return redirect(url_for('project.list_projects'))
    
    prompts = TestPrompt.query.filter_by(project_id=project_id).all()
    return render_template('projects/prompts.html', project=project, prompts=prompts)

# Proje düzenleme
@project_bp.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        flash('Bu projeyi düzenleme yetkiniz yok!', 'error')
        return redirect(url_for('project.list_projects'))
    
    form = ProjectForm(obj=project)
    
    if form.validate_on_submit():
        project.name = form.name.data
        project.url = form.url.data
        project.description = form.description.data
        db.session.commit()
        flash('Proje başarıyla güncellendi!', 'success')
        return redirect(url_for('project.project_detail', project_id=project.id))
    
    return render_template('projects/edit.html', form=form, project=project)

# Proje silme
@project_bp.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        flash('Bu projeyi silme yetkiniz yok!', 'error')
        return redirect(url_for('project.list_projects'))
    
    # İlişkili prompt'ları ve test sonuçlarını sil
    prompts = TestPrompt.query.filter_by(project_id=project_id).all()
    for prompt in prompts:
        TestResult.query.filter_by(prompt_id=prompt.id).delete()
    TestPrompt.query.filter_by(project_id=project_id).delete()
    
    db.session.delete(project)
    db.session.commit()
    flash('Proje başarıyla silindi!', 'success')
    return redirect(url_for('project.list_projects'))

# Test prompt'u oluşturma
@test_bp.route('/project/<int:project_id>/prompt/new', methods=['GET', 'POST'])
@login_required
def new_test_prompt(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        flash('Bu projeye test ekleme yetkiniz yok!', 'error')
        return redirect(url_for('project.list_projects'))
    
    form = TestPromptForm()
    
    if form.validate_on_submit():
        prompt = TestPrompt(
            name=form.name.data,
            content=form.content.data,
            project_id=project_id
        )
        db.session.add(prompt)
        db.session.commit()
        flash('Test promptu başarıyla oluşturuldu!', 'success')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    return render_template('projects/add_prompt.html', form=form, project=project)

# Test prompt'u düzenleme
@test_bp.route('/prompt/<int:prompt_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_test_prompt(prompt_id):
    prompt = TestPrompt.query.get_or_404(prompt_id)
    project = Project.query.get_or_404(prompt.project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        flash('Bu test promptunu düzenleme yetkiniz yok!', 'error')
        return redirect(url_for('project.list_projects'))
    
    form = TestPromptForm(obj=prompt)
    
    if form.validate_on_submit():
        prompt.name = form.name.data
        prompt.content = form.content.data
        db.session.commit()
        flash('Test promptu başarıyla güncellendi!', 'success')
        return redirect(url_for('project.project_detail', project_id=prompt.project_id))
    
    return render_template('projects/edit_prompt.html', form=form, project=project, prompt=prompt)

# Test prompt'u silme
@test_bp.route('/prompt/<int:prompt_id>/delete', methods=['POST'])
@login_required
def delete_test_prompt(prompt_id):
    prompt = TestPrompt.query.get_or_404(prompt_id)
    project = Project.query.get_or_404(prompt.project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        flash('Bu test promptunu silme yetkiniz yok!', 'error')
        return redirect(url_for('project.list_projects'))
    
    # İlişkili test sonuçlarını sil
    TestResult.query.filter_by(prompt_id=prompt_id).delete()
    
    db.session.delete(prompt)
    db.session.commit()
    flash('Test promptu başarıyla silindi!', 'success')
    return redirect(url_for('project.project_detail', project_id=project.id))

# Test çalıştırma sayfası
@test_bp.route('/prompt/<int:prompt_id>/run', methods=['GET', 'POST'])
@login_required
def run_test(prompt_id):
    prompt = TestPrompt.query.get_or_404(prompt_id)
    project = Project.query.get_or_404(prompt.project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        flash('Bu testi çalıştırma yetkiniz yok!', 'error')
        return redirect(url_for('project.list_projects'))
    
    form = RunSingleTestForm()
    
    if form.validate_on_submit():
        # Yeni test sonucu oluştur
        test_result = TestResult(
            project_id=project.id,
            prompt_id=prompt_id,
            user_id=current_user.id,
            status='pending',
            project_url=form.project_url.data
        )
        db.session.add(test_result)
        db.session.commit()
        
        # Arka planda test çalıştır
        thread = threading.Thread(
            target=run_browser_test_async,
            args=(current_app._get_current_object(), test_result.id, form.project_url.data, prompt.content),
            daemon=True
        )
        thread.start()
        
        flash('Test başlatıldı! Sonuçları takip edebilirsiniz.', 'success')
        return redirect(url_for('test.test_result', test_result_id=test_result.id))
    
    # Son test sonuçlarını getir
    recent_results = TestResult.query.filter_by(prompt_id=prompt_id).order_by(TestResult.created_at.desc()).limit(5).all()
    
    return render_template('tests/run_single_test.html', form=form, prompt=prompt, project=project, recent_results=recent_results)

# Test sonucu sayfası
@test_bp.route('/result/<int:test_result_id>')
@login_required
def test_result(test_result_id):
    test_result = TestResult.query.get_or_404(test_result_id)
    prompt = TestPrompt.query.get_or_404(test_result.prompt_id)
    project = Project.query.get_or_404(prompt.project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        flash('Bu test sonucunu görme yetkiniz yok!', 'error')
        return redirect(url_for('project.list_projects'))
    
    return render_template('tests/result.html', test_result=test_result, prompt=prompt, project=project)

# Test silme endpoint
@test_bp.route('/result/<int:test_result_id>/delete', methods=['POST'])
@login_required
def delete_test_result(test_result_id):
    """Test sonucunu sil"""
    test_result = TestResult.query.get_or_404(test_result_id)
    prompt = TestPrompt.query.get_or_404(test_result.prompt_id)
    project = Project.query.get_or_404(prompt.project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Bu testi silme yetkiniz yok!'}), 403
    
    # Çalışan testi silmeye izin verme
    if test_result.status == 'running':
        return jsonify({'success': False, 'message': 'Çalışan test silinemez! Önce testi durdurun.'}), 400
    
    try:
        # Test sonucunu sil
        db.session.delete(test_result)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Test başarıyla silindi.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Test silinirken hata oluştu: {str(e)}'}), 500

# Test tekrar çalıştırma endpoint
@test_bp.route('/result/<int:test_result_id>/rerun', methods=['POST'])
@login_required
def rerun_test(test_result_id):
    """Mevcut test ile aynı parametreleri kullanarak yeni bir test çalıştır"""
    original_test = TestResult.query.get_or_404(test_result_id)
    prompt = TestPrompt.query.get_or_404(original_test.prompt_id)
    project = Project.query.get_or_404(prompt.project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Bu testi tekrar çalıştırma yetkiniz yok!'}), 403
    
    # Çalışan testi tekrar çalıştırmaya izin verme
    if original_test.status == 'running':
        return jsonify({'success': False, 'message': 'Test hala çalışıyor! Önce mevcut testi bekleyin veya durdurun.'}), 400
    
    try:
        # Yeni test sonucu oluştur - tüm zorunlu alanları doldur
        new_test = TestResult(
            project_id=project.id,
            prompt_id=prompt.id,
            user_id=current_user.id,
            status='running',
            project_url=project.url,
            current_step=0,
            total_steps=0
        )
        db.session.add(new_test)
        db.session.commit()
        
        # Arka planda testi başlat
        thread = threading.Thread(
            target=run_browser_test_async,
            args=(current_app._get_current_object(), new_test.id, project.url, prompt.content),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'Test başarıyla tekrar başlatıldı!',
            'new_test_id': new_test.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Test tekrar çalıştırılırken hata oluştu: {str(e)}'}), 500

# Test sonucu API (AJAX için)
@test_bp.route('/api/result/<int:test_result_id>')
@login_required
def api_test_result(test_result_id):
    test_result = TestResult.query.get_or_404(test_result_id)
    prompt = TestPrompt.query.get_or_404(test_result.prompt_id)
    project = Project.query.get_or_404(prompt.project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Running details'i parse et
    running_details = []
    if test_result.running_details:
        try:
            running_details = json.loads(test_result.running_details)
        except json.JSONDecodeError:
            running_details = []
    
    return jsonify({
        'id': test_result.id,
        'status': test_result.status,
        'current_step': test_result.current_step,
        'total_steps': test_result.total_steps,
        'running_details': running_details,
        'result_text': test_result.result_text,
        'error_message': test_result.error_message,
        'created_at': test_result.created_at.isoformat() if test_result.created_at else None,
        'completed_at': test_result.completed_at.isoformat() if test_result.completed_at else None,
        'stop_requested': test_result.stop_requested
    })

# Test durdurma
@test_bp.route('/api/result/<int:test_result_id>/stop', methods=['POST'])
@login_required
def api_stop_test(test_result_id):
    test_result = TestResult.query.get_or_404(test_result_id)
    prompt = TestPrompt.query.get_or_404(test_result.prompt_id)
    project = Project.query.get_or_404(prompt.project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Sadece çalışan testleri durdur
    if test_result.status in ['pending', 'running']:
        test_result.stop_requested = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Test durdurma talebi gönderildi'})
    else:
        return jsonify({'error': 'Test zaten tamamlanmış veya durdurulmuş'}), 400

def run_browser_test_async(app, test_result_id, project_url, prompt_content):
    """Arka planda browser test çalıştır - GERÇEK BROWSER AUTOMATION"""
    import json
    test_logs = []
    
    def log_step(message):
        """Test adımını veritabanına kaydet"""
        timestamp = datetime.utcnow().strftime('%H:%M:%S')
        log_entry = {'timestamp': timestamp, 'message': message}
        test_logs.append(log_entry)
        
        # Veritabanını güncelle
        try:
            with app.app_context():
                test_result = TestResult.query.get(test_result_id)
                if test_result:
                    test_result.running_details = json.dumps(test_logs)
                    test_result.current_step = len(test_logs)
                    db.session.commit()
        except Exception as e:
            print(f"Log kaydetme hatası: {e}")
        
        print(f"[{timestamp}] {message}")
    
    def check_stop_requested():
        """Durdurma talebi var mı kontrol et"""
        try:
            with app.app_context():
                test_result = TestResult.query.get(test_result_id)
                return test_result and test_result.stop_requested
        except Exception as e:
            print(f"Durdurma kontrolü hatası: {e}")
            return False
    
    try:
        from browser_use import Agent
        import os
        from dotenv import load_dotenv
        
        # .env dosyasını yükle
        load_dotenv()
        
        log_step("🚀 Test başlatılıyor...")
        log_step("⚠️ GERÇEK BROWSER AÇILACAK VE OTOMASYON YAPILACAK!")
        
        # Güvenli tür dönüşümü için helper fonksiyon
        def safe_int(value, default):
            try:
                return int(value) if value else default
            except (ValueError, TypeError):
                return default
        
        # Prompt içeriğini URL ile değiştir ve daha net hale getir
        # F-string içinde backslash kullanılamadığı için değişkenleri önceden hazırlıyoruz
        url_placeholder = "Belirtilen URL'yi ziyaret et: {url}"
        cleaned_content = prompt_content.replace(url_placeholder, '').replace('1. adım:', 'Adım 1:').replace('2. adım:', 'Adım 2:')
        
        formatted_prompt = f"""
Öncelikle şu web sitesini ziyaret et: {project_url}

Sonra aşağıdaki adımları takip et:

{cleaned_content}
"""
        
        log_step(f"🌐 Hedef URL: {project_url}")
        log_step("📋 Formatted prompt ilk 300 karakter:")
        log_step(formatted_prompt[:300] + "...")
        
        # Test sonucunu güncelle
        with app.app_context():
            test_result = TestResult.query.get(test_result_id)
            test_result.status = 'running'
            test_result.total_steps = safe_int(os.getenv('MAX_STEPS'), 100)
            db.session.commit()
        
        # Konfigürasyon değerleri
        
        config = {
            'max_steps': safe_int(os.getenv('MAX_STEPS'), 100),
            'headless': os.getenv('HEADLESS', 'False').lower() == 'true',
            'window_width': safe_int(os.getenv('WINDOW_WIDTH'), 1920),
            'window_height': safe_int(os.getenv('WINDOW_HEIGHT'), 1080),
            'implicit_wait': safe_int(os.getenv('IMPLICIT_WAIT'), 5),
            'explicit_wait': safe_int(os.getenv('EXPLICIT_WAIT'), 10),
            'llm_provider': os.getenv('LLM_PROVIDER', 'gemini'),
            'llm_model': os.getenv('LLM_MODEL', 'gemini-flash-latest'),
            'api_key': os.getenv('OPENAI_API_KEY'),
            'gemini_api_key': os.getenv('GEMINI_API_KEY'),
        }
        
        log_step(f"🤖 LLM Provider: {config['llm_provider']} ({config['llm_model']})")
        log_step(f"📊 Max Steps: {config['max_steps']} (Type: {type(config['max_steps'])})")
        log_step(f"👁️ Headless Mode: {config['headless']}")
        log_step(f"🖥️ Window Size: {config['window_width']}x{config['window_height']}")
        
        # LLM konfigürasyonunu dinamik olarak oluştur
        def get_llm_config(config):
            provider = config['llm_provider'].lower()
            model = config['llm_model']
            
            if provider == 'openai':
                if not config['api_key']:
                    log_step("⚠️ OPENAI_API_KEY bulunamadı, Browser-Use default kullanılacak")
                    return None
                return {
                    "provider": "openai",
                    "api_key": config['api_key'],
                    "model": model
                }
            elif provider == 'gemini':
                if not config['gemini_api_key']:
                    log_step("⚠️ GEMINI_API_KEY bulunamadı, Browser-Use default Gemini kullanılacak")
                    return None
                return {
                    "provider": "gemini",
                    "api_key": config['gemini_api_key'],
                    "model": model
                }
            elif provider == 'anthropic':
                anthropic_key = os.getenv('ANTHROPIC_API_KEY')
                if not anthropic_key:
                    log_step("⚠️ ANTHROPIC_API_KEY bulunamadı, Browser-Use default kullanılacak")
                    return None
                return {
                    "provider": "anthropic", 
                    "api_key": anthropic_key,
                    "model": model
                }
            else:
                log_step(f"⚠️ Bilinmeyen provider '{provider}', Browser-Use default kullanılacak")
                return None
        
        # Browser config - FORCED VISIBLE MODE
        browser_config = {
            "headless": False,  # Zorla görünür mod
            "window_size": (config['window_width'], config['window_height']),
            "page_load_strategy": "eager",
            "implicit_wait": config['implicit_wait'],
            "explicit_wait": config['explicit_wait'],
            "disable_images": False,
            "disable_javascript": False,
            "chrome_options": [
                "--start-maximized",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ]
        }
        
        log_step(f"⚙️ Browser Config: {browser_config}")
        
        # LLM konfigürasyonunu al
        llm_config = get_llm_config(config)
        
        log_step("🔧 Browser agent yapılandırılıyor...")
        
        # Max steps değerini garantili integer yap
        max_steps_int = int(config['max_steps']) if isinstance(config['max_steps'], (str, int)) else 100
        log_step(f"🔢 Final max_steps: {max_steps_int} (Type: {type(max_steps_int)})")
        
        # Dinamik LLM konfigürasyonu ile Agent oluştur
        if llm_config:
            log_step(f"✅ Kullanılan LLM: {llm_config['provider']} - {llm_config['model']}")
            agent = Agent(
                task=formatted_prompt,
                llm_config=llm_config,
                max_steps=max_steps_int,
                use_vision=True,
                save_conversation_history=False,
                browser_config=browser_config
            )
        else:
            log_step("🔧 Browser-Use default LLM kullanılıyor (Gemini Flash Latest)")
            agent = Agent(
                task=formatted_prompt,
                max_steps=max_steps_int,
                use_vision=True,
                save_conversation_history=False,
                browser_config=browser_config
            )
        
        log_step("🌐 Browser açılıyor ve test başlatılıyor...")
        log_step("🤖 Browser-use AI Agent devreye giriyor...")
        
        # GERÇEK BROWSER AUTOMATION - Browser açılacak ve otomatik test yapılacak!
        log_step("🚀 GERÇEK BROWSER AUTOMATION BAŞLIYOR - Browser açılıyor...")
        log_step(f"⚠️ Bu aşamada tarayıcı penceresi açılacak! Headless: {config['headless']}")
        log_step(f"🌐 Ziyaret edilecek URL: {project_url}")
        log_step("📋 Agent task preview:")
        log_step(formatted_prompt[:200] + "...")
        
        # Gerçek browser automation çalıştır
        # Browser-use async çağrısı
        log_step("🚀 Agent async çağrısı yapılıyor... BROWSER AÇILIYOR!")
        
        import asyncio
        log_step("⏱️ Browser açılması bekleniyor...")
        
        # Async fonksiyonu sync olarak çalıştır
        try:
            result = asyncio.run(agent.run())
        except Exception as async_error:
            log_step(f"⚠️ Async hatası: {async_error}")
            # Alternatif sync metod dene
            result = agent.run_sync() if hasattr(agent, 'run_sync') else None
        
        log_step("🏁 Agent çağrısı tamamlandı!")
        
        log_step("✅ Browser automation tamamlandı!")
        log_step(f"📊 Test sonucu: {str(result)[:300] if result else 'Başarıyla tamamlandı'}")
        
        # Sonucu kaydet
        with app.app_context():
            test_result = TestResult.query.get(test_result_id)
            test_result.status = 'completed'
            test_result.result_text = str(result) if result else 'Test completed successfully'
            test_result.completed_at = datetime.utcnow()
            db.session.commit()
    
    except Exception as e:
        log_step(f"❌ Test hatası: {str(e)}")
        print(f"Detaylı hata: {e}")
        
        # Hata durumunu kaydet
        with app.app_context():
            test_result = TestResult.query.get(test_result_id)
            test_result.status = 'failed'
            test_result.error_message = str(e)
            test_result.completed_at = datetime.utcnow()
            db.session.commit()

# Test Çalıştır Sayfası
@test_bp.route('/run', methods=['GET', 'POST'])
@login_required
def run_tests():
    """Test çalıştırma ana sayfası"""
    form = RunTestForm()
    
    # Kullanıcının projelerini al
    projects = Project.query.filter_by(user_id=current_user.id).all()
    
    # Form için proje seçeneklerini doldur (tüm projeler)
    form.project_id.choices = [(0, 'Proje seçin...')] + [(p.id, p.name) for p in projects]
    form.prompt_id.choices = [(0, 'Önce proje seçin...')]
    
    # POST işleminde seçilen proje varsa prompt'ları da yükle
    if request.method == 'POST' and form.project_id.data and form.project_id.data != 0:
        project = Project.query.get(form.project_id.data)
        if project and project.user_id == current_user.id:
            prompts = TestPrompt.query.filter_by(project_id=project.id).all()
            form.prompt_id.choices = [(0, 'Prompt seçin...')] + [(p.id, p.name) for p in prompts]
    
    if request.method == 'POST':
        # Manuel form validation (WTF validation bypass)
        project_id = request.form.get('project_id', type=int)
        prompt_id = request.form.get('prompt_id', type=int)
        
        # Debug bilgisi
        print(f"Form submitted - Project ID: {project_id}, Prompt ID: {prompt_id}")
        
        if project_id and project_id != 0 and prompt_id and prompt_id != 0:
            # Seçilen prompt'un gerçekten kullanıcının projesinde olduğunu kontrol et
            prompt = TestPrompt.query.filter_by(id=prompt_id, project_id=project_id).first()
            if prompt and prompt.project.user_id == current_user.id:
                # Test çalıştır sayfasına yönlendir
                return redirect(url_for('test.run_test', prompt_id=prompt_id))
            else:
                flash('Seçilen prompt bulunamadı veya yetkiniz yok.', 'error')
        else:
            flash('Lütfen proje ve prompt seçin.', 'error')
            
        # POST sonrası form değerlerini koru
        if project_id and project_id != 0:
            form.project_id.data = project_id
            # Seçilen proje için prompt'ları yükle
            project = Project.query.get(project_id)
            if project and project.user_id == current_user.id:
                prompts = TestPrompt.query.filter_by(project_id=project.id).all()
                form.prompt_id.choices = [(0, 'Prompt seçin...')] + [(p.id, p.name) for p in prompts]
                if prompt_id and prompt_id != 0:
                    form.prompt_id.data = prompt_id
    
    # Debug bilgisi
    print(f"Kullanıcı {current_user.username} - Toplam proje sayısı: {len(projects)}")
    for project in projects:
        print(f"Proje: {project.name} - Prompt sayısı: {len(project.test_prompts)}")
    
    # Test prompt'u olan projeleri filtrele
    projects_with_prompts = []
    for project in projects:
        if project.test_prompts:
            projects_with_prompts.append(project)
    
    return render_template('tests/run_test.html', form=form, projects=projects, projects_with_prompts=projects_with_prompts)

# Test Geçmişi Sayfası
@test_bp.route('/history')
@login_required
def test_history():
    """Test geçmişi sayfası"""
    # Kullanıcının test sonuçlarını al (en son 50 test)
    test_results = TestResult.query.join(TestPrompt).join(Project).filter(
        Project.user_id == current_user.id
    ).order_by(TestResult.created_at.desc()).limit(50).all()
    
    return render_template('tests/history.html', test_results=test_results)

# AJAX endpoint - Proje için prompt'ları getir
@test_bp.route('/api/project/<int:project_id>/prompts')
@login_required
def get_prompts(project_id):
    """Belirtilen proje için prompt'ları JSON olarak döndür"""
    project = Project.query.get_or_404(project_id)
    
    # Kullanıcı yetkisi kontrolü
    if project.user_id != current_user.id:
        return jsonify({'error': 'Yetkisiz erişim'}), 403
    
    prompts = TestPrompt.query.filter_by(project_id=project_id).all()
    
    prompts_data = [
        {
            'id': prompt.id,
            'name': prompt.name,
            'content': prompt.content[:100] + '...' if len(prompt.content) > 100 else prompt.content
        }
        for prompt in prompts
    ]
    
    return jsonify(prompts_data)