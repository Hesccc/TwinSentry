// API Configuration
const API_BASE = '';

async function apiRequest(url, method = 'GET', body = null, useToken = true) {
    const headers = {
        'Content-Type': 'application/json'
    };

    if (useToken) {
        const token = localStorage.getItem('ts_token');
        if (!token) {
            window.location.href = '/login';
            return;
        }
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        method,
        headers
    };

    if (body) {
        config.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(url, config);

        if (response.status === 401 && useToken) {
            localStorage.removeItem('ts_token');
            window.location.href = '/login';
            return;
        }

        return await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        return { message: 'Network Error' };
    }
}

// User Info & Session
function syncUser(user) {
    if (!user) return;
    localStorage.setItem('ts_user', JSON.stringify(user));

    const nameEl = document.getElementById('header-username');
    const avatarEl = document.getElementById('header-avatar');
    const iconEl = document.getElementById('header-avatar-icon');

    if (nameEl) nameEl.textContent = user.username;
    if (avatarEl) {
        if (user.avatar) {
            avatarEl.src = user.avatar + '?t=' + new Date().getTime();
            avatarEl.style.display = 'block';
            if (iconEl) iconEl.style.display = 'none';
        } else {
            avatarEl.style.display = 'none';
            if (iconEl) iconEl.style.display = 'block';
        }
    }
}

function initUser() {
    const userStr = localStorage.getItem('ts_user');
    if (userStr) {
        syncUser(JSON.parse(userStr));
    }

    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) {
        logoutBtn.onclick = async (e) => {
            e.preventDefault();
            await apiRequest('/api/auth/logout', 'POST');
            localStorage.removeItem('ts_token');
            localStorage.removeItem('ts_user');
            // Clear cookie
            document.cookie = "auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;";
            window.location.href = '/login';
        };
    }
}

// Modal Logic
const modal = {
    el: document.getElementById('modal-container'),
    title: document.getElementById('modal-title'),
    body: document.getElementById('modal-body'),

    show(title, content) {
        this.title.textContent = title;
        if (typeof content === 'string') {
            this.body.innerHTML = content;
        } else {
            this.body.innerHTML = '';
            this.body.appendChild(content);
        }
        this.el.classList.add('active');
    },

    hide() {
        this.el.classList.remove('active');
    }
};

const closeModalBtn = document.getElementById('close-modal');
if (closeModalBtn) {
    closeModalBtn.onclick = () => modal.hide();
}

window.onclick = (event) => {
    if (event.target == modal.el) modal.hide();
};

// Tooltip / Feedback Helper
function showFeedback(message, type = 'success') {
    const feedback = document.createElement('div');
    feedback.className = 'feedback-toast';
    feedback.style.position = 'fixed';
    feedback.style.bottom = '20px';
    feedback.style.right = '20px';
    feedback.style.padding = '10px 20px';
    feedback.style.background = type === 'success' ? '#10b981' : (type === 'info' ? '#6366f1' : '#ef4444');
    feedback.style.color = 'white';
    feedback.style.borderRadius = '5px';
    feedback.style.zIndex = '3000';
    feedback.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
    feedback.style.transition = 'all 0.3s ease';
    feedback.textContent = message;
    document.body.appendChild(feedback);
    setTimeout(() => {
        feedback.style.opacity = '0';
        feedback.style.transform = 'translateY(10px)';
        setTimeout(() => feedback.remove(), 300);
    }, 3000);
}

function copyToClipboard(text, callback) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            if (callback) callback();
            else showFeedback('内容已复制到剪贴板');
        }).catch(err => {
            console.error('Clipboard error:', err);
            fallbackCopy(text, callback);
        });
    } else {
        fallbackCopy(text, callback);
    }
}

function fallbackCopy(text, callback) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    textArea.style.top = "0";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            if (callback) callback();
            else showFeedback('内容已复制到剪贴板');
        }
    } catch (err) {
        console.error('Fallback copy failed', err);
        showFeedback('复制失败，请手动选择复制', 'error');
    }
    document.body.removeChild(textArea);
}

function initMobileNav() {
    const toggleBtn = document.getElementById('mobile-menu-toggle');
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');

    if (!toggleBtn || !sidebar || !backdrop) return;

    const closeMenu = () => {
        sidebar.classList.remove('mobile-open');
        backdrop.classList.remove('active');
        document.body.classList.remove('mobile-menu-open');
    };

    const openMenu = () => {
        sidebar.classList.add('mobile-open');
        backdrop.classList.add('active');
        document.body.classList.add('mobile-menu-open');
    };

    toggleBtn.addEventListener('click', () => {
        const isOpen = sidebar.classList.contains('mobile-open');
        if (isOpen) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    backdrop.addEventListener('click', closeMenu);

    window.addEventListener('resize', () => {
        if (window.innerWidth > 900) {
            closeMenu();
        }
    });
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname !== '/login') {
        initUser();
        initMobileNav();
    }
});
