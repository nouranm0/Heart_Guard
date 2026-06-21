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
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: this.currentTheme } }));
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
            const sunIcon = `
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <circle cx="12" cy="12" r="4"></circle>
                    <path d="M12 2v2.5M12 19.5V22M4.93 4.93l1.77 1.77M17.3 17.3l1.77 1.77M2 12h2.5M19.5 12H22M4.93 19.07l1.77-1.77M17.3 6.7l1.77-1.77"></path>
                </svg>`;
            const moonIcon = `
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M21 14.8A8.5 8.5 0 1 1 9.2 3a7 7 0 1 0 11.8 11.8Z"></path>
                </svg>`;

            if (this.currentTheme === 'light') {
                themeToggle.innerHTML = moonIcon;
                themeToggle.title = 'Switch to Dark Mode';
            } else {
                themeToggle.innerHTML = sunIcon;
                themeToggle.title = 'Switch to Light Mode';
            }
        }
    }
}

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});
