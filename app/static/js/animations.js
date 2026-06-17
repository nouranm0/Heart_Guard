/*
HEARTGAURD - Advanced Animations & Interactions
Handles card animations, scroll effects, and interactive elements
*/

class AnimationManager {
    constructor() {
        this.setupIntersectionObserver();
        this.setupScrollAnimations();
        this.setupCardHovers();
    }

    setupIntersectionObserver() {
        // Animate elements when they come into view
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -100px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in-view');
                    // Add stagger delay for multiple elements
                    const parent = entry.target.parentElement;
                    if (parent && parent.classList.contains('animated-features')) {
                        const index = Array.from(parent.children).indexOf(entry.target);
                        entry.target.style.animationDelay = (index * 0.1) + 's';
                    }
                }
            });
        }, observerOptions);

        // Observe animated elements
        document.querySelectorAll('.feature-card, .parameter-item, .condition-card, .metric-box').forEach(el => {
            observer.observe(el);
        });
    }

    setupScrollAnimations() {
        // Add scroll-triggered animations
        const sections = document.querySelectorAll('.intro-section, .model-section');
        
        sections.forEach((section, index) => {
            if (!section.style.animationDelay) {
                section.style.animationDelay = (index * 0.1) + 's';
            }
        });
    }

    setupCardHovers() {
        // Enhanced hover effects for cards
        const cards = document.querySelectorAll('[class*="-card"]');
        
        cards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-5px)';
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });
        });
    }

    // Stagger animation helper
    static staggerElements(selector, baseDelay = 0.1) {
        const elements = document.querySelectorAll(selector);
        elements.forEach((el, index) => {
            el.style.animationDelay = (baseDelay * index) + 's';
        });
    }
}

// Dashboard Animations
class DashboardAnimations {
    constructor() {
        this.animateVitalCards();
        this.setupRealTimeAnimations();
    }

    animateVitalCards() {
        const cards = document.querySelectorAll('.vital-card');
        cards.forEach((card, index) => {
            card.style.animationDelay = (index * 0.1) + 's';
        });
    }

    setupRealTimeAnimations() {
        // Pulse animation for active elements
        const activeElements = document.querySelectorAll('.risk-indicator, .ai-diagnosis');
        
        activeElements.forEach(el => {
            el.style.animation = 'pulse 2s ease-in-out infinite';
        });
    }
}

// Initialize animations when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on dashboard page
    if (document.querySelector('.dashboard-container')) {
        new DashboardAnimations();
    } else {
        // Other pages
        new AnimationManager();
    }
});

// Smooth scroll animation
document.addEventListener('scroll', () => {
    const scrollPercentage = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
    // Can be used for progress indicators
});

// Export for use in other scripts
window.AnimationManager = AnimationManager;
window.DashboardAnimations = DashboardAnimations;
