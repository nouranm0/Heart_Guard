/*
HEARTGAURD - Dashboard Interactions
Handles ECG chart, vital signs, and real-time updates
*/

class Dashboard {
    constructor() {
        this.initChart();
        this.animateVitalCards();
        this.setupInteractions();
    }

    initChart() {
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.log('Chart.js not loaded, creating fallback ECG visualization');
            this.createFallbackECG();
            return;
        }

        const ctx = document.getElementById('ecgChart');
        if (!ctx) return;

        // Generate mock ECG data
        const ecgData = this.generateECGData(200);
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: 200}, (_, i) => i),
                datasets: [{
                    label: 'ECG Waveform',
                    data: ecgData,
                    borderColor: '#00D9FF',
                    backgroundColor: 'rgba(0, 217, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        min: -100,
                        max: 100,
                        grid: {
                            color: 'rgba(30, 58, 78, 0.2)'
                        },
                        ticks: {
                            color: '#A0B4D4'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#A0B4D4'
                        }
                    }
                }
            }
        });
    }

    generateECGData(length) {
        const data = [];
        for (let i = 0; i < length; i++) {
            const t = i / 20;
            // Simulate ECG waveform with combination of sine waves
            const value = 
                60 * Math.sin(t) + 
                20 * Math.sin(3 * t) + 
                15 * Math.sin(5 * t) +
                Math.random() * 5;
            data.push(value);
        }
        return data;
    }

    createFallbackECG() {
        // Create SVG-based ECG visualization if Chart.js unavailable
        const canvas = document.getElementById('ecgChart');
        if (!canvas) return;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.setAttribute('viewBox', '0 0 800 200');
        svg.style.backgroundColor = 'rgba(0, 217, 255, 0.05)';
        
        // Generate path data
        let pathData = 'M 0 100';
        for (let i = 0; i < 800; i += 4) {
            const t = i / 50;
            const y = 100 - (
                30 * Math.sin(t) + 
                10 * Math.sin(3 * t) + 
                5 * Math.sin(5 * t)
            );
            pathData += ` L ${i} ${y}`;
        }
        
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', pathData);
        path.setAttribute('stroke', '#00D9FF');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke-linecap', 'round');
        
        svg.appendChild(path);
        canvas.replaceWith(svg);
    }

    animateVitalCards() {
        const vitalCards = document.querySelectorAll('.vital-card');
        
        vitalCards.forEach((card, index) => {
            card.style.animation = `fadeInUp 0.6s ease-out ${0.1 * index}s both`;
        });

        // Simulate real-time updates
        setInterval(() => {
            vitalCards.forEach(card => {
                const value = card.querySelector('.vital-value');
                if (value) {
                    // Simulate slight variations
                    const currentValue = parseInt(value.textContent);
                    const variation = Math.floor((Math.random() - 0.5) * 6);
                    const newValue = Math.max(0, currentValue + variation);
                    value.textContent = newValue;
                    
                    // Add pulse animation
                    value.style.animation = 'none';
                    setTimeout(() => {
                        value.style.animation = 'pulse 0.5s ease-out';
                    }, 10);
                }
            });
        }, 3000);
    }

    setupInteractions() {
        // Sidebar icon interactions
        const sidebarIcons = document.querySelectorAll('.sidebar-icon');
        sidebarIcons.forEach((icon, index) => {
            icon.addEventListener('click', () => {
                sidebarIcons.forEach(i => i.classList.remove('active'));
                icon.classList.add('active');
            });
            
            // Set first icon as active by default
            if (index === 0) {
                icon.classList.add('active');
            }
        });
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
