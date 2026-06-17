/*
HEARTGAURD - ECG Module
Real-time ECG visualization and animation mimicking medical device
*/

class ECGModule {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.animationFrame = null;
        this.isAnimating = false;
        this.scrollOffset = 0;
        this.width = 800;
        this.height = 200;
        this.centerY = this.height / 2;
        this.beatCounter = 0;
        this.heartRate = 72; // Default heart rate in BPM
        this.init();
    }

    init() {
        // Initialize ECG canvas
        this.canvas = document.getElementById('ecgChart');
        
        if (!this.canvas) {
            // ECG canvas might not be on all pages
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.width = this.canvas.offsetWidth || 800;
        this.height = this.canvas.offsetHeight || 200;
        this.centerY = this.height / 2;

        // Set canvas resolution
        this.canvas.width = this.width;
        this.canvas.height = this.height;

        // Start continuous animation
        this.startRealisticECGAnimation();
        
        // Responsive resize handling
        window.addEventListener('resize', () => this.handleResize());
    }

    handleResize() {
        const newWidth = this.canvas.offsetWidth || 800;
        const newHeight = this.canvas.offsetHeight || 200;
        
        if (newWidth !== this.width || newHeight !== this.height) {
            this.width = newWidth;
            this.height = newHeight;
            this.centerY = this.height / 2;
            this.canvas.width = newWidth;
            this.canvas.height = newHeight;
        }
    }

    startRealisticECGAnimation() {
        if (this.isAnimating) return;
        this.isAnimating = true;

        const animate = () => {
            this.drawRealisticECG();
            // Smooth continuous scroll - faster for realistic ECG sweep
            this.scrollOffset = (this.scrollOffset + 2.5) % (this.width * 2);
            this.beatCounter++;
            this.animationFrame = requestAnimationFrame(animate);
        };

        animate();
    }

    drawRealisticECG() {
        // Clear with trailing effect for real ECG machine look
        this.ctx.fillStyle = 'rgba(10, 14, 39, 0.15)';
        this.ctx.fillRect(0, 0, this.width, this.height);

        // Draw grid background (like real ECG paper)
        this.drawGridBackground();

        // Draw ECG waveform with sweep effect
        this.drawECGWaveform();

        // Draw device indicators
        this.drawDeviceIndicators();
    }

    drawGridBackground() {
        const majorGridColor = 'rgba(0, 217, 255, 0.08)';
        const minorGridColor = 'rgba(0, 217, 255, 0.03)';
        const majorSpacing = 40;
        const minorSpacing = 10;

        // Minor grid lines
        this.ctx.strokeStyle = minorGridColor;
        this.ctx.lineWidth = 0.5;

        for (let x = 0; x < this.width; x += minorSpacing) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }

        for (let y = 0; y < this.height; y += minorSpacing) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
            this.ctx.stroke();
        }

        // Major grid lines (thicker)
        this.ctx.strokeStyle = majorGridColor;
        this.ctx.lineWidth = 1;

        for (let x = 0; x < this.width; x += majorSpacing) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }

        for (let y = 0; y < this.height; y += majorSpacing) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
            this.ctx.stroke();
        }
    }

    drawECGWaveform() {
        // Realistic ECG waveform - medical standard
        const lineWidth = 2;
        
        // Main gradient for ECG line
        const gradient = this.ctx.createLinearGradient(0, 0, this.width, 0);
        gradient.addColorStop(0, 'rgba(0, 217, 255, 0.2)');
        gradient.addColorStop(0.5, 'rgba(0, 217, 255, 1)');
        gradient.addColorStop(1, 'rgba(0, 153, 204, 0.2)');

        this.ctx.strokeStyle = gradient;
        this.ctx.lineWidth = lineWidth;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.beginPath();

        const timeScale = 0.015; // Control horizontal scale
        const amplitude = 35; // ECG amplitude

        for (let x = 0; x < this.width; x++) {
            // Create realistic ECG wave pattern
            const t = (this.scrollOffset + x) * timeScale;
            const beat = this.generateBeat(t, amplitude);
            const y = this.centerY - beat;

            if (x === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }

        this.ctx.stroke();

        // Add glow/shadow effect for depth
        this.ctx.strokeStyle = 'rgba(0, 217, 255, 0.1)';
        this.ctx.lineWidth = lineWidth + 3;
        this.ctx.beginPath();

        for (let x = 0; x < this.width; x++) {
            const t = (this.scrollOffset + x) * timeScale;
            const beat = this.generateBeat(t, amplitude);
            const y = this.centerY - beat;

            if (x === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }

        this.ctx.stroke();
    }

    generateBeat(t, amplitude) {
        // Realistic ECG pattern with P-QRS-T waves
        const beatLength = 60; // Length of one heartbeat cycle
        const phase = ((t * 10) % beatLength) / beatLength;

        let signal = 0;

        // P wave
        if (phase < 0.15) {
            signal += Math.sin(phase * Math.PI * 6) * amplitude * 0.3;
        }

        // QRS complex (main wave)
        if (phase >= 0.15 && phase < 0.35) {
            const qrsPhase = (phase - 0.15) / 0.2;
            signal += Math.sin(qrsPhase * Math.PI) * amplitude;
            signal += Math.sin(qrsPhase * Math.PI * 2) * amplitude * 0.5;
        }

        // T wave
        if (phase >= 0.35 && phase < 0.6) {
            const tPhase = (phase - 0.35) / 0.25;
            signal += Math.sin(tPhase * Math.PI) * amplitude * 0.4;
        }

        // Add slight noise for realism
        signal += (Math.random() - 0.5) * 2;

        return signal;
    }

    drawDeviceIndicators() {
        // Draw a moving sweep line to show current reading point
        const sweepX = (this.scrollOffset * 1.5) % this.width;
        
        // Bright sweep indicator
        const sweepGradient = this.ctx.createLinearGradient(
            sweepX - 20, 0, 
            sweepX + 20, 0
        );
        sweepGradient.addColorStop(0, 'rgba(0, 217, 255, 0)');
        sweepGradient.addColorStop(0.5, 'rgba(0, 217, 255, 0.8)');
        sweepGradient.addColorStop(1, 'rgba(0, 217, 255, 0)');

        this.ctx.fillStyle = sweepGradient;
        this.ctx.fillRect(sweepX - 20, 0, 40, this.height);

        // Draw heart rate indicator dots
        this.drawHeartRateDots();
    }

    drawHeartRateDots() {
        // Show active heartbeat indicators
        const dotRadius = 3;
        const beatPhase = (this.beatCounter % 60) / 60;

        // Create pulsing effect
        const intensity = Math.sin(beatPhase * Math.PI) * 0.5 + 0.5;
        
        // Right side indicator
        this.ctx.beginPath();
        this.ctx.arc(
            this.width - 25,
            25,
            dotRadius * intensity,
            0,
            Math.PI * 2
        );
        this.ctx.fillStyle = `rgba(255, 46, 99, ${0.7 * intensity})`;
        this.ctx.fill();

        // Outer ring
        this.ctx.strokeStyle = `rgba(255, 107, 157, ${0.5 * intensity})`;
        this.ctx.lineWidth = 1.5;
        this.ctx.stroke();
    }

    // Legacy method for compatibility
    drawECGPath(canvasElement, width = 800, height = 200) {
        if (!canvasElement) return;

        const ctx = canvasElement.getContext('2d');
        if (!ctx) return;

        ctx.clearRect(0, 0, width, height);
        ctx.strokeStyle = '#00D9FF';
        ctx.lineWidth = 2;
        ctx.beginPath();

        const centerY = height / 2;
        for (let i = 0; i < width; i++) {
            const t = i / 50;
            const y = centerY - (
                30 * Math.sin(t) +
                10 * Math.sin(3 * t) +
                5 * Math.sin(5 * t)
            );

            if (i === 0) {
                ctx.moveTo(i, y);
            } else {
                ctx.lineTo(i, y);
            }
        }

        ctx.stroke();
    }
}

// Initialize ECG module when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ECGModule();
});
