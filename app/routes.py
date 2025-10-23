from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, render_template_string
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
import re
from datetime import datetime

def is_running_in_docker():
    """Uygulamanın Docker container içinde çalışıp çalışmadığını kontrol eder"""
    try:
        # Environment variable kontrolü (en güvenilir - Azure Container Apps için)
        if os.getenv('RUNNING_IN_DOCKER') == 'true':
            return True
            
        # Azure Container Apps kontrolü
        if os.getenv('AZURE_CONTAINER_APP') == 'true':
            return True
            
        # .dockerenv dosyası kontrol et
        if os.path.exists('/.dockerenv'):
            return True
            
        # cgroup kontrol et (fallback)
        if os.path.exists('/proc/1/cgroup'):
            with open('/proc/1/cgroup', 'r') as f:
                content = f.read()
                return 'docker' in content or 'containerd' in content
        return False
    except:
        return False

def mask_sensitive_data(text):
    """Hassas verileri (şifreler, kredi kartı numaraları vb.) maskeler"""
    if not text or not isinstance(text, str):
        return text
    
    # Şifre maskeleme - yaygın şifre pattern'ları
    password_patterns = [
        # Bilinen şifreler - önce bunları maskele
        (r"Baracuda\.11", "B******11"),
        (r"baracuda\.11", "b******11"),
        # Password alanına girilen veriler
        (r"Input '(Baracuda\.11)' into element", r"Input 'B******11' into element"),
        (r'Input "(Baracuda\.11)" into element', r'Input "B******11" into element'),
        # Email değil ama şifre pattern'ı olan veriler
        (r"Input '([^'@]{6,})' into element (\d+)", lambda m: f"Input '{mask_if_password(m.group(1))}' into element {m.group(2)}"),
        (r'Input "([^"@]{6,})" into element (\d+)', lambda m: f'Input "{mask_if_password(m.group(1))}" into element {m.group(2)}'),
        # Dosya içeriklerinde şifre maskeleme
        (r'"([^"@]{6,})"', lambda m: f'"{mask_if_password(m.group(1))}"'),
        (r"'([^'@]{6,})'", lambda m: f"'{mask_if_password(m.group(1))}'"),
    ]
    
    masked_text = text
    for pattern, replacement in password_patterns:
        if callable(replacement):
            masked_text = re.sub(pattern, replacement, masked_text, flags=re.IGNORECASE)
        else:
            masked_text = re.sub(pattern, replacement, masked_text, flags=re.IGNORECASE)
    
    return masked_text

def is_likely_password(text):
    """Metinin şifre olma ihtimalini kontrol eder"""
    if not text or len(text) < 6:
        return False
    
    # Şifre benzeri pattern'lar
    password_indicators = [
        r"[A-Z].*[a-z].*\d",  # Büyük harf, küçük harf, rakam
        r".*[!@#$%^&*()_+\-=\[\]{}|;':\",./<>?].*",  # Özel karakter
        r"^[A-Za-z]\w*\.\d+$",  # Word.Number formatı (Baracuda.11 gibi)
    ]
    
    for pattern in password_indicators:
        if re.search(pattern, text):
            return True
    
    return False

def mask_if_password(text):
    """Şifre ise maskeler, değilse olduğu gibi döner"""
    if is_likely_password(text):
        return mask_password(text)
    return text

def mask_password(password):
    """Şifreyi maskeler"""
    if len(password) <= 3:
        return "*" * len(password)
    elif len(password) <= 8:
        return password[0] + "*" * (len(password) - 2) + password[-1]
    else:
        return password[:2] + "*" * (len(password) - 4) + password[-2:]

# Test sonuçlarını işleme fonksiyonları
def parse_agent_history(agent_history_text):
    """Agent history'sini adım adım parse eder"""
    if not agent_history_text:
        return []
    
    # AgentHistoryList yapısını kontrol et
    if 'AgentHistoryList' in agent_history_text and 'ActionResult' in agent_history_text:
        return parse_browser_use_results(agent_history_text)
    
    # Eski format için fallback
    return parse_legacy_format(agent_history_text)

def parse_browser_use_results(agent_history_text):
    """Browser-use AgentHistoryList yapısını parse eder"""
    steps = []
    step_counter = 1
    
    # ActionResult'ları daha detaylı yakala
    # Nested parantezleri de hesaba katarak parse et
    action_results = []
    start = 0
    while True:
        action_start = agent_history_text.find('ActionResult(', start)
        if action_start == -1:
            break
            
        # Parantezleri sayarak bitiş noktasını bul
        paren_count = 1
        pos = action_start + len('ActionResult(')
        while pos < len(agent_history_text) and paren_count > 0:
            if agent_history_text[pos] == '(':
                paren_count += 1
            elif agent_history_text[pos] == ')':
                paren_count -= 1
            pos += 1
        
        if paren_count == 0:
            action_result = agent_history_text[action_start:pos]
            action_results.append(action_result)
        
        start = pos
    
    for action_result in action_results:
        # is_done kontrolü
        is_done = 'is_done=True' in action_result
        success = None
        if 'success=True' in action_result:
            success = True
        elif 'success=False' in action_result:
            success = False
            
        # extracted_content yakala (daha güçlü regex)
        extracted_content = ""
        extracted_patterns = [
            r"extracted_content='([^']*)'",
            r'extracted_content="([^"]*)"',
            r"extracted_content=([^,)]*)"
        ]
        for pattern in extracted_patterns:
            extracted_match = re.search(pattern, action_result)
            if extracted_match:
                extracted_content = extracted_match.group(1).strip('"\'')
                break
        
        # long_term_memory yakala (daha güçlü regex)
        memory = ""
        memory_patterns = [
            r"long_term_memory='([^']*)'",
            r'long_term_memory="([^"]*)"',
            r"long_term_memory=([^,)]*)"
        ]
        for pattern in memory_patterns:
            memory_match = re.search(pattern, action_result)
            if memory_match:
                memory = memory_match.group(1).strip('"\'')
                break
        
        # Action type belirle
        action_type = "Browser İşlemi"
        content_to_check = (extracted_content + " " + memory).lower()
        
        if is_done and success:
            action_type = "✅ Test Tamamlandı"
        elif is_done:
            action_type = "🏁 İşlem Tamamlandı"
        elif 'navigated' in content_to_check or 'navigate' in content_to_check:
            action_type = "🌐 Sayfa Yükleme"
        elif 'input' in content_to_check and 'element' in content_to_check:
            action_type = "⌨️ Veri Girişi"
        elif 'clicked' in content_to_check or 'click' in content_to_check:
            action_type = "🖱️ Tıklama"
        elif 'waited' in content_to_check or 'wait' in content_to_check:
            action_type = "⏳ Bekleme"
        elif 'file' in content_to_check and ('written' in content_to_check or 'replaced' in content_to_check):
            action_type = "📄 Dosya İşlemi"
        elif memory and not extracted_content:
            action_type = "🧠 Hafıza Güncellemesi"
        
        # İçeriği temizle, şifreleri maskele ve kısalt
        display_content = extracted_content or memory
        display_content = mask_sensitive_data(display_content)
        if len(display_content) > 150:
            display_content = display_content[:147] + "..."
        
        steps.append({
            'step_number': step_counter,
            'action_type': action_type,
            'details': {
                'extracted_content': display_content,
                'long_term_memory': mask_sensitive_data(memory[:200]) if memory else "",
                'success': success,
                'is_done': is_done,
                'content': display_content
            },
            'raw_content': mask_sensitive_data(action_result[:500])  # Ham içeriği maskele ve kısalt
        })
        step_counter += 1
    
    return steps[:50]  # İlk 50 adımı al

def parse_legacy_format(agent_history_text):
    """Eski format için fallback parser"""
    steps = []
    
    # Agent log pattern'larını yakala
    patterns = {
        'step': r'📍 Step (\d+):',
        'action_result': r'ActionResult\(([^)]+)\)',
        'memory': r'🧠 Memory: (.+?)(?=\n|$)',
        'done': r'▶️\s+done: text: (.+?)(?=\n|$)',
        'final_result': r'📄\s+Final Result:\s*(.+?)(?=\n|$)'
    }
    
    step_counter = 1
    current_step = None
    
    # Satır satır işle
    lines = agent_history_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Step başlangıcını yakala
        step_match = re.search(patterns['step'], line)
        if step_match:
            step_number = int(step_match.group(1))
            current_step = {
                'step_number': step_number,
                'action_type': f'Adım {step_number}',
                'details': {'content': line},
                'raw_content': line
            }
            steps.append(current_step)
            continue
            
        # Memory yakala
        memory_match = re.search(patterns['memory'], line)
        if memory_match:
            memory_content = memory_match.group(1).strip()
            steps.append({
                'step_number': step_counter,
                'action_type': 'Agent Hafızası',
                'details': {
                    'long_term_memory': memory_content,
                    'success': True
                },
                'raw_content': line
            })
            step_counter += 1
            continue
            
        # Done result yakala
        done_match = re.search(patterns['done'], line)
        if done_match:
            done_content = done_match.group(1).strip()
            # success kontrolü
            success = 'success=True' in done_content or 'başarılı' in done_content.lower()
            steps.append({
                'step_number': step_counter,
                'action_type': 'Adım Sonucu',
                'details': {
                    'extracted_content': done_content,
                    'success': success,
                    'is_done': True
                },
                'raw_content': line
            })
            step_counter += 1
            continue
            
        # Final result yakala
        final_match = re.search(patterns['final_result'], line)
        if final_match:
            final_content = final_match.group(1).strip()
            steps.append({
                'step_number': step_counter,
                'action_type': 'Son Sonuç',
                'details': {
                    'extracted_content': final_content,
                    'success': 'başarısız' not in final_content.lower() and 'hata' not in final_content.lower(),
                    'is_done': True
                },
                'raw_content': line
            })
            step_counter += 1
            continue
        
        # ActionResult yakala
        action_match = re.search(patterns['action_result'], line)
        if action_match:
            params = {}
            match_content = action_match.group(1)
            
            # Parametreleri parse et
            if 'is_done=True' in match_content:
                params['is_done'] = True
            elif 'is_done=False' in match_content:
                params['is_done'] = False
                
            if 'success=True' in match_content:
                params['success'] = True
            elif 'success=False' in match_content:
                params['success'] = False
            
            # extracted_content yakala
            content_match = re.search(r"extracted_content='([^']*)'", match_content)
            if content_match:
                params['extracted_content'] = content_match.group(1)
            
            # long_term_memory yakala  
            memory_match = re.search(r'long_term_memory="([^"]*)"', match_content)
            if memory_match:
                params['long_term_memory'] = memory_match.group(1)
                
            steps.append({
                'step_number': step_counter,
                'action_type': 'Eylem Sonucu',
                'details': params,
                'raw_content': line[:200] + '...' if len(line) > 200 else line
            })
            step_counter += 1
            continue
        
        # Genel log satırları
        if any(word in line.lower() for word in ['info', 'error', 'warning', 'debug']):
            steps.append({
                'step_number': step_counter,
                'action_type': 'Log',
                'details': {'content': line},
                'raw_content': line
            })
            step_counter += 1
    
    return steps[:20]  # İlk 20 adımı al

def format_test_result(test_result):
    """Test sonucunu formatla"""
    if not test_result.result_text:
        return "Test henüz tamamlanmadı veya sonuç yok."
    
    # JSON olarak parse etmeye çalış
    try:
        if isinstance(test_result.result_text, str):
            result_data = json.loads(test_result.result_text)
        else:
            result_data = test_result.result_text
        
        if 'agent_history' in result_data:
            return parse_agent_history(result_data['agent_history'])
        else:
            return [{'step_number': 1, 'action_type': 'Result', 'details': result_data, 'raw_content': str(result_data)}]
    except (json.JSONDecodeError, TypeError):
        # String olarak işle
        return parse_agent_history(test_result.result_text)

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
        
        # Handle login credentials if enabled
        if form.login_enabled.data:
            project.set_login_credentials(
                username=form.login_username.data,
                password=form.login_password.data
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
    
    # Populate login credentials if they exist
    if project.login_enabled:
        login_data = project.get_login_credentials()
        if login_data:
            form.login_enabled.data = True
            form.login_username.data = login_data.get('username', '')
            # Don't populate password for security
    
    if form.validate_on_submit():
        project.name = form.name.data
        project.url = form.url.data
        project.description = form.description.data
        
        # Handle login credentials
        if form.login_enabled.data:
            # Only update password if a new one is provided
            if form.login_password.data and form.login_password.data.strip():
                project.set_login_credentials(
                    username=form.login_username.data,
                    password=form.login_password.data
                )
            else:
                # Update only username, keep existing password
                project.login_enabled = True
                project.login_username = form.login_username.data
        else:
            # Clear login credentials if disabled
            project.login_enabled = False
            project.login_username = None
            project.login_password = None
        
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
    
    # Test sonuçlarını formatla
    formatted_steps = format_test_result(test_result)
    
    # Docker tespiti
    docker_running = is_running_in_docker()
    
    return render_template('tests/result.html', 
                         test_result=test_result, 
                         prompt=prompt, 
                         project=project,
                         formatted_steps=formatted_steps,
                         docker_running=docker_running)

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
        
        # Get project login credentials if available
        login_instructions = ""
        with app.app_context():
            test_result = TestResult.query.get(test_result_id)
            if test_result and test_result.prompt and test_result.prompt.project:
                project = test_result.prompt.project
                if project.login_enabled:
                    login_data = project.get_login_credentials()
                    if login_data:
                        username = login_data.get('username', '')
                        password = login_data.get('password', '')
                        if username and password:
                            login_instructions = f"""

ÖNEMLI - Otomatik Giriş Bilgileri:
Bu proje için otomatik giriş etkin. Eğer test sırasında giriş yapman gerekirse aşağıdaki bilgileri kullan:
- Kullanıcı adı: {username}
- Şifre: {password}

Test sırasında "giriş yap", "login ol", "sign in" gibi talepler karşılaştığında bu bilgileri otomatik olarak kullan.
"""
                            log_step(f"🔐 Otomatik giriş etkin - Kullanıcı: {username}")
        
        # Prompt içeriğini URL ile değiştir ve daha net hale getir
        # F-string içinde backslash kullanılamadığı için değişkenleri önceden hazırlıyoruz
        url_placeholder = "Belirtilen URL'yi ziyaret et: {url}"
        cleaned_content = prompt_content.replace(url_placeholder, '').replace('1. adım:', 'Adım 1:').replace('2. adım:', 'Adım 2:')
        
        formatted_prompt = f"""
Öncelikle şu web sitesini ziyaret et: {project_url}
{login_instructions}
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
        
        # Docker container'da mı çalışıyoruz kontrol et
        is_docker = os.getenv('DOCKER_USER') is not None
        
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
        log_step(f"👁️ Headless Mode: {config['headless']} (Docker: {is_docker})")
        log_step(f"🖥️ Window Size: {config['window_width']}x{config['window_height']}")
        log_step(f"🐳 Environment: {'Docker Container' if is_docker else 'Local Development'}")
        
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
        
        # Browser config - Docker destekli
        # Headless modunu Docker durumuna göre ayarla
        # Docker'da VNC ile görüntülenebilir olsun
        use_headless = False if is_docker else config['headless']
        
        # Microsoft sitesi için özel strateji - ÖNCE TANIMLA
        is_microsoft_site = "microsoft" in project_url.lower() or "login.microsoftonline" in project_url.lower()
        log_step(f"🔍 Microsoft site check: {is_microsoft_site} for URL: {project_url}")
        
        # Anti-bot tespiti için Chrome seçenekleri
        base_chrome_options = [
            "--no-sandbox",
            "--disable-dev-shm-usage", 
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
            "--disable-extensions-file-access-check",
            "--disable-extensions-except",
            "--disable-plugins-discovery",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor,TranslateUI",
            "--disable-ipc-flooding-protection",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "--exclude-switches=enable-automation",
            "--disable-blink-features=AutomationControlled",
            "--useAutomationExtension=false",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--disable-translate",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI,BlinkGenPropertyTrees",
            "--disable-component-extensions-with-background-pages",
            "--no-default-browser-check",
            "--mute-audio"
        ]
        
        # Chrome prefs (anti-detection)
        chrome_prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 1,
            "profile.password_manager_enabled": False,
            "credentials_enable_service": False,
            "profile.password_manager_leak_detection": False,
            "autofill.profile_enabled": False,
            "autofill.credit_card_enabled": False,
            "profile.default_content_setting_values.geolocation": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.media_stream_mic": 2,
            # Microsoft bypass için ek prefs
            "webrtc.ip_handling_policy": "disable_non_proxied_udp",
            "webrtc.multiple_routes_enabled": False,
            "webrtc.nonproxied_udp_enabled": False,
            "enable_do_not_track": False,
            "plugins.always_open_pdf_externally": False,
            "profile.managed_default_content_settings.javascript": 1
        }

        browser_config = {
            "headless": use_headless,
            "window_size": (config['window_width'], config['window_height']),
            "page_load_strategy": "eager",
            "implicit_wait": 15 if is_microsoft_site else config['implicit_wait'],
            "explicit_wait": 30 if is_microsoft_site else config['explicit_wait'],
            "disable_images": False,
            "disable_javascript": False,
            "chrome_options": base_chrome_options,
            "chrome_prefs": chrome_prefs,
            "chrome_experimental_options": {
                "useAutomationExtension": False,
                "excludeSwitches": ["enable-automation"],
                "prefs": chrome_prefs
            }
        }
        
        # Docker'da ek Chrome seçenekleri ekle
        if is_docker:
            browser_config["chrome_options"].extend([
                "--disable-setuid-sandbox",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--remote-debugging-port=0",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                # Güçlü Microsoft bypass için anti-bot seçenekleri
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
                "--disable-blink-features=AutomationControlled",
                "--exclude-switches=enable-automation",
                "--disable-extensions",
                "--disable-plugins-discovery",
                "--disable-component-extensions-with-background-pages", 
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI,BlinkGenPropertyTrees",
                "--disable-ipc-flooding-protection",
                "--enable-features=NetworkService,NetworkServiceInProcess",
                "--force-color-profile=srgb",
                "--metrics-recording-only",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-pings",
                "--password-store=basic",
                "--use-mock-keychain",
                "--lang=tr-TR,tr,en-US,en",
                "--disable-client-side-phishing-detection",
                "--disable-component-extensions-with-background-pages",
                # Ek stealth seçenekleri
                "--disable-plugins-discovery",
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor,TranslateUI,BlinkGenPropertyTrees",
                "--disable-background-networking",
                "--disable-field-trial-config",
                "--disable-ipc-flooding-protection",
                "--disable-hang-monitor",
                "--disable-prompt-on-repost",
                "--disable-domain-reliability",
                "--disable-component-update",
                "--autoplay-policy=user-gesture-required",
                "--disable-background-mode",
                "--mute-audio",
                "--no-default-browser-check"
            ])
        else:
            # Yerel çalıştırmada maximize et
            browser_config["chrome_options"].extend([
                "--start-maximized",
                "--remote-debugging-port=0"
            ])
        
        log_step(f"⚙️ Browser Config: {browser_config}")
        
        # LLM konfigürasyonunu al
        llm_config = get_llm_config(config)
        
        log_step("🔧 Browser agent yapılandırılıyor...")
        
        # Max steps değerini garantili integer yap
        max_steps_int = int(config['max_steps']) if isinstance(config['max_steps'], (str, int)) else 100
        log_step(f"🔢 Final max_steps: {max_steps_int} (Type: {type(max_steps_int)})")
        
        # Microsoft sitesi için özel strateji uygulanması
        if is_microsoft_site:
            log_step("🔐 Microsoft sitesi tespit edildi, özel strateji uygulanıyor...")
            
            # Microsoft bypass için JavaScript injection
            browser_config["chrome_options"].append(
                '--user-data-dir=/tmp/chrome_user_data'
            )
            
            # Microsoft için özel prompt
            microsoft_prompt = f"""
IMPORTANT: You are accessing a Microsoft authentication page that may show access restrictions.

STEP 1: First, inject anti-detection JavaScript:
```javascript
Object.defineProperty(navigator, 'webdriver', {{
    get: () => undefined,
}});

Object.defineProperty(navigator, 'languages', {{
    get: () => ['en-US', 'en'],
}});

Object.defineProperty(navigator, 'plugins', {{
    get: () => [1, 2, 3, 4, 5],
}});

window.chrome = {{
    runtime: {{}},
}};

Object.defineProperty(navigator, 'permissions', {{
    get: () => ({{
        query: () => Promise.resolve({{ state: 'granted' }}),
    }}),
}});
```

STEP 2: Wait 3 seconds for JavaScript to load properly.

STEP 3: If you see "You cannot access this right now" message, try:
- Click on "Sign out and sign in with a different account" link
- Wait 5 seconds
- Continue with the authentication flow

URL to visit: {project_url}

Special handling for Microsoft login:
1. Navigate to the URL carefully
2. If you see "You cannot access this right now" message:
   - Look for "Sign out and sign in with a different account" link and click it
   - Or wait 3 seconds and refresh the page once
   - Be patient, don't rush actions
3. Wait for page elements to fully load before interacting
4. When login form appears, proceed with the original task

Original task: {cleaned_content}

Be methodical and wait between actions to avoid triggering security measures.
"""
            formatted_prompt = microsoft_prompt
            # Microsoft siteler için daha yavaş işlem
            max_steps_int = min(max_steps_int + 20, 150)  # Daha fazla adım ver
            log_step(f"🔐 Microsoft için max_steps artırıldı: {max_steps_int}")
        
        # Dinamik LLM konfigürasyonu ile Agent oluştur
        if llm_config:
            log_step(f"✅ Kullanılan LLM: {llm_config['provider']} - {llm_config['model']}")
            try:
                agent = Agent(
                    task=formatted_prompt,
                    llm_config=llm_config,
                    max_steps=max_steps_int,
                    use_vision=True,
                    save_conversation_history=False,
                    browser_config=browser_config
                )
            except Exception as e:
                log_step(f"❌ LLM konfigürasyonu hatası: {e}")
                log_step("� OpenAI default ile deneniyor...")
                # OpenAI default deneme
                try:
                    agent = Agent(
                        task=formatted_prompt,
                        llm_config={"provider": "openai", "model": "gpt-4o"},
                        max_steps=max_steps_int,
                        use_vision=True,
                        save_conversation_history=False,
                        browser_config=browser_config
                    )
                except Exception as e2:
                    log_step(f"❌ OpenAI default da başarısız: {e2}")
                    raise Exception(f"LLM yapılandırması başarısız: {e}")
        else:
            log_step("🔧 API key yok - OpenAI default LLM kullanılıyor")
            try:
                # API key olmadığında OpenAI default deneme
                agent = Agent(
                    task=formatted_prompt,
                    llm_config={"provider": "openai", "model": "gpt-4o"},
                    max_steps=max_steps_int,
                    use_vision=True,
                    save_conversation_history=False,
                    browser_config=browser_config
                )
            except Exception as e:
                log_step(f"❌ OpenAI default başarısız: {e}")
                log_step("🔄 Browser-Use varsayılan yapılandırması deneniyor...")
                # Son çare: sadece temel parametrelerle
                agent = Agent(
                    task=formatted_prompt,
                    max_steps=max_steps_int,
                    browser_config=browser_config
                )
        
        log_step("🌐 Browser açılıyor ve test başlatılıyor...")
        log_step("🤖 Browser-use AI Agent devreye giriyor...")
        log_step("🛡️ Microsoft bot tespitine karşı önlemler aktif!")
        
        # GERÇEK BROWSER AUTOMATION - Browser açılacak ve otomatik test yapılacak!
        log_step("🚀 GERÇEK BROWSER AUTOMATION BAŞLIYOR - Browser açılıyor...")
        log_step(f"⚠️ Bu aşamada tarayıcı penceresi açılacak! Headless: {use_headless}")
        log_step(f"🌐 Ziyaret edilecek URL: {project_url}")
        log_step("📋 Agent task preview:")
        log_step(formatted_prompt[:200] + "...")
        
        # Microsoft siteler için özel talimatlar ekle
        if 'microsoft' in project_url.lower() or 'outlook' in project_url.lower() or 'office' in project_url.lower():
            log_step("🔍 Microsoft sitesi tespit edildi - özel önlemler uygulanıyor...")
            enhanced_prompt = f"""
ÖNEMLI: Bu bir Microsoft sitesi. Bot tespitini engellemek için:
1. Sayfayı yükledikten sonra 3-5 saniye bekle
2. Fare hareketlerini doğal yap, aniden tıklama
3. Eğer 'You cannot access this right now' hatası alırsan, sayfayı yenile ve tekrar dene
4. Giriş yapmaya çalışırken human-like davran
5. CAPTCHA veya güvenlik kontrolü varsa, bunları rapor et

Orijinal görev:
{formatted_prompt}
"""
            formatted_prompt = enhanced_prompt
        
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

# VNC Proxy Endpoints
@main_bp.route('/vnc.html')
def vnc_viewer():
    """VNC viewer sayfası - Tamamen kendi implementasyonumuz"""
    # Kendi VNC viewer'ımızı döndür (noVNC'ye bağımlı değil)
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>VNC Viewer</title>
    <meta charset="utf-8">
    <style>
        body { margin: 0; padding: 20px; font-family: Arial, sans-serif; background: #f0f2f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .error { color: #d32f2f; padding: 15px; background: #ffebee; border: 1px solid #ffcdd2; border-radius: 8px; margin: 15px 0; }
        .info { color: #1976d2; padding: 15px; background: #e3f2fd; border: 1px solid #bbdefb; border-radius: 8px; margin: 15px 0; }
        .controls { margin: 15px 0; }
        .btn { padding: 10px 20px; margin: 0 8px; background: #1976d2; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
        .btn:hover { background: #1565c0; }
        .btn-danger { background: #d32f2f; }
        .btn-danger:hover { background: #c62828; }
        .vnc-area { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        #vnc-canvas { border: 1px solid #ddd; border-radius: 4px; width: 100%; max-width: 1200px; height: 700px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .status.loading { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
        .status.success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .status.error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ Browser VNC Görünümü</h1>
            <div class="info">
                <strong>Bilgi:</strong> Browser automation işlemlerini bu ekranda canlı olarak izleyebilirsiniz.
            </div>
        </div>
        
        <div class="controls">
            <button class="btn" onclick="connectVNC()">� Bağlan</button>
            <button class="btn" onclick="disconnectVNC()">⚡ Bağlantıyı Kes</button>
            <button class="btn" onclick="refreshConnection()">� Yenile</button>
            <button class="btn btn-danger" onclick="window.close()">❌ Kapat</button>
        </div>
        
        <div class="vnc-area">
            <div id="status" class="status loading">VNC bağlantısı kontrol ediliyor...</div>
            <div id="vnc-container">
                <canvas id="vnc-canvas" style="display: none;"></canvas>
                <div id="connection-info" style="display: none;">
                    <p><strong>Bağlantı Bilgileri:</strong></p>
                    <ul>
                        <li>VNC Server: Container internal port 5900</li>
                        <li>Web Proxy: Container internal port 6080</li>
                        <li>Display: :99 (1920x1080)</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="error">
            <strong>VNC Bağlantı Hatası:</strong><br>
            Azure Container Apps ortamında VNC servislerine doğrudan erişim sağlanamadı.<br>
            <br>
            <strong>Geçici Çözüm:</strong><br>
            1. Container logs'larında VNC servislerinin başlayıp başlamadığını kontrol edin<br>
            2. Test işlemlerini başlatın, VNC arka planda çalışacaktır<br>
            3. Test sonuçlarını sayfada görüntüleyebilirsiniz<br>
            <br>
            <strong>Hata Detayı:</strong> {{ error_message }}
        </div>
    </div>

    <script>
        let vncConnected = false;
        let vncWebSocket = null;
        let vncCanvas = null;
        let vncContext = null;
        
        function updateStatus(message, type = 'loading') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
        }
        
        function connectVNC() {
            updateStatus('VNC ekran görüntüsü alınıyor...', 'loading');
            
            // Screenshot tabanlı VNC viewer
            startScreenshotPolling();
        }
        
        function startScreenshotPolling() {
            // Canvas'ı görüntüle
            vncCanvas = document.getElementById('vnc-canvas');
            vncCanvas.style.display = 'block';
            document.getElementById('connection-info').style.display = 'block';
            
            // İlk screenshot'ı al
            updateScreenshot();
            
            // Her 2 saniyede bir yenile
            if (vncConnected) {
                setTimeout(function() {
                    if (vncConnected) {
                        startScreenshotPolling();
                    }
                }, 2000);
            }
        }
        
        function updateScreenshot() {
            fetch('/vnc-screenshot')
                .then(response => {
                    if (response.ok) {
                        return response.blob();
                    } else {
                        throw new Error('Screenshot alınamadı');
                    }
                })
                .then(blob => {
                    const img = new Image();
                    img.onload = function() {
                        const canvas = document.getElementById('vnc-canvas');
                        const ctx = canvas.getContext('2d');
                        
                        // Canvas boyutunu ayarla
                        canvas.width = img.width;
                        canvas.height = img.height;
                        
                        // Resmi çiz
                        ctx.drawImage(img, 0, 0);
                        
                        updateStatus('VNC ekranı güncellendi (' + new Date().toLocaleTimeString() + ')', 'success');
                        vncConnected = true;
                    };
                    img.src = URL.createObjectURL(blob);
                })
                .catch(error => {
                    updateStatus('Screenshot hatası: ' + error.message, 'error');
                    console.error('Screenshot error:', error);
                });
        }
        
        function disconnectVNC() {
            if (vncWebSocket) {
                vncWebSocket.close();
            }
            vncConnected = false;
            updateStatus('VNC bağlantısı kesildi', 'error');
            vncCanvas.style.display = 'none';
            document.getElementById('connection-info').style.display = 'none';
        }
        
        function refreshConnection() {
            if (vncConnected) {
                disconnectVNC();
                setTimeout(connectVNC, 1000);
            } else {
                connectVNC();
            }
        }
        
        // Sayfa yüklendiğinde VNC durumunu kontrol et
        window.onload = function() {
            updateStatus('VNC servisleri kontrol ediliyor...', 'loading');
            
            fetch('/vnc-status')
                .then(response => response.json())
                .then(data => {
                    if (data.available) {
                        updateStatus('VNC servisleri hazır. Bağlanmak için Bağlan butonuna tıklayın.', 'success');
                    } else {
                        updateStatus('VNC servisleri çalışmıyor: ' + (data.error || 'Bilinmeyen hata'), 'error');
                    }
                })
                .catch(error => {
                    updateStatus('VNC status kontrolü başarısız. Manuel bağlantı deneyebilirsiniz.', 'error');
                });
        };
    </script>
</body>
</html>
        ''')

@main_bp.route('/vnc-status')
def vnc_status():
    """VNC servis durumunu kontrol et"""
    try:
        import requests
        import subprocess
        
        # VNC process kontrolü
        try:
            result = subprocess.run(['pgrep', '-f', 'x11vnc'], capture_output=True, text=True, timeout=5)
            vnc_running = len(result.stdout.strip()) > 0
        except:
            vnc_running = False
            
        # noVNC process kontrolü  
        try:
            result = subprocess.run(['pgrep', '-f', 'websockify'], capture_output=True, text=True, timeout=5)
            novnc_running = len(result.stdout.strip()) > 0
        except:
            novnc_running = False
            
        # Port 6080 kontrolü
        try:
            response = requests.get('http://localhost:6080', timeout=2)
            port_accessible = True
        except:
            port_accessible = False
            
        return jsonify({
            'available': vnc_running and novnc_running and port_accessible,
            'vnc_running': vnc_running,
            'novnc_running': novnc_running,
            'port_accessible': port_accessible,
            'error': None if (vnc_running and novnc_running and port_accessible) else 'VNC servisleri çalışmıyor'
        })
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e)
        })

@main_bp.route('/vnc-static/<path:path>')
def vnc_static_proxy(path):
    """VNC static dosyaları proxy"""
    try:
        import requests
        response = requests.get(f'http://localhost:6080/{path}', timeout=5)
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        return response.content, response.status_code, {'Content-Type': content_type}
    except Exception as e:
        return f"Static file error: {str(e)}", 503

@main_bp.route('/vnc-screenshot')
def vnc_screenshot():
    """VNC ekran görüntüsünü al"""
    try:
        import subprocess
        import io
        from flask import send_file
        
        # Xvfb ekranından screenshot al
        result = subprocess.run([
            'import', '-window', 'root', '-display', ':99', 'png:-'
        ], capture_output=True, timeout=10)
        
        if result.returncode == 0:
            # PNG data'yı BytesIO'ya yükle
            img_data = io.BytesIO(result.stdout)
            img_data.seek(0)
            
            return send_file(
                img_data,
                mimetype='image/png',
                as_attachment=False,
                download_name='vnc_screenshot.png'
            )
        else:
            # Fallback: Dummy image
            return create_dummy_screenshot()
            
    except Exception as e:
        print(f"Screenshot error: {e}")
        return create_dummy_screenshot()

def create_dummy_screenshot():
    """Dummy screenshot oluştur"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # 1024x768 boyutunda dummy image
        img = Image.new('RGB', (1024, 768), color='#2c3e50')
        draw = ImageDraw.Draw(img)
        
        # Basit metin ekle
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
        text_lines = [
            "VNC Display Active",
            "Browser automation running...",
            f"Time: {datetime.now().strftime('%H:%M:%S')}",
            "Click 'Yenile' to update view"
        ]
        
        y_pos = 300
        for line in text_lines:
            bbox = draw.textbbox((0, 0), line, font=font) if font else (0, 0, len(line)*8, 20)
            text_width = bbox[2] - bbox[0]
            x_pos = (1024 - text_width) // 2
            draw.text((x_pos, y_pos), line, fill='white', font=font)
            y_pos += 40
        
        # BytesIO'ya kaydet
        img_data = io.BytesIO()
        img.save(img_data, format='PNG')
        img_data.seek(0)
        
        return send_file(
            img_data,
            mimetype='image/png',
            as_attachment=False,
            download_name='dummy_screenshot.png'
        )
    except Exception as e:
        # Son fallback
        return f"Screenshot unavailable: {str(e)}", 503

@main_bp.route('/websockify')
def websockify_proxy():
    """WebSocket proxy endpoint - Info only"""
    return jsonify({
        'info': 'WebSocket proxy endpoint',
        'note': 'Azure Container Apps WebSocket limitations',
        'alternative': 'Use VNC screenshot polling instead'
    })