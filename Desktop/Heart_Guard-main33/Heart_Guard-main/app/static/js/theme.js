/*
HEARTGAURD - Theme System (Dark/Light Mode)
Handles theme toggle and persistence
*/

class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'dark';
        this.init();
    }

    init() {
        // Apply saved theme on page load
        this.applyTheme(this.currentTheme);
        
        // Add event listener to theme toggle button
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
            this.updateThemeIcon();
        }
    }

    toggleTheme() {
        this.currentTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(this.currentTheme);
        localStorage.setItem('theme', this.currentTheme);
        this.updateThemeIcon();
    }

    applyTheme(theme) {
        const body = document.body;
        if (theme === 'light') {
            body.classList.add('light-mode');
            body.classList.remove('theme-dark');
            document.documentElement.style.colorScheme = 'light';
        } else {
            body.classList.remove('light-mode');
            body.classList.add('theme-dark');
            document.documentElement.style.colorScheme = 'dark';
        }
    }

    updateThemeIcon() {
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            if (this.currentTheme === 'light') {
                themeToggle.innerHTML = '🌙';
                themeToggle.title = 'Switch to Dark Mode';
            } else {
                themeToggle.innerHTML = '☀️';
                themeToggle.title = 'Switch to Light Mode';
            }
        }
    }
}

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ThemeManager();
});
