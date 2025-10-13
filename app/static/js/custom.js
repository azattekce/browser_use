// Custom JavaScript for Browser Test Application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });
    
    // Confirm delete operations
    const deleteButtons = document.querySelectorAll('form[action*="delete"]');
    deleteButtons.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm('Bu işlemi gerçekleştirmek istediğinizden emin misiniz?')) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-refresh running tests
    if (window.location.pathname.includes('/tests/') || window.location.pathname.includes('/history')) {
        const runningElements = document.querySelectorAll('.status-running, .badge.bg-warning');
        if (runningElements.length > 0) {
            // Refresh every 30 seconds if there are running tests
            setTimeout(function() {
                location.reload();
            }, 30000);
        }
    }
    
    // Form validation improvements
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('input[type="submit"], button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + submitButton.textContent;
                
                // Re-enable after 5 seconds to prevent permanent disable on validation errors
                setTimeout(function() {
                    if (submitButton.disabled) {
                        submitButton.disabled = false;
                        submitButton.innerHTML = submitButton.innerHTML.replace('<i class="fas fa-spinner fa-spin"></i> ', '');
                    }
                }, 5000);
            }
        });
    });
});

// Utility functions
function showLoading(element) {
    element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Yükleniyor...';
    element.disabled = true;
}

function hideLoading(element, originalText) {
    element.innerHTML = originalText;
    element.disabled = false;
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('tr-TR');
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return Math.round(seconds) + 's';
    } else if (seconds < 3600) {
        return (seconds / 60).toFixed(1) + 'dk';
    } else {
        return (seconds / 3600).toFixed(1) + 'sa';
    }
}

// Project and prompt management functions
function updatePromptList(projectId) {
    const promptSelect = document.getElementById('prompt-select');
    
    if (!projectId) {
        promptSelect.innerHTML = '<option value="">Önce proje seçin</option>';
        return;
    }
    
    showLoading(promptSelect);
    
    fetch(`/tests/get_prompts/${projectId}`)
        .then(response => response.json())
        .then(data => {
            promptSelect.innerHTML = '<option value="">Prompt seçin...</option>';
            data.forEach(prompt => {
                const option = document.createElement('option');
                option.value = prompt.id;
                option.textContent = prompt.name;
                promptSelect.appendChild(option);
            });
            promptSelect.disabled = false;
        })
        .catch(error => {
            console.error('Prompt\'lar yüklenirken hata:', error);
            promptSelect.innerHTML = '<option value="">Hata: Prompt\'lar yüklenemedi</option>';
            promptSelect.disabled = false;
        });
}

// Copy to clipboard function
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Show success message
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
        alert.style.top = '20px';
        alert.style.right = '20px';
        alert.style.zIndex = '9999';
        alert.innerHTML = `
            <i class="fas fa-check"></i> Kopyalandı!
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);
        
        setTimeout(function() {
            alert.remove();
        }, 3000);
    });
}

// Theme toggle (for future use)
function toggleTheme() {
    const body = document.body;
    const isDark = body.classList.contains('dark-theme');
    
    if (isDark) {
        body.classList.remove('dark-theme');
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-theme');
        localStorage.setItem('theme', 'dark');
    }
}

// Initialize theme from localStorage
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }
});

// Real-time test status updates (WebSocket would be better for production)
function startTestStatusPolling(testId) {
    const pollInterval = setInterval(function() {
        fetch(`/tests/status/${testId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'running') {
                    clearInterval(pollInterval);
                    location.reload(); // Refresh to show final results
                }
            })
            .catch(error => {
                console.error('Test durumu kontrol edilirken hata:', error);
            });
    }, 10000); // Check every 10 seconds
    
    // Stop polling after 30 minutes
    setTimeout(function() {
        clearInterval(pollInterval);
    }, 30 * 60 * 1000);
}