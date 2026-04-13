// ============================================
// SIDEBAR NAVIGATION MANAGER
// ============================================

class SidebarNavigationManager {
    constructor() {
        this.navItems = document.querySelectorAll('.nav-item');
        this.init();
    }

    init() {
        this.setActiveNavItem();
        // Listen for navigation changes
        window.addEventListener('popstate', () => this.setActiveNavItem());
    }

    setActiveNavItem() {
        const currentPath = window.location.pathname;
        
        this.navItems.forEach(item => {
            item.classList.remove('active');
            
            const href = item.getAttribute('href');
            
            // Check if nav item href matches current path
            if (href && href !== '#') {
                // Normalize paths for comparison
                const itemPath = new URL(href, window.location.origin).pathname;
                
                if (currentPath === itemPath) {
                    item.classList.add('active');
                }
            }
        });
    }

    // Method to programmatically navigate
    navigateTo(path) {
        window.location.href = path;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new SidebarNavigationManager();
    initializeIconLabels();
});

// ============================================
// ICON LABEL TOOLTIP SYSTEM
// ============================================

function initializeIconLabels() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        // Get the tooltip text from data attribute
        const tooltipText = item.getAttribute('data-tooltip');
        
        if (tooltipText) {
            // Show label on click
            item.addEventListener('click', (e) => {
                // Show temporary label notification
                showIconLabel(tooltipText);
            });
            
            // Also show on hover for better UX
            item.addEventListener('mouseenter', () => {
                showHoverLabel(item, tooltipText);
            });
        }
    });
}

function showHoverLabel(element, text) {
    // Remove any existing hover label
    const existing = document.querySelector('.icon-hover-label');
    if (existing) existing.remove();
    
    // Create and show hover label
    const label = document.createElement('div');
    label.className = 'icon-hover-label';
    label.textContent = text;
    label.style.cssText = `
        position: fixed;
        background: var(--accent-glow);
        color: var(--bg-dark);
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        white-space: nowrap;
        z-index: 10000;
        pointer-events: none;
        animation: slideIn 0.2s ease-out;
    `;
    
    document.body.appendChild(label);
    
    // Position near the element
    const rect = element.getBoundingClientRect();
    label.style.left = (rect.right + 10) + 'px';
    label.style.top = (rect.top + rect.height / 2 - label.offsetHeight / 2) + 'px';
    
    // Remove on mouse leave
    element.addEventListener('mouseleave', () => {
        if (label.parentNode) {
            label.remove();
        }
    });
}

function showIconLabel(text) {
    // Remove existing notification
    const existing = document.querySelector('.icon-label-toast');
    if (existing) existing.remove();
    
    // Create notification
    const toast = document.createElement('div');
    toast.className = 'icon-label-toast';
    toast.textContent = text;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, var(--accent-glow), var(--accent-secondary));
        color: var(--bg-dark);
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        z-index: 10000;
        animation: slideUp 0.3s ease-out;
        box-shadow: 0 8px 24px rgba(0, 217, 255, 0.3);
    `;
    
    document.body.appendChild(toast);
    
    // Auto remove after 2 seconds
    setTimeout(() => {
        toast.style.animation = 'slideDown 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// Add animations if not already in CSS
if (!document.querySelector('style[data-animations]')) {
    const style = document.createElement('style');
    style.setAttribute('data-animations', 'true');
    style.textContent = `
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-10px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes slideDown {
            from {
                opacity: 1;
                transform: translateY(0);
            }
            to {
                opacity: 0;
                transform: translateY(20px);
            }
        }
    `;
    document.head.appendChild(style);
}

// ============================================
// ACTIVE STATE DETECTION FOR BREADCRUMBS
// ============================================

function updatePageIndicators() {
    const currentPath = window.location.pathname;
    const pathSegments = currentPath.split('/').filter(segment => segment);
    
    // Update page title based on path
    let pageTitle = 'Dashboard';
    if (currentPath.includes('doctor')) {
        pageTitle = 'Doctor Dashboard';
    } else if (currentPath.includes('settings')) {
        pageTitle = 'Settings';
    } else if (currentPath.includes('analytics')) {
        pageTitle = 'Analytics';
    } else if (currentPath.includes('alerts')) {
        pageTitle = 'Alerts';
    }
    
    // Update browser title
    document.title = `${pageTitle} - HeartGaurd`;
}

document.addEventListener('DOMContentLoaded', updatePageIndicators);

// ============================================
// SETTINGS PERSISTENCE AND GLOBAL STATE
// ============================================

const AppSettings = {
    STORAGE_KEYS: {
        THEME: 'app_theme',
        LANGUAGE: 'app_language'
    },

    initializeSettings() {
        this.restoreTheme();
        this.restoreLanguage();
        this.setupToggleListeners();
    },

    restoreTheme() {
        const savedTheme = localStorage.getItem(this.STORAGE_KEYS.THEME) || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        if (document.body.classList) {
            document.body.classList.remove('theme-light', 'theme-dark');
            document.body.classList.add(`theme-${savedTheme}`);
        }
    },

    restoreLanguage() {
        const savedLanguage = localStorage.getItem(this.STORAGE_KEYS.LANGUAGE) || 'en';
        document.documentElement.lang = savedLanguage;
        document.documentElement.dir = savedLanguage === 'ar' ? 'rtl' : 'ltr';
    },

    setupToggleListeners() {
        // Theme toggle
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('theme-toggle')) {
                this.toggleTheme();
            }
        });

        // Language toggle
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('language-toggle')) {
                this.toggleLanguage();
            }
        });
    },

    toggleTheme() {
        const currentTheme = localStorage.getItem(this.STORAGE_KEYS.THEME) || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        localStorage.setItem(this.STORAGE_KEYS.THEME, newTheme);
        this.restoreTheme();
        
        // Dispatch event for other scripts to listen to
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
    },

    toggleLanguage() {
        const currentLanguage = localStorage.getItem(this.STORAGE_KEYS.LANGUAGE) || 'en';
        const newLanguage = currentLanguage === 'en' ? 'ar' : 'en';
        localStorage.setItem(this.STORAGE_KEYS.LANGUAGE, newLanguage);
        this.restoreLanguage();
        
        // Dispatch event for other scripts to listen to
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: newLanguage } }));
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    AppSettings.initializeSettings();
});

// ============================================
// FORM VALIDATION UTILITIES
// ============================================

const FormValidator = {
    validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    validatePhone(phone) {
        const re = /^[\d\s\-\+\(\)]{10,}$/;
        return re.test(phone);
    },

    validatePassword(password) {
        // At least 8 characters, 1 uppercase, 1 lowercase, 1 number
        const re = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
        return re.test(password);
    },

    showError(input, message) {
        input.style.borderColor = 'var(--danger)';
        input.style.background = 'rgba(255, 71, 87, 0.1)';
        
        let errorDiv = input.nextElementSibling;
        if (!errorDiv || !errorDiv.classList.contains('error-message')) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            input.parentNode.insertBefore(errorDiv, input.nextSibling);
        }
        errorDiv.textContent = message;
        errorDiv.style.color = 'var(--danger)';
        errorDiv.style.fontSize = '0.85rem';
        errorDiv.style.marginTop = '0.5rem';
    },

    clearError(input) {
        input.style.borderColor = '';
        input.style.background = '';
        
        let errorDiv = input.nextElementSibling;
        if (errorDiv && errorDiv.classList.contains('error-message')) {
            errorDiv.remove();
        }
    }
};

// ============================================
// SETTINGS PAGE HANDLERS
// ============================================

const SettingsPage = {
    init() {
        this.setupProfileForm();
        this.setupPasswordForm();
        this.setupNotificationToggles();
        this.setupThemeToggle();
        this.setupLanguageSelector();
        this.setupPrivacyToggles();
    },

    setupProfileForm() {
        const profileForm = document.querySelector('.profile-form');
        if (!profileForm) return;

        const inputs = profileForm.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="date"]');
        
        inputs.forEach(input => {
            input.addEventListener('blur', (e) => {
                this.validateProfileInput(e.target);
            });

            input.addEventListener('focus', () => {
                FormValidator.clearError(input);
            });
        });

        // Form submission
        profileForm.addEventListener('submit', (e) => {
            e.preventDefault();
            let isValid = true;

            inputs.forEach(input => {
                if (!this.validateProfileInput(input)) {
                    isValid = false;
                }
            });

            if (isValid) {
                this.saveProfile(profileForm);
            }
        });
    },

    validateProfileInput(input) {
        const value = input.value.trim();
        const type = input.type;

        if (!value) {
            FormValidator.showError(input, 'This field is required');
            return false;
        }

        if (type === 'email' && !FormValidator.validateEmail(value)) {
            FormValidator.showError(input, 'Please enter a valid email');
            return false;
        }

        if (type === 'tel' && !FormValidator.validatePhone(value)) {
            FormValidator.showError(input, 'Please enter a valid phone number');
            return false;
        }

        FormValidator.clearError(input);
        return true;
    },

    saveProfile(form) {
        const formData = new FormData(form);
        
        // Show success message
        this.showNotification('Profile updated successfully!', 'success');
        
        // Here you would send to server
        console.log('Profile data:', Object.fromEntries(formData));
    },

    setupPasswordForm() {
        const passwordForm = document.querySelector('.password-form');
        if (!passwordForm) return;

        const currentPassword = passwordForm.querySelector('input[name="current_password"]');
        const newPassword = passwordForm.querySelector('input[name="new_password"]');
        const confirmPassword = passwordForm.querySelector('input[name="confirm_password"]');

        const validatePassword = () => {
            let isValid = true;

            if (!currentPassword.value) {
                FormValidator.showError(currentPassword, 'Current password is required');
                isValid = false;
            } else {
                FormValidator.clearError(currentPassword);
            }

            if (!newPassword.value) {
                FormValidator.showError(newPassword, 'New password is required');
                isValid = false;
            } else if (!FormValidator.validatePassword(newPassword.value)) {
                FormValidator.showError(newPassword, 'Password must be at least 8 characters with uppercase, lowercase, and numbers');
                isValid = false;
            } else {
                FormValidator.clearError(newPassword);
            }

            if (!confirmPassword.value) {
                FormValidator.showError(confirmPassword, 'Please confirm password');
                isValid = false;
            } else if (confirmPassword.value !== newPassword.value) {
                FormValidator.showError(confirmPassword, 'Passwords do not match');
                isValid = false;
            } else {
                FormValidator.clearError(confirmPassword);
            }

            return isValid;
        };

        passwordForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (validatePassword()) {
                this.showNotification('Password changed successfully!', 'success');
                passwordForm.reset();
            }
        });
    },

    setupNotificationToggles() {
        const toggles = document.querySelectorAll('.notification-toggle');
        toggles.forEach(toggle => {
            const checkbox = toggle.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.addEventListener('change', (e) => {
                    const setting = e.target.getAttribute('data-setting');
                    this.saveNotificationPreference(setting, e.target.checked);
                });
            }
        });
    },

    saveNotificationPreference(setting, enabled) {
        console.log(`Notification setting: ${setting} = ${enabled}`);
        // Send to server via API
    },

    setupThemeToggle() {
        const themeToggle = document.querySelector('input[data-setting="theme"]');
        if (!themeToggle) return;

        themeToggle.addEventListener('change', (e) => {
            const isDark = e.target.checked;
            document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            this.showNotification(`Switched to ${isDark ? 'dark' : 'light'} mode`, 'info');
        });
    },

    setupLanguageSelector() {
        const languageSelect = document.querySelector('select[name="language"]');
        if (!languageSelect) return;

        languageSelect.addEventListener('change', (e) => {
            const language = e.target.value;
            localStorage.setItem('language', language);
            
            // Trigger language change event
            const event = new CustomEvent('languageChanged', { detail: { language } });
            window.dispatchEvent(event);
            
            this.showNotification(`Language changed to ${language}`, 'success');
        });
    },

    setupPrivacyToggles() {
        const toggles = document.querySelectorAll('.privacy-toggle');
        toggles.forEach(toggle => {
            const checkbox = toggle.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.addEventListener('change', (e) => {
                    const setting = e.target.getAttribute('data-setting');
                    this.savePrivacySetting(setting, e.target.checked);
                });
            }
        });
    },

    savePrivacySetting(setting, enabled) {
        console.log(`Privacy setting: ${setting} = ${enabled}`);
        // Send to server via API
    },

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--danger)' : 'var(--accent-glow)'};
            color: white;
            padding: 16px 24px;
            border-radius: 12px;
            font-weight: 600;
            z-index: 9999;
            animation: slideInUp 0.3s ease-out;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOutDown 0.3s ease-out forwards';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
};

// Initialize settings page when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('settings')) {
        SettingsPage.init();
    }
});
