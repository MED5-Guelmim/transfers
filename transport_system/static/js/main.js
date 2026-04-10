/* ═══════════════════════════════════════════
   نظام إدارة النقل اللوجستي - JavaScript
   ═══════════════════════════════════════════ */

// ── إدارة الشريط الجانبي ──
document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebarToggle');
    const overlay = document.getElementById('sidebarOverlay');

    if (toggle) {
        toggle.addEventListener('click', function () {
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
        });
    }

    if (overlay) {
        overlay.addEventListener('click', function () {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        });
    }

    // تحريك العناصر عند التمرير
    animateOnScroll();
});

// ── نظام الإشعارات (Toast) ──
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: 'bi-check-circle-fill',
        error: 'bi-x-circle-fill',
        info: 'bi-info-circle-fill',
        warning: 'bi-exclamation-triangle-fill'
    };

    const titles = {
        success: 'نجاح',
        error: 'خطأ',
        info: 'معلومة',
        warning: 'تنبيه'
    };

    const toastId = 'toast-' + Date.now();

    const toastHTML = `
        <div id="${toastId}" class="toast toast-custom toast-${type}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="bi ${icons[type] || icons.info} me-2" style="color: var(--${type === 'error' ? 'danger' : type})"></i>
                <strong class="me-auto">${titles[type] || titles.info}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="إغلاق" style="filter: invert(1) brightness(0.7);"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', toastHTML);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 4000
    });

    toast.show();

    // إزالة العنصر بعد الاختفاء
    toastElement.addEventListener('hidden.bs.toast', function () {
        toastElement.remove();
    });
}

// ── تحريكات التمرير ──
function animateOnScroll() {
    const elements = document.querySelectorAll('.stat-card, .quick-action-card, .content-card, .team-card, .team-status-card');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                entry.target.style.animationDelay = `${index * 0.1}s`;
                entry.target.classList.add('animated');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    elements.forEach(el => observer.observe(el));
}

// ── دالة مساعدة: طلب API ──
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        const result = await response.json();
        return { ok: response.ok, data: result };
    } catch (error) {
        console.error('API Error:', error);
        return { ok: false, data: { error: 'حدث خطأ في الاتصال بالخادم' } };
    }
}

// ── تأثير الأرقام المتحركة ──
function animateNumbers() {
    document.querySelectorAll('.stat-number').forEach(el => {
        const target = parseInt(el.textContent) || 0;
        if (target === 0) return;

        let current = 0;
        const increment = Math.ceil(target / 30);
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            el.textContent = current;
        }, 30);
    });
}

// تشغيل تحريك الأرقام عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', animateNumbers);

// ── تغيير كلمة المرور (متاح في كل الصفحات) ──
function openChangePasswordModal() {
    const modal = document.getElementById('globalChangePasswordModal');
    if (!modal) return;

    document.getElementById('globalCurrentPassword').value = '';
    document.getElementById('globalNewPassword').value = '';
    document.getElementById('globalConfirmPassword').value = '';

    new bootstrap.Modal(modal).show();
}

async function globalChangePassword() {
    const current_password = document.getElementById('globalCurrentPassword').value;
    const new_password = document.getElementById('globalNewPassword').value;
    const confirm_password = document.getElementById('globalConfirmPassword').value;

    if (!current_password || !new_password) {
        showToast('جميع الحقول مطلوبة', 'error');
        return;
    }

    if (new_password.length < 4) {
        showToast('كلمة المرور الجديدة قصيرة جداً (4 أحرف على الأقل)', 'error');
        return;
    }

    if (new_password !== confirm_password) {
        showToast('كلمة المرور الجديدة وتأكيدها غير متطابقتين', 'error');
        return;
    }

    const { ok, data } = await apiRequest('/change-password', 'POST', { current_password, new_password });
    if (ok) {
        showToast(data.message || 'تم تغيير كلمة المرور بنجاح', 'success');
        bootstrap.Modal.getInstance(document.getElementById('globalChangePasswordModal')).hide();
    } else {
        showToast(data.error || 'حدث خطأ', 'error');
    }
}
