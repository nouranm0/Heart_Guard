/*
HEARTGAURD - Video Splash Screen
Plays animated heart video with enhanced styling
*/

class SplashScreen {
    constructor() {
        this.setupVideo();
        this.setupAutoRedirect();
        this.setupParticles();
    }

    setupVideo() {
        const video = document.querySelector('.splash-video');
        const videoContainer = document.querySelector('.video-container');
        
        if (video) {
            // Auto-play video
            video.play().catch(error => {
                console.log('Video autoplay failed:', error);
            });

            // Handle video events
            video.addEventListener('loadedmetadata', () => {
                console.log('Video loaded successfully');
            });

            video.addEventListener('ended', () => {
                // Restart video when it ends
                video.currentTime = 0;
                video.play();
            });

            // Add mouse tracking for subtle parallax on container
            document.addEventListener('mousemove', (e) => {
                if (!videoContainer) return;
                
                const mouseX = (e.clientX / window.innerWidth - 0.5) * 10;
                const mouseY = (e.clientY / window.innerHeight - 0.5) * 10;
                
                videoContainer.style.transform = `perspective(1000px) rotateX(${mouseY}deg) rotateY(${mouseX}deg) translateZ(20px)`;
            });

            document.addEventListener('mouseleave', () => {
                if (videoContainer) {
                    videoContainer.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
                }
            });

            // Smooth transition
            if (videoContainer) {
                videoContainer.style.transition = 'transform 0.15s ease-out';
            }
        }

        this.enhanceVideoGlow();
    }

    enhanceVideoGlow() {
        const videoContainer = document.querySelector('.video-container');
        
        if (videoContainer) {
            // Pulse the glow effect
            setInterval(() => {
                videoContainer.style.filter = 'drop-shadow(0 0 30px rgba(255, 23, 68, 0.8)) drop-shadow(0 0 60px rgba(255, 82, 82, 0.5))';
            }, 1000);
        }
    }

    setupParticles() {
        // Create floating particles around video
        const container = document.querySelector('.splash-container');
        if (!container) return;

        for (let i = 0; i < 30; i++) {
            const particle = document.createElement('div');
            particle.className = 'splash-particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 8 + 's';
            particle.style.width = (Math.random() * 3 + 2) + 'px';
            particle.style.height = particle.style.width;
            container.appendChild(particle);
        }
    }

    setupAutoRedirect() {
        // Auto redirect to /intro after 4 seconds
        setTimeout(() => {
            window.location.href = '/intro';
        }, 4000);
    }
}

// Initialize splash screen when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new SplashScreen();
});
